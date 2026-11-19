import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="suppliers")
    profile = relationship("SupplierProfile", back_populates="supplier", uselist=False, cascade="all, delete-orphan")
    aliases = relationship("ProductAlias", back_populates="supplier", cascade="all, delete-orphan")
    memos = relationship("Memo", back_populates="supplier")
    price_history = relationship("PriceHistory", back_populates="supplier", cascade="all, delete-orphan")


class SupplierProfile(Base):
    __tablename__ = "supplier_profiles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), unique=True, nullable=False)
    column_conventions = Column(JSON, default=dict)
    abbreviations = Column(JSON, default=dict)
    typical_price_ranges = Column(JSON, default=dict)
    avg_correction_rate = Column(Float, default=0.0)
    total_memos_processed = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="profile")
