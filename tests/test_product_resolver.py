import pytest
from decimal import Decimal
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.supplier import Supplier
from app.models.product import Product, ProductVariant
from app.services.matching.resolver import ProductResolver, compute_trigram_similarity


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_trigram_similarity():
    # Misspelled names
    assert compute_trigram_similarity("Castor", "Cantor") > 0.4
    assert compute_trigram_similarity("Castor", "Caster") > 0.5
    assert compute_trigram_similarity("Vaseline", "Vase") > 0.3
    assert compute_trigram_similarity("Sunscreen", "Sun") > 0.3


def test_supplier_alias_resolution(db_session):
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    supplier = db_session.query(Supplier).filter(Supplier.name == "K Color Cosmetics").first()
    assert tenant is not None
    assert supplier is not None

    # "Sun" has a supplier-scoped alias to Sunscreen 625ml
    res = ProductResolver.resolve_line(
        db=db_session,
        tenant_id=tenant.id,
        supplier_id=supplier.id,
        parsed_name="Sun",
        parsed_variant="SH",
        size_value="625",
        size_unit="ml"
    )
    assert res["status"] == "AUTO_MATCHED"
    assert res["match_confidence"] >= 0.95
    assert "Sunscreen" in res["matched_product_name"]


def test_different_sizes_never_merge(db_session):
    """
    Requirement: Different sizes of the same brand never merge.
    Querying Vaseline with 50ml must match 50ml variant and NOT 100ml.
    """
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    assert tenant is not None

    res = ProductResolver.resolve_line(
        db=db_session,
        tenant_id=tenant.id,
        supplier_id=None,
        parsed_name="Vaseline Cocoa",
        parsed_variant="J Cocoa",
        size_value="50",
        size_unit="ml",
        unit_price=Decimal("150.00")
    )
    assert res["status"] == "AUTO_MATCHED"
    matched_variant = db_session.query(ProductVariant).filter(
        ProductVariant.id == res["matched_variant_id"]
    ).first()
    assert matched_variant.size_value == "50"
    assert matched_variant.size_value != "100"


def test_spelling_variation_tolerance(db_session):
    """
    Same item spelled several ways (Castor / Cantor / Caster) resolves to one product.
    """
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    assert tenant is not None

    for spelling in ["Ribana Castor oil", "Ribana Cantor oil", "Ribana Caster oil"]:
        res = ProductResolver.resolve_line(
            db=db_session,
            tenant_id=tenant.id,
            supplier_id=None,
            parsed_name=spelling,
            size_value="200",
            size_unit="ml",
            unit_price=Decimal("550.00")
        )
        assert res["status"] in ["AUTO_MATCHED", "SUGGESTION_NEEDED"]
        assert "Ribana" in res["matched_product_name"] or "Castor" in res["matched_product_name"]
