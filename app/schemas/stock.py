import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StockAdjustmentCreate(BaseModel):
    variant_id: uuid.UUID
    movement_type: str = "INVENTORY_ADJUSTMENT"  # PURCHASE_RECEIPT, SALE, INVENTORY_ADJUSTMENT, RETURN
    quantity_change: Decimal
    unit_cost: Optional[Decimal] = Decimal("0.00")
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: uuid.UUID
    product_variant_id: uuid.UUID
    memo_id: Optional[uuid.UUID] = None
    movement_type: str
    quantity_change: Decimal
    running_balance: Decimal
    unit_cost: Decimal
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StockSummaryItem(BaseModel):
    variant_id: uuid.UUID
    product_name: str
    brand: Optional[str] = None
    size_value: Optional[str] = None
    size_unit: Optional[str] = None
    variant_code: Optional[str] = None
    current_stock: Decimal
    cost_price: Decimal
    retail_price: Decimal
