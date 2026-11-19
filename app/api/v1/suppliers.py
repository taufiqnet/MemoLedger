import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.supplier import Supplier, SupplierProfile
from app.schemas.product import SupplierCreate, SupplierResponse

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=List[SupplierResponse])
def list_suppliers(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Supplier).filter(Supplier.tenant_id == current_user.tenant_id)
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))
    return query.all()


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier_in: SupplierCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    supplier = Supplier(
        tenant_id=current_user.tenant_id,
        name=supplier_in.name,
        phone=supplier_in.phone,
        address=supplier_in.address,
    )
    db.add(supplier)
    db.flush()

    # Create initial supplier profile
    profile = SupplierProfile(
        supplier_id=supplier.id,
        abbreviations={},
        column_conventions={},
    )
    db.add(profile)
    db.commit()
    db.refresh(supplier)
    return supplier
