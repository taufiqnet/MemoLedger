import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Uuid
from app.core.database import Base


class EvalExample(Base):
    __tablename__ = "eval_examples"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(Uuid(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    memo_id = Column(Uuid(as_uuid=True), ForeignKey("memos.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(100), nullable=False)
    raw_input_data = Column(JSON, nullable=False)
    ground_truth_data = Column(JSON, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
