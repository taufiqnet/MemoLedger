from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.memo import Memo
from app.models.stock import StockMovement
from app.models.product import ProductVariant

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total_memos = db.query(func.count(Memo.id)).filter(
        Memo.tenant_id == current_user.tenant_id
    ).scalar() or 0

    pending_review = db.query(func.count(Memo.id)).filter(
        Memo.tenant_id == current_user.tenant_id,
        Memo.status == "REVIEW_REQUIRED"
    ).scalar() or 0

    total_spent = db.query(func.sum(Memo.extracted_total)).filter(
        Memo.tenant_id == current_user.tenant_id,
        Memo.status == "APPROVED"
    ).scalar() or 0

    low_stock_count = db.query(func.count(ProductVariant.id)).join(ProductVariant.product).filter(
        ProductVariant.product.has(tenant_id=current_user.tenant_id),
        ProductVariant.current_stock <= 5
    ).scalar() or 0

    return {
        "total_memos": total_memos,
        "pending_review": pending_review,
        "total_spent_bdt": float(total_spent),
        "low_stock_count": low_stock_count
    }
