import uuid
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel


class ProductVariantBase(BaseModel):
    sku: Optional[str] = None
    size_value: Optional[str] = None
    size_unit: Optional[str] = None
    variant_code: Optional[str] = None
    cost_price: Decimal = Decimal("0.00")
    retail_price: Decimal = Decimal("0.00")


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantResponse(ProductVariantBase):
    id: uuid.UUID
    product_id: uuid.UUID
    current_stock: Decimal

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    variants: Optional[List[ProductVariantCreate]] = None


class ProductResponse(ProductBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    variants: List[ProductVariantResponse] = []

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: uuid.UUID
    tenant_id: uuid.UUID

    class Config:
        from_attributes = True
