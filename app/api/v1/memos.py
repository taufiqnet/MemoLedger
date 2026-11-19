import io
import re
import uuid
import hashlib
from decimal import Decimal
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
    MemoLineCreate,
    MemoLineUpdate,
    MemoLinesSaveDraftRequest,
    MemoManualCreate,
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


@router.post("/manual", response_model=MemoUploadResponse, status_code=status.HTTP_201_CREATED)
def create_manual_memo(
    memo_in: MemoManualCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a manual memo with itemized lines without requiring camera/OCR.
    """
    memo_hash = hashlib.sha256(f"manual_{current_user.tenant_id}_{uuid.uuid4()}".encode()).hexdigest()
    memo = Memo(
        tenant_id=current_user.tenant_id,
        supplier_id=memo_in.supplier_id,
        memo_number=memo_in.memo_number or f"M-{uuid.uuid4().hex[:6].upper()}",
        memo_date=memo_in.memo_date,
        image_s3_key="memos/manual_entry.png",
        image_hash=memo_hash,
        status="REVIEW_REQUIRED"
    )
    db.add(memo)
    db.flush()

    total_sum = Decimal("0.00")
    for idx, l in enumerate(memo_in.lines, 1):
        line_total = l.parsed_line_total or (l.parsed_qty * l.parsed_unit_price)
        total_sum += line_total
        line = MemoLine(
            memo_id=memo.id,
            line_number=idx,
            raw_text=l.raw_text or f"{l.parsed_name} - {l.parsed_qty} - {l.parsed_unit_price}",
            parsed_name=l.parsed_name,
            parsed_variant=l.parsed_variant,
            parsed_qty=l.parsed_qty,
            parsed_unit=l.parsed_unit or "piece",
            parsed_unit_price=l.parsed_unit_price,
            parsed_line_total=line_total,
            matched_variant_id=l.matched_variant_id,
            status="AUTO_MATCHED" if l.matched_variant_id else "NEEDS_REVIEW"
        )
        db.add(line)

    memo.extracted_total = total_sum
    memo.written_total = total_sum
    db.commit()
    db.refresh(memo)

    return MemoUploadResponse(
        memo_id=memo.id,
        status=memo.status,
        message="Manual memo created successfully."
    )


@router.put("/{memo_id}/lines")
def save_memo_lines_draft(
    memo_id: uuid.UUID,
    draft_data: MemoLinesSaveDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves draft updates to memo lines and totals without committing to stock ledger.
    """
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    if memo.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify lines for an already approved memo. This memo has already been committed to the inventory ledger."
        )

    # Optional metadata updates
    if draft_data.supplier_id is not None:
        memo.supplier_id = draft_data.supplier_id
    if draft_data.memo_number is not None:
        memo.memo_number = draft_data.memo_number
    if draft_data.memo_date is not None:
        memo.memo_date = draft_data.memo_date

    total_sum = Decimal("0.00")
    for l_update in draft_data.lines:
        line = None
        if l_update.id:
            line = db.query(MemoLine).filter(MemoLine.id == l_update.id, MemoLine.memo_id == memo.id).first()
        
        if line:
            if l_update.parsed_name is not None:
                line.parsed_name = l_update.parsed_name
            if l_update.parsed_variant is not None:
                line.parsed_variant = l_update.parsed_variant
            if l_update.parsed_qty is not None:
                line.parsed_qty = l_update.parsed_qty
            if l_update.parsed_unit_price is not None:
                line.parsed_unit_price = l_update.parsed_unit_price
            if l_update.parsed_line_total is not None:
                line.parsed_line_total = l_update.parsed_line_total
            else:
                line.parsed_line_total = line.parsed_qty * (line.parsed_unit_price or Decimal("0.00"))
            if l_update.matched_variant_id is not None:
                line.matched_variant_id = l_update.matched_variant_id
            total_sum += line.parsed_line_total
        else:
            # New line item
            line_tot = l_update.parsed_line_total or (l_update.parsed_qty * l_update.parsed_unit_price)
            new_line = MemoLine(
                memo_id=memo.id,
                line_number=l_update.line_number or (len(memo.lines) + 1),
                raw_text=l_update.raw_text or f"{l_update.parsed_name}",
                parsed_name=l_update.parsed_name,
                parsed_variant=l_update.parsed_variant,
                parsed_qty=l_update.parsed_qty,
                parsed_unit=l_update.parsed_unit or "piece",
                parsed_unit_price=l_update.parsed_unit_price,
                parsed_line_total=line_tot,
                matched_variant_id=l_update.matched_variant_id,
                status=l_update.status or "AUTO_MATCHED"
            )
            db.add(new_line)
            total_sum += line_tot

    memo.extracted_total = total_sum
    if draft_data.written_total is not None:
        memo.written_total = draft_data.written_total
    
    # Recalculate mismatch
    if memo.written_total is not None and abs(float(memo.extracted_total) - float(memo.written_total)) > 0.5:
        memo.total_mismatch_flag = True
    else:
        memo.total_mismatch_flag = False

    db.commit()
    db.refresh(memo)
    return {
        "status": "SUCCESS",
        "message": "Memo draft lines saved successfully.",
        "extracted_total": float(memo.extracted_total),
        "total_mismatch_flag": memo.total_mismatch_flag,
        "lines": [
            {
                "id": str(l.id),
                "line_number": l.line_number,
                "parsed_name": l.parsed_name,
                "parsed_line_total": float(l.parsed_line_total or 0)
            }
            for l in memo.lines
        ]
    }


