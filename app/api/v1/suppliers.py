import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.supplier import Supplier, SupplierProfile
from app.schemas.product import SupplierCreate, SupplierUpdate, SupplierResponse

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
    suppliers = query.all()
    res = []
    for s in suppliers:
        abbr = s.profile.abbreviations if s.profile else {}
        res.append(SupplierResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            name=s.name,
            phone=s.phone,
            address=s.address,
            abbreviations=abbr
        ))
    return res


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
        abbreviations=supplier_in.abbreviations or {},
        column_conventions={},
    )
    db.add(profile)
    db.commit()
    db.refresh(supplier)
    return SupplierResponse(
        id=supplier.id,
        tenant_id=supplier.tenant_id,
        name=supplier.name,
        phone=supplier.phone,
        address=supplier.address,
        abbreviations=profile.abbreviations
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.tenant_id == current_user.tenant_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    abbr = supplier.profile.abbreviations if supplier.profile else {}
    return SupplierResponse(
        id=supplier.id,
        tenant_id=supplier.tenant_id,
        name=supplier.name,
        phone=supplier.phone,
        address=supplier.address,
        abbreviations=abbr
    )


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: uuid.UUID,
    supplier_update: SupplierUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.tenant_id == current_user.tenant_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if supplier_update.name is not None:
        supplier.name = supplier_update.name
    if supplier_update.phone is not None:
        supplier.phone = supplier_update.phone
    if supplier_update.address is not None:
        supplier.address = supplier_update.address

    if supplier_update.abbreviations is not None:
        if not supplier.profile:
            supplier.profile = SupplierProfile(supplier_id=supplier.id, abbreviations={}, column_conventions={})
            db.add(supplier.profile)
        # Update or merge abbreviations
        current_abbr = dict(supplier.profile.abbreviations or {})
        current_abbr.update(supplier_update.abbreviations)
        supplier.profile.abbreviations = current_abbr

    db.commit()
    db.refresh(supplier)
    abbr = supplier.profile.abbreviations if supplier.profile else {}
    return SupplierResponse(
        id=supplier.id,
        tenant_id=supplier.tenant_id,
        name=supplier.name,
        phone=supplier.phone,
        address=supplier.address,
        abbreviations=abbr
    )


@router.delete("/{supplier_id}", status_code=status.HTTP_200_OK)
def delete_supplier(
    supplier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.tenant_id == current_user.tenant_id
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    db.commit()
    return {"status": "SUCCESS", "message": f"Supplier '{supplier.name}' deleted successfully."}
