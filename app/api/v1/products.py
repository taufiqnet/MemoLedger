import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductVariantCreate,
    ProductVariantResponse,
)
from app.services.matching.embeddings import vector_embedder

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.tenant_id == current_user.tenant_id)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    return query.all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = Product(
        tenant_id=current_user.tenant_id,
        name=product_in.name,
        brand=product_in.brand,
        product_type=product_in.product_type,
        description=product_in.description,
    )
    db.add(product)
    db.flush()

    if product_in.variants:
        for v in product_in.variants:
            emb = vector_embedder.embed_text(f"{product.brand or ''} {product.name} {v.size_value or ''}{v.size_unit or ''} {v.variant_code or ''}")
            variant = ProductVariant(
                product_id=product.id,
                sku=v.sku,
                size_value=v.size_value,
                size_unit=v.size_unit,
                variant_code=v.variant_code,
                cost_price=v.cost_price,
                retail_price=v.retail_price,
                embedding=emb,
            )
            db.add(variant)

    db.commit()
    db.refresh(product)
    return product


@router.get("/variants", response_model=List[ProductVariantResponse])
def list_variants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ProductVariant).join(Product).filter(Product.tenant_id == current_user.tenant_id).all()
