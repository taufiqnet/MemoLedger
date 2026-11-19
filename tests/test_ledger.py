import pytest
import uuid
from decimal import Decimal
from fastapi import HTTPException
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.supplier import Supplier
from app.models.product import ProductVariant
from app.models.memo import Memo
from app.services.ledger.ledger_service import LedgerService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_append_only_stock_movement(db_session):
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    variant = db_session.query(ProductVariant).first()
    assert tenant is not None
    assert variant is not None

    initial_stock = Decimal(str(variant.current_stock))
    qty_add = Decimal("5.0")

    movement = LedgerService.record_movement(
        db=db_session,
        tenant_id=tenant.id,
        variant_id=variant.id,
        movement_type="PURCHASE_RECEIPT",
        quantity_change=qty_add,
        unit_cost=Decimal("100.00"),
        notes="Test ledger entry"
    )
    db_session.commit()

    assert movement.quantity_change == qty_add
    assert movement.running_balance == initial_stock + qty_add
    db_session.refresh(variant)
    assert Decimal(str(variant.current_stock)) == initial_stock + qty_add


def test_anomaly_detection_price_spike(db_session):
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    supplier = db_session.query(Supplier).filter(Supplier.name == "K Color Cosmetics").first()
    variant = db_session.query(ProductVariant).first()

    # Normal price 100 -> sudden price 250 (150% spike)
    # First seed 2 prices of 100
    from app.models.stock import PriceHistory
    db_session.add(PriceHistory(tenant_id=tenant.id, supplier_id=supplier.id, product_variant_id=variant.id, unit_price=Decimal("100.00")))
    db_session.commit()

    flags = LedgerService.check_anomalies(
        db=db_session,
        tenant_id=tenant.id,
        supplier_id=supplier.id,
        variant_id=variant.id,
        unit_price=Decimal("250.00"),
        quantity=Decimal("1.0")
    )
    assert any("PRICE_SPIKE_DETECTED" in f for f in flags)


def test_duplicate_memo_detection(db_session):
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    sample_memo = db_session.query(Memo).first()
    assert sample_memo is not None

    # Mark as approved
    sample_memo.status = "APPROVED"
    db_session.commit()

    # Check duplicate
    is_dup = LedgerService.check_duplicate_memo(
        db=db_session,
        tenant_id=tenant.id,
        image_hash=sample_memo.image_hash
    )
    assert is_dup is True
