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
    initial_stock: Decimal = Decimal("0.00")


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = None
    size_value: Optional[str] = None
    size_unit: Optional[str] = None
    variant_code: Optional[str] = None
    cost_price: Optional[Decimal] = None
    retail_price: Optional[Decimal] = None
    current_stock: Optional[Decimal] = None


class ProductVariantResponse(ProductVariantBase):
    id: uuid.UUID
    product_id: uuid.UUID
    current_stock: Decimal

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    short_name: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None


class ProductCreate(ProductBase):
    variants: Optional[List[ProductVariantCreate]] = None


class ProductSimpleCreate(BaseModel):
    name: str
    short_name: Optional[str] = None
    cost_price: Optional[Decimal] = Decimal("0.00")
    retail_price: Optional[Decimal] = Decimal("0.00")


class ProductBulkCreate(BaseModel):
    names: List[str]


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None


class ProductResponse(ProductBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    short_name: Optional[str] = None
    variants: List[ProductVariantResponse] = []

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None


class SupplierCreate(SupplierBase):
    abbreviations: Optional[dict] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    abbreviations: Optional[dict] = None


class SupplierResponse(SupplierBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    abbreviations: Optional[dict] = None

    class Config:
        from_attributes = True
