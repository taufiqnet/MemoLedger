import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = Column(Uuid(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    memo_id = Column(Uuid(as_uuid=True), ForeignKey("memos.id", ondelete="SET NULL"), nullable=True, index=True)
    
    movement_type = Column(String(50), nullable=False, index=True)
    
    quantity_change = Column(Numeric(12, 2), nullable=False)
    running_balance = Column(Numeric(12, 2), nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="stock_movements")
    variant = relationship("ProductVariant", back_populates="stock_movements")
    memo = relationship("Memo", back_populates="stock_movements")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = Column(Uuid(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    supplier = relationship("Supplier", back_populates="price_history")
    variant = relationship("ProductVariant", back_populates="price_history")
