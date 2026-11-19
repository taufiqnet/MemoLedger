import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Float, JSON, Uuid
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(384)
except ImportError:
    class MockVector(TypeDecorator):
        impl = JSON
        cache_ok = True
    VectorType = MockVector()


class Product(Base):
    __tablename__ = "products"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=True, index=True)
    product_type = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String(100), nullable=True, index=True)
    size_value = Column(String(50), nullable=True)
    size_unit = Column(String(50), nullable=True)
    variant_code = Column(String(50), nullable=True)
    cost_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    retail_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    current_stock = Column(Numeric(12, 2), default=0.00, nullable=False)
    embedding = Column(VectorType, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="variants")
    aliases = relationship("ProductAlias", back_populates="variant", cascade="all, delete-orphan")
    memo_lines = relationship("MemoLine", back_populates="matched_variant")
    stock_movements = relationship("StockMovement", back_populates="variant", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="variant", cascade="all, delete-orphan")


class ProductAlias(Base):
    __tablename__ = "product_aliases"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True, index=True)
    product_variant_id = Column(Uuid(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_text = Column(String(255), nullable=False, index=True)
    confidence = Column(Float, default=1.0, nullable=False)
    source = Column(String(50), default="MANUAL_CORRECTION")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    supplier = relationship("Supplier", back_populates="aliases")
    variant = relationship("ProductVariant", back_populates="aliases")
