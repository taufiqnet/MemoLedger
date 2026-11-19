from typing import TypedDict, List, Optional, Dict, Any
from decimal import Decimal


class RawLineRecord(TypedDict):
    line_number: int
    raw_text: str
    bbox: Optional[List[int]]  # [ymin, xmin, ymax, xmax] 0..1000
    script_tag: Optional[str]  # 'bn', 'en', 'mixed', 'digits_bn'


class StructuredLineRecord(TypedDict):
    line_number: int
    raw_text: str
    bbox: Optional[List[int]]
    script_tag: Optional[str]
    item_name_raw: str
    variant_raw: Optional[str]
    qty_raw: Optional[str]
    unit_raw: Optional[str]
    unit_price_raw: Optional[str]
    line_total_raw: Optional[str]
    notes_raw: Optional[str]
    flags: List[str]


class NormalizedLineRecord(TypedDict):
    line_number: int
    raw_text: str
    bbox: Optional[List[int]]
    script_tag: Optional[str]
    parsed_name: str
    parsed_variant: Optional[str]
    parsed_qty: Decimal
    parsed_unit: str
    parsed_unit_price: Optional[Decimal]
    parsed_line_total: Optional[Decimal]
    size_value: Optional[str]
    size_unit: Optional[str]
    flags: List[str]


class ReconciledLineRecord(TypedDict):
    line_number: int
    raw_text: str
    bbox: Optional[List[int]]
    script_tag: Optional[str]
    parsed_name: str
    parsed_variant: Optional[str]
    parsed_qty: Decimal
    parsed_unit: str
    parsed_unit_price: Decimal
    parsed_line_total: Decimal
    flags: List[str]


class ResolvedLineRecord(TypedDict):
    line_number: int
    raw_text: str
    bbox: Optional[List[int]]
    script_tag: Optional[str]
    parsed_name: str
    parsed_variant: Optional[str]
    parsed_qty: Decimal
    parsed_unit: str
    parsed_unit_price: Decimal
    parsed_line_total: Decimal
    matched_variant_id: Optional[str]
    matched_product_name: Optional[str]
    match_confidence: float
    status: str  # 'AUTO_MATCHED', 'SUGGESTION_NEEDED', 'MANUAL_ENTRY'
    suggestions: List[Dict[str, Any]]
    flags: List[str]


class MemoExtractionState(TypedDict):
    memo_id: str
    tenant_id: str
    supplier_id: Optional[str]
    image_bytes: bytes
    preprocessed_image_bytes: Optional[bytes]
    image_quality_report: Dict[str, Any]
    memo_number: Optional[str]
    memo_date: Optional[str]
    supplier_profile: Dict[str, Any]
    few_shot_examples: List[Dict[str, Any]]
    stage_a_raw_lines: List[RawLineRecord]
    stage_b_structured_lines: List[StructuredLineRecord]
    normalized_lines: List[NormalizedLineRecord]
    reconciled_lines: List[ReconciledLineRecord]
    resolved_lines: List[ResolvedLineRecord]
    extracted_total: Optional[Decimal]
    written_total: Optional[Decimal]
    total_mismatch_flag: bool
    review_flags: List[str]
    run_stats: Dict[str, Any]
