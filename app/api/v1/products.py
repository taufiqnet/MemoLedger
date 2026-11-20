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
    ProductUpdate,
    ProductResponse,
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    ProductBulkCreate,
    ProductSimpleCreate,
)
from decimal import Decimal
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
        name=product_in.name.strip(),
        short_name=product_in.short_name.strip() if product_in.short_name else None,
        brand=product_in.brand.strip() if product_in.brand else None,
        product_type=product_in.product_type,
        description=product_in.description,
    )
    db.add(product)
    db.flush()

    if product_in.variants:
        for v in product_in.variants:
            emb = vector_embedder.embed_text(f"{product.brand or ''} {product.name} {product.short_name or ''} {v.size_value or ''}{v.size_unit or ''} {v.variant_code or ''}")
            variant = ProductVariant(
                product_id=product.id,
                sku=v.sku or f"SKU-{uuid.uuid4().hex[:6].upper()}",
                size_value=v.size_value,
                size_unit=v.size_unit,
                variant_code=v.variant_code,
                cost_price=v.cost_price or Decimal("0.00"),
                retail_price=v.retail_price or Decimal("0.00"),
                current_stock=getattr(v, 'initial_stock', 0) or 0,
                embedding=emb,
            )
            db.add(variant)
    else:
        # Auto-create default variant for seamless matching and ledger tracking
        emb = vector_embedder.embed_text(f"{product.name} {product.short_name or ''}")
        variant = ProductVariant(
            product_id=product.id,
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            cost_price=Decimal("0.00"),
            retail_price=Decimal("0.00"),
            current_stock=0,
            embedding=emb,
        )
        db.add(variant)

    db.commit()
    db.refresh(product)
    return product


@router.post("/simple", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product_simple(
    product_in: ProductSimpleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    name = product_in.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Product name cannot be empty")

    short_name = product_in.short_name.strip() if product_in.short_name else None

    product = Product(
        tenant_id=current_user.tenant_id,
        name=name,
        short_name=short_name,
    )
    db.add(product)
    db.flush()

    emb = vector_embedder.embed_text(f"{product.name} {product.short_name or ''}")
    variant = ProductVariant(
        product_id=product.id,
        sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
        cost_price=product_in.cost_price or Decimal("0.00"),
        retail_price=product_in.retail_price or Decimal("0.00"),
        current_stock=0,
        embedding=emb,
    )
    db.add(variant)
    db.commit()
    db.refresh(product)
    return product


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_products(
    payload: ProductBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    created = []
    updated = []
    
    # Flatten names in case user passed a multi-line string or list
    raw_lines = []
    for item in payload.names:
        for sub in item.split("\n"):
            line = sub.strip()
            if line:
                raw_lines.append(line)

    for raw_line in raw_lines:
        # Support "Full Name - Short Name", "Full Name | Short Name", or "Full Name"
        full_name = raw_line
        short_name = raw_line

        if " - " in raw_line:
            parts = [p.strip() for p in raw_line.split(" - ", 1)]
            full_name = parts[0]
            short_name = parts[1] if len(parts) > 1 and parts[1] else parts[0]
        elif "|" in raw_line:
            parts = [p.strip() for p in raw_line.split("|", 1)]
            full_name = parts[0]
            short_name = parts[1] if len(parts) > 1 and parts[1] else parts[0]
        elif "-" in raw_line and not any(raw_line.endswith(suffix) for suffix in ["ml", "gm", "kg", "pc"]):
            parts = [p.strip() for p in raw_line.split("-", 1)]
            full_name = parts[0]
            short_name = parts[1] if len(parts) > 1 and parts[1] else parts[0]

        # Check if product with same name exists for this tenant
        existing = db.query(Product).filter(
            Product.tenant_id == current_user.tenant_id,
            Product.name.ilike(full_name)
        ).first()

        if existing:
            # Update short_name if provided
            existing.short_name = short_name
            if existing.variants:
                emb = vector_embedder.embed_text(f"{full_name} {short_name}")
                existing.variants[0].embedding = emb
            updated.append(f"{full_name} (Short: {short_name})")
            continue

        prod = Product(
            tenant_id=current_user.tenant_id,
            name=full_name,
            short_name=short_name,
        )
        db.add(prod)
        db.flush()

        emb = vector_embedder.embed_text(f"{full_name} {short_name}")
        var = ProductVariant(
            product_id=prod.id,
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            cost_price=Decimal("0.00"),
            retail_price=Decimal("0.00"),
            current_stock=0,
            embedding=emb,
        )
        db.add(var)
        created.append(f"{full_name} (Short: {short_name})")

    db.commit()
    return {
        "status": "SUCCESS",
        "created_count": len(created),
        "updated_count": len(updated),
        "created_items": created,
        "updated_items": updated,
    }


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: uuid.UUID,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product_update.name is not None:
        product.name = product_update.name
    if product_update.short_name is not None:
        product.short_name = product_update.short_name
    if product_update.brand is not None:
        product.brand = product_update.brand
    if product_update.product_type is not None:
        product.product_type = product_update.product_type
    if product_update.description is not None:
        product.description = product_update.description

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"status": "SUCCESS", "message": f"Product '{product.name}' deleted successfully."}


@router.post("/{product_id}/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
def add_product_variant(
    product_id: uuid.UUID,
    variant_in: ProductVariantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    emb = vector_embedder.embed_text(f"{product.brand or ''} {product.name} {variant_in.size_value or ''}{variant_in.size_unit or ''} {variant_in.variant_code or ''}")
    variant = ProductVariant(
        product_id=product.id,
        sku=variant_in.sku,
        size_value=variant_in.size_value,
        size_unit=variant_in.size_unit,
        variant_code=variant_in.variant_code,
        cost_price=variant_in.cost_price,
        retail_price=variant_in.retail_price,
        current_stock=variant_in.initial_stock,
        embedding=emb,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.put("/variants/{variant_id}", response_model=ProductVariantResponse)
def update_product_variant(
    variant_id: uuid.UUID,
    variant_update: ProductVariantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    variant = db.query(ProductVariant).join(Product).filter(
        ProductVariant.id == variant_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    if variant_update.sku is not None:
        variant.sku = variant_update.sku
    if variant_update.size_value is not None:
        variant.size_value = variant_update.size_value
    if variant_update.size_unit is not None:
        variant.size_unit = variant_update.size_unit
    if variant_update.variant_code is not None:
        variant.variant_code = variant_update.variant_code
    if variant_update.cost_price is not None:
        variant.cost_price = variant_update.cost_price
    if variant_update.retail_price is not None:
        variant.retail_price = variant_update.retail_price
    if variant_update.current_stock is not None:
        variant.current_stock = variant_update.current_stock

    # Re-embed if size or code changed
    product = variant.product
    variant.embedding = vector_embedder.embed_text(f"{product.brand or ''} {product.name} {variant.size_value or ''}{variant.size_unit or ''} {variant.variant_code or ''}")

    db.commit()
    db.refresh(variant)
    return variant


@router.delete("/variants/{variant_id}", status_code=status.HTTP_200_OK)
def delete_product_variant(
    variant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    variant = db.query(ProductVariant).join(Product).filter(
        ProductVariant.id == variant_id,
        Product.tenant_id == current_user.tenant_id
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    db.delete(variant)
    db.commit()
    return {"status": "SUCCESS", "message": "Variant deleted successfully."}


@router.get("/variants", response_model=List[ProductVariantResponse])
def list_variants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ProductVariant).join(Product).filter(Product.tenant_id == current_user.tenant_id).all()
