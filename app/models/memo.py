import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text, Uuid
from sqlalchemy.orm import relationship
from app.core.database import Base


class Memo(Base):
    __tablename__ = "memos"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Uuid(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    memo_number = Column(String(100), nullable=True)
    memo_date = Column(String(100), nullable=True)
    image_s3_key = Column(String(500), nullable=False)
    image_hash = Column(String(64), nullable=False, index=True)
    status = Column(String(50), default="PROCESSING", nullable=False, index=True)
    
    image_quality_report = Column(JSON, default=dict)
    
    extracted_total = Column(Numeric(12, 2), nullable=True)
    written_total = Column(Numeric(12, 2), nullable=True)
    total_mismatch_flag = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="memos")
    supplier = relationship("Supplier", back_populates="memos")
    lines = relationship("MemoLine", back_populates="memo", cascade="all, delete-orphan", order_by="MemoLine.line_number")
    corrections = relationship("Correction", back_populates="memo", cascade="all, delete-orphan")
    extraction_runs = relationship("ExtractionRun", back_populates="memo", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="memo")


class MemoLine(Base):
    __tablename__ = "memo_lines"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memo_id = Column(Uuid(as_uuid=True), ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    
    bbox = Column(JSON, nullable=True)
    script_tag = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=False)
    
    parsed_name = Column(String(255), nullable=True)
    parsed_variant = Column(String(100), nullable=True)
    parsed_qty = Column(Numeric(10, 2), default=1.00, nullable=False)
    parsed_unit = Column(String(50), default="piece", nullable=False)
    parsed_unit_price = Column(Numeric(12, 2), nullable=True)
    parsed_line_total = Column(Numeric(12, 2), nullable=True)
    
    matched_variant_id = Column(Uuid(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    match_confidence = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="AUTO_MATCHED", nullable=False)
    
    anomaly_flags = Column(JSON, default=list)

    memo = relationship("Memo", back_populates="lines")
    matched_variant = relationship("ProductVariant", back_populates="memo_lines")
    corrections = relationship("Correction", back_populates="line", cascade="all, delete-orphan")


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memo_id = Column(Uuid(as_uuid=True), ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    memo_line_id = Column(Uuid(as_uuid=True), ForeignKey("memo_lines.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    before_data = Column(JSON, nullable=False)
    after_data = Column(JSON, nullable=False)
    corrected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    memo = relationship("Memo", back_populates="corrections")
    line = relationship("MemoLine", back_populates="corrections")
    user = relationship("User", back_populates="corrections")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memo_id = Column(Uuid(as_uuid=True), ForeignKey("memos.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(50), nullable=False)
    cost_usd = Column(Numeric(8, 5), default=0.00000, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    langfuse_trace_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    memo = relationship("Memo", back_populates="extraction_runs")
