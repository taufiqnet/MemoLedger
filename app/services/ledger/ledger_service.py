import uuid
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select
from fastapi import HTTPException, status
from app.models.stock import StockMovement, PriceHistory
from app.models.product import ProductVariant
from app.models.memo import Memo, MemoLine
from app.models.audit import AuditLog


class LedgerService:
    @staticmethod
    def record_movement(
        db: Session,
        tenant_id: uuid.UUID,
        variant_id: uuid.UUID,
        movement_type: str,
        quantity_change: Decimal,
        unit_cost: Decimal,
        memo_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """
        Atomically records an immutable entry in the stock ledger.
        Updates the product variant's cached current_stock and cost_price.
        """
        # Fetch variant with row-level lock where possible
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == variant_id
        ).with_for_update().first()
        
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product variant {variant_id} not found."
            )

        new_balance = Decimal(str(variant.current_stock)) + Decimal(str(quantity_change))

        # Create immutable stock ledger entry
        movement = StockMovement(
            tenant_id=tenant_id,
            product_variant_id=variant_id,
            memo_id=memo_id,
            movement_type=movement_type,
            quantity_change=Decimal(str(quantity_change)),
            running_balance=new_balance,
            unit_cost=Decimal(str(unit_cost)),
            notes=notes,
        )
        db.add(movement)

        # Update cached variant fields
        variant.current_stock = new_balance
        if movement_type == "PURCHASE_RECEIPT" and unit_cost > 0:
            variant.cost_price = Decimal(str(unit_cost))

        return movement

    @staticmethod
    def check_duplicate_memo(db: Session, tenant_id: uuid.UUID, image_hash: str, memo_id: Optional[uuid.UUID] = None) -> bool:
        """
        Checks if an identical image hash has already been approved for this tenant.
        """
        query = db.query(Memo).filter(
            Memo.tenant_id == tenant_id,
            Memo.image_hash == image_hash,
            Memo.status == "APPROVED"
        )
        if memo_id:
            query = query.filter(Memo.id != memo_id)
        return query.first() is not None

    @staticmethod
    def check_anomalies(
        db: Session,
        tenant_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID],
        variant_id: uuid.UUID,
        unit_price: Decimal,
        quantity: Decimal,
    ) -> List[str]:
        """
        Detects price spikes (>30% variance against history) and unusual quantities (>5x average).
        """
        flags: List[str] = []

        # Price check against recent price history for this supplier/variant
        if supplier_id and unit_price > 0:
            recent_prices = db.query(PriceHistory.unit_price).filter(
                PriceHistory.tenant_id == tenant_id,
                PriceHistory.supplier_id == supplier_id,
                PriceHistory.product_variant_id == variant_id
            ).order_by(desc(PriceHistory.observed_at)).limit(5).all()

            if recent_prices:
                avg_price = sum(Decimal(str(p[0])) for p in recent_prices) / len(recent_prices)
                if avg_price > 0:
                    pct_diff = abs(unit_price - avg_price) / avg_price
                    if pct_diff > Decimal("0.30"):
                        flags.append(f"PRICE_SPIKE_DETECTED ({pct_diff*100:.1f}% deviation from historical ৳{avg_price:.2f})")

        # Quantity check against recent purchases
        if quantity > 0:
            recent_qty = db.query(StockMovement.quantity_change).filter(
                StockMovement.tenant_id == tenant_id,
                StockMovement.product_variant_id == variant_id,
                StockMovement.movement_type == "PURCHASE_RECEIPT"
            ).order_by(desc(StockMovement.created_at)).limit(5).all()

            if recent_qty:
                avg_qty = sum(Decimal(str(q[0])) for q in recent_qty) / len(recent_qty)
                if avg_qty > 0 and quantity > (avg_qty * Decimal("5.0")):
                    flags.append(f"UNUSUAL_LARGE_QUANTITY ({quantity} units vs historical average of {avg_qty:.1f})")

        return flags

    @staticmethod
    def commit_memo(
        db: Session,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        memo_id: uuid.UUID,
        lines_data: Optional[List[dict]] = None
    ) -> Memo:
        """
        Approves a memo and commits all lines to the append-only stock ledger.
        """
        memo = db.query(Memo).filter(
            Memo.id == memo_id,
            Memo.tenant_id == tenant_id
        ).first()

        if not memo:
            raise HTTPException(status_code=404, detail="Memo not found")

        if memo.status == "APPROVED":
            raise HTTPException(status_code=400, detail="Memo is already approved and committed to ledger")

        # Check duplicate memo by image hash
        if LedgerService.check_duplicate_memo(db, tenant_id, memo.image_hash, memo_id=memo.id):
            raise HTTPException(
                status_code=400,
                detail="Duplicate memo rejected: An approved memo with this exact image hash already exists."
            )

        # Update line records if updated lines were submitted
        if lines_data:
            line_map = {line.id: line for line in memo.lines}
            for item in lines_data:
                raw_id = item.get("id")
                line_id = None
                if raw_id:
                    try:
                        line_id = uuid.UUID(str(raw_id))
                    except (ValueError, TypeError):
                        line_id = None
                if line_id and line_id in line_map:
                    line = line_map[line_id]
                    line.parsed_name = item.get("parsed_name", line.parsed_name)
                    line.parsed_variant = item.get("parsed_variant", line.parsed_variant)
                    line.parsed_qty = Decimal(str(item.get("parsed_qty", line.parsed_qty)))
                    line.parsed_unit = item.get("parsed_unit", line.parsed_unit)
                    line.parsed_unit_price = Decimal(str(item.get("parsed_unit_price", line.parsed_unit_price or 0)))
                    line.parsed_line_total = Decimal(str(item.get("parsed_line_total", line.parsed_line_total or 0)))
                    if item.get("matched_variant_id"):
                        try:
                            line.matched_variant_id = uuid.UUID(str(item["matched_variant_id"]))
                        except (ValueError, TypeError):
                            pass
                    line.status = item.get("status", "AUTO_MATCHED")

        # Post movements to the stock ledger for every line with a matched variant
        for line in memo.lines:
            if line.matched_variant_id and line.parsed_qty > 0:
                # Check for anomalies to record in audit/notes
                unit_price = Decimal(str(line.parsed_unit_price or 0))
                anomalies = LedgerService.check_anomalies(
                    db,
                    tenant_id,
                    memo.supplier_id,
                    line.matched_variant_id,
                    unit_price,
                    Decimal(str(line.parsed_qty))
                )
                line.anomaly_flags = anomalies

                # Create stock movement
                LedgerService.record_movement(
                    db=db,
                    tenant_id=tenant_id,
                    variant_id=line.matched_variant_id,
                    movement_type="PURCHASE_RECEIPT",
                    quantity_change=Decimal(str(line.parsed_qty)),
                    unit_cost=unit_price,
                    memo_id=memo.id,
                    notes=f"Memo #{memo.memo_number or 'N/A'} - Line {line.line_number}: {line.parsed_name or line.raw_text}"
                )

                # Record supplier price history
                if memo.supplier_id and unit_price > 0:
                    price_entry = PriceHistory(
                        tenant_id=tenant_id,
                        supplier_id=memo.supplier_id,
                        product_variant_id=line.matched_variant_id,
                        unit_price=unit_price,
                    )
                    db.add(price_entry)

        # Mark memo as approved
        memo.status = "APPROVED"

        # Log audit trail
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="APPROVE_MEMO",
            resource_type="Memo",
            resource_id=str(memo.id),
            details={"memo_number": memo.memo_number, "line_count": len(memo.lines)}
        )
        db.add(audit)
        db.commit()
        db.refresh(memo)
        return memo
