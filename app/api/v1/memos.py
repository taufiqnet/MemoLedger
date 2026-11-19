import io
import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.memo import Memo, MemoLine
from app.models.supplier import Supplier
from app.schemas.memo import (
    MemoUploadResponse,
    MemoDetailResponse,
    MemoCommitRequest,
)
from app.services.storage import storage_service
from app.services.ledger.ledger_service import LedgerService
from app.services.matching.learning_loop import LearningLoopService
from app.services.exports.pdf_invoice import PDFInvoiceGenerator
from app.services.exports.spreadsheets import SpreadsheetExporter
from app.services.exports.whatsapp import WhatsAppShareLink

router = APIRouter(prefix="/memos", tags=["Memos"])


@router.post("/upload", response_model=MemoUploadResponse)
async def upload_memo(
    file: UploadFile = File(...),
    supplier_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Idempotent photo upload endpoint with SHA-256 deduplication.
    """
    # 1. Validate File Format
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only image files (JPEG, PNG, WebP) are accepted."
        )

    file_bytes = await file.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 15MB limit."
        )

    # 2. Compute SHA-256 Hash for Idempotency
    image_hash = hashlib.sha256(file_bytes).hexdigest()

    # Check for existing memo with this hash
    existing = db.query(Memo).filter(
        Memo.tenant_id == current_user.tenant_id,
        Memo.image_hash == image_hash
    ).first()

    if existing:
        if existing.status == "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This exact memo has already been approved and committed (Memo #{existing.memo_number or 'N/A'})."
            )
        # If in progress, return existing ID
        return MemoUploadResponse(
            memo_id=existing.id,
            status=existing.status,
            message="Existing unprocessed memo found for this image."
        )

    # 3. Store in S3 / MinIO
    object_name = f"memos/{current_user.tenant_id}/{image_hash[:16]}_{file.filename}"
    storage_service.upload_bytes(file_bytes, object_name, content_type=file.content_type)

    # 4. Create Memo Record
    supp_uuid = uuid.UUID(supplier_id) if supplier_id else None
    memo = Memo(
        tenant_id=current_user.tenant_id,
        supplier_id=supp_uuid,
        image_s3_key=object_name,
        image_hash=image_hash,
        status="PROCESSING",
        notes=notes
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)

    # 5. Dispatch async background task (with inline fallback)
    task_id = None
    try:
        from app.workers.tasks import extract_memo_task
        task = extract_memo_task.delay(str(memo.id))
        task_id = task.id
    except Exception:
        # Inline fallback for environments without Celery/Redis
        from app.services.extraction.pipeline import MemoExtractionPipeline
        pipeline = MemoExtractionPipeline(db=db)
        pipeline.run(memo_id=memo.id)

    return MemoUploadResponse(
        memo_id=memo.id,
        task_id=task_id,
        status=memo.status,
        message="Memo uploaded and processing started."
    )


@router.get("/{memo_id}", response_model=MemoDetailResponse)
def get_memo_details(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    return memo


@router.get("/{memo_id}/status")
def get_memo_status(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    return {
        "id": str(memo.id),
        "status": memo.status,
        "line_count": len(memo.lines),
        "extracted_total": float(memo.extracted_total or 0),
        "total_mismatch_flag": memo.total_mismatch_flag
    }


@router.get("/{memo_id}/image")
def get_memo_image(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    
    image_bytes = storage_service.get_bytes(memo.image_s3_key)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.post("/{memo_id}/commit")
def commit_memo(
    memo_id: uuid.UUID,
    commit_data: MemoCommitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    One-Tap Approve: commits all approved lines to the append-only stock ledger.
    """
    lines_dicts = [l.model_dump() for l in commit_data.lines] if commit_data.lines else None
    updated_memo = LedgerService.commit_memo(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        memo_id=memo_id,
        lines_data=lines_dicts
    )
    return {
        "status": "SUCCESS",
        "message": f"Memo #{updated_memo.memo_number or 'N/A'} approved and committed to inventory ledger.",
        "memo_id": str(updated_memo.id)
    }


@router.post("/{memo_id}/lines/{line_id}/correct")
def correct_memo_line(
    memo_id: uuid.UUID,
    line_id: uuid.UUID,
    correction_payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Feeds user edit into the Learning Loop.
    """
    line = db.query(MemoLine).filter(MemoLine.id == line_id, MemoLine.memo_id == memo_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Memo line not found")

    before_data = {
        "raw_text": line.raw_text,
        "parsed_name": line.parsed_name,
        "parsed_variant": line.parsed_variant,
        "parsed_qty": float(line.parsed_qty),
        "parsed_unit_price": float(line.parsed_unit_price or 0),
        "matched_variant_id": str(line.matched_variant_id) if line.matched_variant_id else None
    }
    after_data = correction_payload.get("after_data", {})

    LearningLoopService.record_correction(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        memo_id=memo_id,
        line_id=line_id,
        before_data=before_data,
        after_data=after_data
    )
    return {"status": "SUCCESS", "message": "Correction recorded into learning loop."}


@router.get("/{memo_id}/pdf")
def export_pdf(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")
    
    pdf_bytes = PDFInvoiceGenerator.generate_pdf(memo)
    filename = f"Invoice_Memo_{memo.memo_number or str(memo.id)[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/{memo_id}/excel")
def export_excel(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    excel_bytes = SpreadsheetExporter.export_memo_excel(memo)
    filename = f"Memo_{memo.memo_number or str(memo.id)[:8]}.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{memo_id}/whatsapp")
def get_whatsapp_share_url(
    memo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    link = WhatsAppShareLink.generate_link(memo)
    return {"whatsapp_url": link}
