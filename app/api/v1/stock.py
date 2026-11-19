import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.stock import StockMovement
from app.models.product import ProductVariant, Product
from app.schemas.stock import StockMovementResponse, StockSummaryItem, StockAdjustmentCreate
from app.services.ledger.ledger_service import LedgerService

router = APIRouter(prefix="/stock", tags=["Stock Ledger"])


@router.get("/ledger", response_model=List[StockMovementResponse])
def get_stock_ledger(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the immutable append-only stock movements.
    """
    return db.query(StockMovement).filter(
        StockMovement.tenant_id == current_user.tenant_id
    ).order_by(desc(StockMovement.created_at)).limit(limit).all()


@router.get("/summary", response_model=List[StockSummaryItem])
def get_stock_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns current stock levels for all product variants with low-stock alerts.
    """
    variants = db.query(ProductVariant).join(Product).filter(
        Product.tenant_id == current_user.tenant_id
    ).all()

    summary = []
    for v in variants:
        summary.append(StockSummaryItem(
            variant_id=v.id,
            product_name=v.product.name,
            brand=v.product.brand,
            size_value=v.size_value,
            size_unit=v.size_unit,
            variant_code=v.variant_code,
            current_stock=v.current_stock,
            cost_price=v.cost_price,
            retail_price=v.retail_price,
        ))
    return summary


@router.post("/adjust", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def adjust_stock(
    adj: StockAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records a manual stock adjustment, sale, or receipt and updates running balance atomically.
    """
    variant = db.query(ProductVariant).join(Product).filter(
        ProductVariant.id == adj.variant_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Product variant not found")

    movement = LedgerService.record_movement(
        db=db,
        tenant_id=current_user.tenant_id,
        variant_id=adj.variant_id,
        movement_type=adj.movement_type,
        quantity_change=adj.quantity_change,
        unit_cost=adj.unit_cost or variant.cost_price,
        notes=adj.notes or "Manual Stock Adjustment"
    )
    db.commit()
    db.refresh(movement)
    return movement
