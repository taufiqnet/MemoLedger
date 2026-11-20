import uuid
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class MemoLineCreate(BaseModel):
    raw_text: Optional[str] = ""
    parsed_name: str
    parsed_variant: Optional[str] = None
    parsed_qty: Decimal = Decimal("1.00")
    parsed_unit: str = "piece"
    parsed_unit_price: Decimal = Decimal("0.00")
    parsed_line_total: Decimal = Decimal("0.00")
    matched_variant_id: Optional[uuid.UUID] = None


class MemoLineUpdate(BaseModel):
    id: Optional[uuid.UUID] = None
    line_number: Optional[int] = None
    raw_text: Optional[str] = None
    parsed_name: Optional[str] = None
    parsed_variant: Optional[str] = None
    parsed_qty: Decimal = Decimal("1.00")
    parsed_unit: str = "piece"
    parsed_unit_price: Decimal = Decimal("0.00")
    parsed_line_total: Decimal = Decimal("0.00")
    matched_variant_id: Optional[uuid.UUID] = None
    status: Optional[str] = "AUTO_MATCHED"


class MemoLinesSaveDraftRequest(BaseModel):
    lines: List[MemoLineUpdate]
    written_total: Optional[Decimal] = None
    supplier_id: Optional[uuid.UUID] = None
    memo_number: Optional[str] = None
    memo_date: Optional[str] = None


class MemoManualCreate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    memo_number: Optional[str] = None
    memo_date: Optional[str] = None
    lines: List[MemoLineCreate] = []


class MemoLineResponse(BaseModel):
    id: uuid.UUID
    line_number: int
    bbox: Optional[List[int]] = None
    script_tag: Optional[str] = None
    raw_text: str
    parsed_name: Optional[str] = None
    parsed_variant: Optional[str] = None
    parsed_qty: Decimal
    parsed_unit: str
    parsed_unit_price: Optional[Decimal] = None
    parsed_line_total: Optional[Decimal] = None
    matched_variant_id: Optional[uuid.UUID] = None
    match_confidence: float
    status: str
    anomaly_flags: List[str] = []

    class Config:
        from_attributes = True


class MemoDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    memo_number: Optional[str] = None
    memo_date: Optional[str] = None
    image_s3_key: str
    image_hash: str
    status: str
    image_quality_report: Dict[str, Any] = {}
    extracted_total: Optional[Decimal] = None
    written_total: Optional[Decimal] = None
    total_mismatch_flag: bool = False
    lines: List[MemoLineResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MemoCommitRequest(BaseModel):
    lines: Optional[List[MemoLineUpdate]] = None
    total_amount: Optional[Decimal] = None
    written_total: Optional[Decimal] = None
    notes: Optional[str] = None


class MemoUploadResponse(BaseModel):
    memo_id: uuid.UUID
    task_id: Optional[str] = None
    status: str
    message: str
