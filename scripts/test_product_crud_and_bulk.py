import unittest
import uuid
from decimal import Decimal
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.product import Product, ProductVariant
from app.schemas.product import ProductBulkCreate, ProductSimpleCreate
from app.api.v1.products import bulk_create_products, create_product_simple
from app.services.matching.resolver import ProductResolver


class TestProductCRUDAndBulk(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.tenant = self.db.query(Tenant).first()

    def tearDown(self):
        self.db.close()

    def test_simple_product_creation(self):
        unique_name = f"Test Simple Cream {uuid.uuid4().hex[:6]}"
        simple_in = ProductSimpleCreate(name=unique_name, cost_price=Decimal("250.00"), retail_price=Decimal("350.00"))
        
        class DummyUser:
            tenant_id = self.tenant.id

        prod = create_product_simple(product_in=simple_in, current_user=DummyUser(), db=self.db)
        self.assertIsNotNone(prod.id)
        self.assertEqual(prod.name, unique_name)
        self.assertEqual(len(prod.variants), 1)
        self.assertEqual(prod.variants[0].cost_price, Decimal("250.00"))

    def test_bulk_product_creation(self):
        p1 = f"Bulk Item A {uuid.uuid4().hex[:6]}"
        p2 = f"Bulk Item B {uuid.uuid4().hex[:6]}"
        
        class DummyUser:
            tenant_id = self.tenant.id

        payload = ProductBulkCreate(names=[f"{p1}\n{p2}"])
        res = bulk_create_products(payload=payload, current_user=DummyUser(), db=self.db)
        
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["created_count"], 2)
        self.assertIn(p1, res["created_names"])
        self.assertIn(p2, res["created_names"])

    def test_fuzzy_matching_and_clean_name(self):
        res = ProductResolver.resolve_line(
            db=self.db,
            tenant_id=self.tenant.id,
            supplier_id=None,
            parsed_name="B0B:a132Qyo",
        )
        self.assertIn(res["status"], ["AUTO_MATCHED", "SUGGESTION_NEEDED"])
        self.assertIn("BOB", res["matched_clean_name"])


if __name__ == "__main__":
    unittest.main()
