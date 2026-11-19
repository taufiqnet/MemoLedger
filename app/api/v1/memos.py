import io
import re
import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
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


def parse_multipart_fallback(body: bytes, content_type: str):
    """
    Pure Python multipart/form-data parser without external C/rust dependencies.
    """
    match = re.search(r'boundary=([^;]+)', content_type)
    if not match:
        return body, "memo.jpg", None

    boundary = match.group(1).strip().strip('"').encode()
    delimiter = b'--' + boundary
    parts = body.split(delimiter)

    file_bytes = None
    filename = "memo_capture.jpg"
    supplier_id = None

    for part in parts:
        if not part or part == b'--\r\n' or part == b'--':
            continue
        if b'\r\n\r\n' not in part:
            continue
        header_part, content_part = part.split(b'\r\n\r\n', 1)
        # Strip trailing \r\n
        if content_part.endswith(b'\r\n'):
            content_part = content_part[:-2]

        headers_str = header_part.decode('utf-8', errors='ignore')
        if 'name="file"' in headers_str:
            fn_match = re.search(r'filename="([^"]+)"', headers_str)
            if fn_match:
                filename = fn_match.group(1)
            file_bytes = content_part
        elif 'name="supplier_id"' in headers_str:
            supplier_id = content_part.decode('utf-8', errors='ignore').strip()

    return file_bytes or body, filename, supplier_id


@router.post("/upload", response_model=MemoUploadResponse)
async def upload_memo(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Idempotent photo upload endpoint with SHA-256 deduplication.
    Accepts multipart/form-data, direct image bytes, or octet-stream.
    """
    content_type = request.headers.get("content-type", "")
    body_bytes = await request.body()

    if not body_bytes:
        raise HTTPException(status_code=400, detail="Empty upload body received.")

    if len(body_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 15MB limit.")

    file_bytes, filename, supplier_id = parse_multipart_fallback(body_bytes, content_type)

    # Compute SHA-256 Hash for Idempotency
    image_hash = hashlib.sha256(file_bytes).hexdigest()

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
        return MemoUploadResponse(
            memo_id=existing.id,
            status=existing.status,
            message="Existing unprocessed memo found for this image."
        )

    # Store in S3 / MinIO / Local storage
    object_name = f"memos/{current_user.tenant_id}/{image_hash[:16]}_{filename}"
    storage_service.upload_bytes(file_bytes, object_name, content_type="image/jpeg")

    supp_uuid = uuid.UUID(supplier_id) if supplier_id else None
    memo = Memo(
        tenant_id=current_user.tenant_id,
        supplier_id=supp_uuid,
        image_s3_key=object_name,
        image_hash=image_hash,
        status="PROCESSING"
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)

    # Run extraction pipeline
    task_id = None
    try:
        from app.workers.tasks import extract_memo_task
        task = extract_memo_task.delay(str(memo.id))
        task_id = task.id
    except Exception:
        # Inline fallback for standalone web server execution
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
