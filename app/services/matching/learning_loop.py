import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.memo import Memo, MemoLine, Correction
from app.models.product import ProductAlias, ProductVariant
from app.models.supplier import Supplier, SupplierProfile
from app.models.eval import EvalExample


class LearningLoopService:
    @staticmethod
    def record_correction(
        db: Session,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        memo_id: uuid.UUID,
        line_id: uuid.UUID,
        before_data: Dict[str, Any],
        after_data: Dict[str, Any]
    ) -> Correction:
        """
        Processes a manual correction from the review screen:
        1. Logs the correction.
        2. Creates or strengthens a supplier-scoped ProductAlias.
        3. Updates the SupplierProfile's abbreviations and correction rate.
        4. Saves an EvalExample into the golden dataset for continuous regression tests.
        """
        # 1. Log Correction
        correction = Correction(
            memo_id=memo_id,
            memo_line_id=line_id,
            user_id=user_id,
            before_data=before_data,
            after_data=after_data
        )
        db.add(correction)

        memo = db.query(Memo).filter(Memo.id == memo_id).first()
        supplier_id = memo.supplier_id if memo else None

        # 2. Update / Create Supplier-scoped Product Alias
        after_variant_id = after_data.get("matched_variant_id")
        raw_text = before_data.get("raw_text") or after_data.get("parsed_name")
        alias_candidate = before_data.get("parsed_name") or raw_text

        if after_variant_id and alias_candidate:
            variant_uuid = uuid.UUID(str(after_variant_id))
            # Check existing alias
            existing_alias = db.query(ProductAlias).filter(
                ProductAlias.tenant_id == tenant_id,
                ProductAlias.supplier_id == supplier_id,
                ProductAlias.alias_text.ilike(alias_candidate.strip())
            ).first()

            if existing_alias:
                existing_alias.product_variant_id = variant_uuid
                existing_alias.confidence = 1.0
                existing_alias.source = "MANUAL_CORRECTION"
            else:
                new_alias = ProductAlias(
                    tenant_id=tenant_id,
                    supplier_id=supplier_id,
                    product_variant_id=variant_uuid,
                    alias_text=alias_candidate.strip(),
                    confidence=1.0,
                    source="MANUAL_CORRECTION"
                )
                db.add(new_alias)

        # 3. Update SupplierProfile Abbreviations & Stats
        if supplier_id:
            profile = db.query(SupplierProfile).filter(SupplierProfile.supplier_id == supplier_id).first()
            if not profile:
                profile = SupplierProfile(supplier_id=supplier_id, abbreviations={}, total_memos_processed=1.0)
                db.add(profile)

            # Update abbreviations if name changed significantly
            old_name = (before_data.get("parsed_name") or "").strip()
            new_name = (after_data.get("parsed_name") or "").strip()
            if old_name and new_name and old_name.lower() != new_name.lower():
                abbrevs = dict(profile.abbreviations or {})
                abbrevs[old_name] = new_name
                profile.abbreviations = abbrevs

            # Update correction statistics
            total = float(profile.total_memos_processed or 1.0)
            prev_rate = float(profile.avg_correction_rate or 0.0)
            # Rolling average
            profile.avg_correction_rate = (prev_rate * 0.9) + 0.1

        # 4. Save into EvalExample for continuous evaluation
        eval_ex = EvalExample(
            supplier_id=supplier_id,
            memo_id=memo_id,
            category="real_correction",
            raw_input_data=before_data,
            ground_truth_data=after_data,
            is_verified=True
        )
        db.add(eval_ex)

        db.commit()
        return correction