@router.post("/{memo_id}/lines")
def add_memo_line(
    memo_id: uuid.UUID,
    line_in: MemoLineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memo = db.query(Memo).filter(
        Memo.id == memo_id,
        Memo.tenant_id == current_user.tenant_id
    ).first()
    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    line_tot = line_in.parsed_line_total or (line_in.parsed_qty * line_in.parsed_unit_price)
    next_num = len(memo.lines) + 1
    new_line = MemoLine(
        memo_id=memo.id,
        line_number=next_num,
        raw_text=line_in.raw_text or f"{line_in.parsed_name} - {line_in.parsed_qty} - {line_in.parsed_unit_price}",
        parsed_name=line_in.parsed_name,
        parsed_variant=line_in.parsed_variant,
        parsed_qty=line_in.parsed_qty,
        parsed_unit=line_in.parsed_unit or "piece",
        parsed_unit_price=line_in.parsed_unit_price,
        parsed_line_total=line_tot,
        matched_variant_id=line_in.matched_variant_id,
        status="AUTO_MATCHED" if line_in.matched_variant_id else "NEEDS_REVIEW"
    )
    db.add(new_line)
    memo.extracted_total = (memo.extracted_total or Decimal("0.00")) + line_tot
    db.commit()
    db.refresh(new_line)
    return {
        "status": "SUCCESS",
        "line_id": str(new_line.id),
        "line_number": new_line.line_number,
        "message": "Line item added."
    }


@router.delete("/{memo_id}/lines/{line_id}")
def delete_memo_line(
    memo_id: uuid.UUID,
    line_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    line = db.query(MemoLine).filter(MemoLine.id == line_id, MemoLine.memo_id == memo_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Memo line not found")

    memo = line.memo
    memo.extracted_total = max(Decimal("0.00"), (memo.extracted_total or Decimal("0.00")) - (line.parsed_line_total or Decimal("0.00")))
    db.delete(line)
    db.commit()
    return {"status": "SUCCESS", "message": "Line deleted.", "extracted_total": float(memo.extracted_total)}


@router.delete("/{memo_id}", status_code=status.HTTP_200_OK)
def delete_memo(
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
    if memo.status == "APPROVED":
        raise HTTPException(status_code=400, detail="Cannot delete an already approved memo that updated inventory.")

    db.delete(memo)
    db.commit()
    return {"status": "SUCCESS", "message": "Memo deleted successfully."}


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
