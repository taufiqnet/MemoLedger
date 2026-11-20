import uuid
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.extraction.state import MemoExtractionState
from app.services.imaging.preprocessor import ImagePreprocessor
from app.services.extraction.llm_provider import get_vision_provider
from app.services.extraction.normalizer import Normalizer
from app.services.extraction.arithmetic import ArithmeticReconciler
from app.services.matching.resolver import ProductResolver
from app.models.supplier import Supplier, SupplierProfile
from app.models.memo import Memo, MemoLine, ExtractionRun
from app.models.product import ProductVariant


class MemoExtractionPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = get_vision_provider()

    def run(self, memo_id: uuid.UUID) -> Memo:
        """
        Executes the full pipeline for a given Memo record.
        """
        start_time = time.time()
        memo = self.db.query(Memo).filter(Memo.id == memo_id).first()
        if not memo:
            raise ValueError(f"Memo {memo_id} not found")

        # 1. Fetch raw image bytes from storage
        from app.services.storage import storage_service
        raw_image_bytes = storage_service.get_bytes(memo.image_s3_key)

        # 2. Server-side OpenCV Preprocessing
        enhanced_bytes, quality_report = ImagePreprocessor.process_image(raw_image_bytes)
        memo.image_quality_report = quality_report

        # 3. Retrieve Supplier Profile & Context
        supplier_profile_data = {}
        few_shot_examples = []
        if memo.supplier_id:
            profile = self.db.query(SupplierProfile).filter(SupplierProfile.supplier_id == memo.supplier_id).first()
            if profile:
                supplier_profile_data = {
                    "abbreviations": profile.abbreviations,
                    "column_conventions": profile.column_conventions,
                    "typical_price_ranges": profile.typical_price_ranges,
                }

        # 4. Stage A: Verbatim Transcription
        stage_a_result = self.llm_provider.extract_memo_stage_a(enhanced_bytes)
        raw_lines = stage_a_result.get("lines", [])
        
        # Populate header info if detected
        header = stage_a_result.get("supplier_header", {})
        if header.get("memo_number") and not memo.memo_number:
            memo.memo_number = Normalizer.bengali_to_english_digits(str(header["memo_number"]))
        if header.get("memo_date") and not memo.memo_date:
            memo.memo_date = Normalizer.bengali_to_english_digits(str(header["memo_date"]))

        # Check if supplier can be linked by name from header
        if not memo.supplier_id and header.get("name"):
            header_name = header["name"].strip()
            matched_supplier = self.db.query(Supplier).filter(
                Supplier.tenant_id == memo.tenant_id,
                Supplier.name.ilike(f"%{header_name}%")
            ).first()
            if matched_supplier:
                memo.supplier_id = matched_supplier.id

        # 5. Stage B: Layout-Agnostic Structuring
        stage_b_result = self.llm_provider.extract_memo_stage_b(
            raw_lines=raw_lines,
            supplier_profile=supplier_profile_data,
            few_shot_examples=few_shot_examples
        )
        structured_lines = stage_b_result.get("structured_lines", [])
        written_total_raw = stage_b_result.get("written_total_raw") or stage_a_result.get("written_total_raw")
        written_total = Normalizer.clean_amount(written_total_raw)
        memo.written_total = written_total

        # 6. Normalisation Engine
        normalized_lines = []
        supplier_abbrevs = supplier_profile_data.get("abbreviations", {})
        for s_line in structured_lines:
            norm = Normalizer.normalize_line(
                raw_text=s_line["raw_text"],
                parsed_name=s_line.get("item_name_raw"),
                parsed_variant=s_line.get("variant_raw"),
                raw_qty=s_line.get("qty_raw"),
                raw_unit=s_line.get("unit_raw"),
                raw_unit_price=s_line.get("unit_price_raw"),
                raw_line_total=s_line.get("line_total_raw"),
                supplier_abbrevs=supplier_abbrevs,
            )
            merged = {**s_line, **norm}
            normalized_lines.append(merged)

        # 7. Arithmetic Reconciliation
        reconciled_lines, calculated_total, total_mismatch, global_flags = ArithmeticReconciler.reconcile_memo(
            lines=normalized_lines,
            written_total=written_total
        )
        memo.extracted_total = calculated_total
        memo.total_mismatch_flag = total_mismatch

        # 8. Hybrid Product Resolver
        # Clear any existing lines (in case of rerun)
        self.db.query(MemoLine).filter(MemoLine.memo_id == memo.id).delete()

        for idx, r_line in enumerate(reconciled_lines, start=1):
            resolution = ProductResolver.resolve_line(
                db=self.db,
                tenant_id=memo.tenant_id,
                supplier_id=memo.supplier_id,
                parsed_name=r_line["parsed_name"],
                parsed_variant=r_line.get("parsed_variant"),
                size_value=r_line.get("size_value"),
                size_unit=r_line.get("size_unit"),
                unit_price=r_line.get("parsed_unit_price"),
            )

            all_flags = list(r_line.get("flags", [])) + list(resolution.get("flags", []))

            matched_id = None
            if resolution.get("matched_variant_id"):
                matched_id = uuid.UUID(str(resolution["matched_variant_id"]))

            # If matched against product database, use the official clean product name
            final_name = r_line["parsed_name"]
            if resolution.get("matched_variant_id") and resolution.get("matched_clean_name"):
                final_name = resolution["matched_clean_name"]

            unit_price = r_line.get("parsed_unit_price")
            line_total = r_line.get("parsed_line_total")
            qty = r_line.get("parsed_qty") or Decimal("1.00")

            # Fallback to catalog variant price if extracted price is 0 or None
            if (unit_price is None or unit_price == 0) and matched_id:
                var = self.db.query(ProductVariant).filter(ProductVariant.id == matched_id).first()
                if var and var.cost_price and var.cost_price > 0:
                    unit_price = var.cost_price
                    line_total = qty * unit_price

            line_obj = MemoLine(
                memo_id=memo.id,
                line_number=idx,
                bbox=r_line.get("bbox"),
                script_tag=r_line.get("script_tag"),
                raw_text=r_line["raw_text"],
                parsed_name=final_name,
                parsed_variant=r_line.get("parsed_variant"),
                parsed_qty=qty,
                parsed_unit=r_line["parsed_unit"],
                parsed_unit_price=unit_price,
                parsed_line_total=line_total,
                matched_variant_id=matched_id,
                match_confidence=resolution.get("match_confidence", 0.0),
                status=resolution.get("status", "MANUAL_ENTRY"),
                anomaly_flags=all_flags,
            )
            self.db.add(line_obj)

        memo.status = "REVIEW_REQUIRED"
        
        # 9. Record Execution Run telemetry
        latency_ms = int((time.time() - start_time) * 1000)
        run_record = ExtractionRun(
            memo_id=memo.id,
            model_name=getattr(self.llm_provider, "__class__", type).__name__,
            prompt_version="v1.2-bilingual-structured",
            cost_usd=Decimal("0.0015"),
            latency_ms=latency_ms,
            langfuse_trace_id=str(uuid.uuid4())
        )
        self.db.add(run_record)

        self.db.commit()
        self.db.refresh(memo)
        return memo
