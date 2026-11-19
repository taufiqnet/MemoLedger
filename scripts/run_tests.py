import os
import sys
import uuid
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.extraction.normalizer import Normalizer
from app.services.extraction.arithmetic import ArithmeticReconciler
from app.services.chat.text_to_sql import GuardedTextToSQL
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.supplier import Supplier
from app.models.product import ProductVariant
from app.models.memo import Memo
from app.services.matching.resolver import ProductResolver, compute_trigram_similarity
from app.services.ledger.ledger_service import LedgerService


class TestMemoLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # 1. Normalizer Tests
    def test_bengali_digits(self):
        self.assertEqual(Normalizer.bengali_to_english_digits("১০৫০"), "1050")
        self.assertEqual(Normalizer.bengali_to_english_digits("১৫০"), "150")
        self.assertEqual(Normalizer.bengali_to_english_digits("৩৬০"), "360")
        self.assertEqual(Normalizer.bengali_to_english_digits("৩6০"), "360")
        self.assertEqual(Normalizer.bengali_to_english_digits("৩৫৫০"), "3550")

    def test_clean_monetary_amount(self):
        self.assertEqual(Normalizer.clean_amount("৩৫৫০/-"), Decimal("3550"))
        self.assertEqual(Normalizer.clean_amount("৳ ১০৫০/-"), Decimal("1050"))
        self.assertEqual(Normalizer.clean_amount("= ৩৫২০/-"), Decimal("3520"))
        self.assertEqual(Normalizer.clean_amount("Tk. 150"), Decimal("150"))

    def test_unit_normalization(self):
        self.assertEqual(Normalizer.normalize_unit("P"), "piece")
        self.assertEqual(Normalizer.normalize_unit("pc"), "piece")
        self.assertEqual(Normalizer.normalize_unit("পিস"), "piece")
        self.assertEqual(Normalizer.normalize_unit("টুকরা"), "piece")
        self.assertEqual(Normalizer.normalize_unit("dz"), "dozen")
        self.assertEqual(Normalizer.normalize_unit("ডজন"), "dozen")

    def test_size_extraction(self):
        self.assertEqual(Normalizer.extract_size_and_unit("Sun 625ml (SH)"), ("625", "ml"))
        self.assertEqual(Normalizer.extract_size_and_unit("Vase 50ml Cocoa"), ("50", "ml"))
        self.assertEqual(Normalizer.extract_size_and_unit("Bath Salt 100g"), ("100", "gram"))

    def test_variant_code(self):
        self.assertEqual(Normalizer.extract_variant_code("Sun 625ml (SH)"), "SH")
        self.assertEqual(Normalizer.extract_variant_code("Emeli Lip (928)"), "928")
        self.assertEqual(Normalizer.extract_variant_code("BOB: Mas (13)"), "13")
        self.assertEqual(Normalizer.extract_variant_code("Cosrx Sali (F)"), "F")

    def test_abbreviation_expansion(self):
        abbrevs = {"Sun": "Sunscreen", "Vase": "Vaseline", "Cantor": "Castor"}
        self.assertIn("Sunscreen", Normalizer.expand_abbreviations("Sun 625ml", abbrevs))
        self.assertIn("Vaseline", Normalizer.expand_abbreviations("Vase 50ml", abbrevs))
        self.assertIn("Castor", Normalizer.expand_abbreviations("Ribana Cantor oil", abbrevs))

    # 2. Arithmetic Reconciliation Tests
    def test_arithmetic_exact(self):
        up, lt, flags = ArithmeticReconciler.reconcile_line(Decimal("1.0"), Decimal("1050.00"), Decimal("1050.00"))
        self.assertEqual(up, Decimal("1050.00"))
        self.assertEqual(lt, Decimal("1050.00"))
        self.assertEqual(len(flags), 0)

    def test_arithmetic_mismatch(self):
        up, lt, flags = ArithmeticReconciler.reconcile_line(Decimal("2.0"), Decimal("150.00"), Decimal("400.00"))
        self.assertTrue(len(flags) > 0)
        self.assertIn("LINE_ARITHMETIC_MISMATCH", flags[0])

    def test_memo_total_reconciliation(self):
        lines = [
            {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("1050.00"), "parsed_line_total": Decimal("1050.00")},
            {"parsed_qty": Decimal("1.0"), "parsed_unit_price": Decimal("150.00"), "parsed_line_total": Decimal("150.00")},
        ]
        _, total_sum, mismatch, flags = ArithmeticReconciler.reconcile_memo(lines, Decimal("1200.00"))
        self.assertEqual(total_sum, Decimal("1200.00"))
        self.assertFalse(mismatch)

    # 3. Product Resolver Tests
    def test_supplier_alias_matching(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        supplier = self.db.query(Supplier).filter(Supplier.name == "K Color Cosmetics").first()
        res = ProductResolver.resolve_line(
            db=self.db,
            tenant_id=tenant.id,
            supplier_id=supplier.id,
            parsed_name="Sun",
            parsed_variant="SH",
            size_value="625",
            size_unit="ml"
        )
        self.assertEqual(res["status"], "AUTO_MATCHED")
        self.assertIn("Sunscreen", res["matched_product_name"])

    def test_different_sizes_never_merge(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        res = ProductResolver.resolve_line(
            db=self.db,
            tenant_id=tenant.id,
            supplier_id=None,
            parsed_name="Vaseline Cocoa",
            parsed_variant="J Cocoa",
            size_value="50",
            size_unit="ml",
            unit_price=Decimal("150.00")
        )
        self.assertIn(res["status"], ["AUTO_MATCHED", "SUGGESTION_NEEDED"])
        matched_uuid = uuid.UUID(str(res["matched_variant_id"]))
        variant = self.db.query(ProductVariant).filter(ProductVariant.id == matched_uuid).first()
        self.assertEqual(variant.size_value, "50")
        self.assertNotEqual(variant.size_value, "100")

    def test_spelling_variation_tolerance(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        for spelling in ["Ribana Castor oil", "Ribana Cantor oil"]:
            res = ProductResolver.resolve_line(
                db=self.db,
                tenant_id=tenant.id,
                supplier_id=None,
                parsed_name=spelling,
                size_value="200",
                size_unit="ml",
                unit_price=Decimal("550.00")
            )
            self.assertIn(res["status"], ["AUTO_MATCHED", "SUGGESTION_NEEDED"])

    # 4. Ledger & Anomaly Detection Tests
    def test_stock_ledger_movement(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        variant = self.db.query(ProductVariant).first()
        initial_stock = Decimal(str(variant.current_stock))
        qty_add = Decimal("2.0")

        movement = LedgerService.record_movement(
            db=self.db,
            tenant_id=tenant.id,
            variant_id=variant.id,
            movement_type="PURCHASE_RECEIPT",
            quantity_change=qty_add,
            unit_cost=Decimal("150.00"),
            notes="Unittest movement"
        )
        self.db.commit()
        self.assertEqual(movement.running_balance, initial_stock + qty_add)

    def test_duplicate_memo(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        sample_memo = self.db.query(Memo).first()
        sample_memo.status = "APPROVED"
        self.db.commit()
        self.assertTrue(LedgerService.check_duplicate_memo(self.db, tenant.id, sample_memo.image_hash))

    # 5. Guarded Text-to-SQL Tests
    def test_sql_security_validator(self):
        self.assertFalse(GuardedTextToSQL.validate_sql("DROP TABLE users;"))
        self.assertFalse(GuardedTextToSQL.validate_sql("SELECT * FROM products; DELETE FROM memos;"))
        self.assertFalse(GuardedTextToSQL.validate_sql("SELECT * FROM products -- comment"))
        self.assertFalse(GuardedTextToSQL.validate_sql("UPDATE product_variants SET current_stock = 9999"))
        self.assertTrue(GuardedTextToSQL.validate_sql("SELECT name, current_stock FROM products LIMIT 10"))

    def test_ask_data_query(self):
        tenant = self.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        res = GuardedTextToSQL.execute_query(
            db=self.db,
            tenant_id=tenant.id,
            user_id=None,
            user_query="সানস্ক্রিনের স্টক কত?"
        )
        self.assertIsNone(res["error"])
        self.assertTrue("Sunscreen" in res["answer"] or "stock" in res["answer"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
