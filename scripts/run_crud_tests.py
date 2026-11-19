import os
import sys
import uuid
import unittest
from decimal import Decimal

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.supplier import Supplier, SupplierProfile
from app.models.memo import Memo, MemoLine
from app.models.stock import StockMovement
from app.schemas.product import ProductCreate, ProductUpdate, ProductVariantCreate, ProductVariantUpdate, SupplierCreate, SupplierUpdate
from app.schemas.stock import StockAdjustmentCreate
from app.schemas.memo import MemoManualCreate, MemoLineCreate, MemoLinesSaveDraftRequest, MemoLineUpdate
from app.api.v1.products import create_product, get_product, update_product, delete_product, add_product_variant, update_product_variant, delete_product_variant
from app.api.v1.suppliers import create_supplier, get_supplier, update_supplier, delete_supplier
from app.api.v1.stock import adjust_stock
from app.api.v1.memos import create_manual_memo, save_memo_lines_draft, add_memo_line, delete_memo_line, delete_memo


class TestMemoLedgerCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Find or create tenant
        cls.tenant = cls.db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        if not cls.tenant:
            cls.tenant = Tenant(name="Dhaka Cosmetics Mart", slug="dhaka-cosmetics-mart", settings={"currency": "BDT"})
            cls.db.add(cls.tenant)
            cls.db.commit()

        # Find or create user
        cls.user = cls.db.query(User).filter(User.email == "owner@dhakacosmetics.com").first()
        if not cls.user:
            cls.user = User(tenant_id=cls.tenant.id, email="owner@dhakacosmetics.com", full_name="Store Owner", role="owner", password_hash="dummy")
            cls.db.add(cls.user)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_product_and_variant_crud(self):
        """Tests full lifecycle: create product with variant, update, add variant, update variant, and delete."""
        # 1. Create Product
        p_in = ProductCreate(
            name="Test Vitamin C Serum",
            brand="Garnier",
            product_type="Skin Care",
            description="Brightening serum",
            variants=[
                ProductVariantCreate(
                    size_value="30",
                    size_unit="ml",
                    variant_code="V1",
                    cost_price=Decimal("450.00"),
                    retail_price=Decimal("600.00"),
                    initial_stock=Decimal("15.00")
                )
            ]
        )
        created_p = create_product(product_in=p_in, current_user=self.user, db=self.db)
        self.assertIsNotNone(created_p.id)
        self.assertEqual(created_p.name, "Test Vitamin C Serum")
        self.assertEqual(len(created_p.variants), 1)
        v1_id = created_p.variants[0].id

        # 2. Get Product
        fetched_p = get_product(product_id=created_p.id, current_user=self.user, db=self.db)
        self.assertEqual(fetched_p.name, "Test Vitamin C Serum")

        # 3. Update Product
        p_up = ProductUpdate(name="Garnier Vitamin C Serum 30ml", description="Updated description")
        updated_p = update_product(product_id=created_p.id, product_update=p_up, current_user=self.user, db=self.db)
        self.assertEqual(updated_p.name, "Garnier Vitamin C Serum 30ml")

        # 4. Add Second Variant
        v2_in = ProductVariantCreate(
            size_value="50",
            size_unit="ml",
            variant_code="V2",
            cost_price=Decimal("650.00"),
            retail_price=Decimal("850.00"),
            initial_stock=Decimal("20.00")
        )
        created_v2 = add_product_variant(product_id=created_p.id, variant_in=v2_in, current_user=self.user, db=self.db)
        self.assertEqual(created_v2.size_value, "50")

        # 5. Update Variant Price & Stock
        v_up = ProductVariantUpdate(retail_price=Decimal("900.00"), current_stock=Decimal("25.00"))
        updated_v2 = update_product_variant(variant_id=created_v2.id, variant_update=v_up, current_user=self.user, db=self.db)
        self.assertEqual(updated_v2.retail_price, Decimal("900.00"))
        self.assertEqual(updated_v2.current_stock, Decimal("25.00"))

        # 6. Delete Variant
        res_v = delete_product_variant(variant_id=created_v2.id, current_user=self.user, db=self.db)
        self.assertEqual(res_v["status"], "SUCCESS")

        # 7. Delete Product
        res_p = delete_product(product_id=created_p.id, current_user=self.user, db=self.db)
        self.assertEqual(res_p["status"], "SUCCESS")

    def test_02_supplier_crud(self):
        """Tests full lifecycle: create supplier with abbreviations, update, and delete."""
        # 1. Create Supplier
        s_in = SupplierCreate(
            name="Chawkbazar Wholesalers Ltd",
            phone="01711002233",
            address="Moulvibazar, Dhaka",
            abbreviations={"Sun": "Sunscreen", "Vase": "Vaseline"}
        )
        created_s = create_supplier(supplier_in=s_in, current_user=self.user, db=self.db)
        self.assertIsNotNone(created_s.id)
        self.assertEqual(created_s.name, "Chawkbazar Wholesalers Ltd")
        self.assertEqual(created_s.abbreviations.get("Sun"), "Sunscreen")

        # 2. Get Supplier
        fetched_s = get_supplier(supplier_id=created_s.id, current_user=self.user, db=self.db)
        self.assertEqual(fetched_s.phone, "01711002233")

        # 3. Update Supplier & Merge Abbreviations
        s_up = SupplierUpdate(phone="01999887766", abbreviations={"Cantor": "Castor"})
        updated_s = update_supplier(supplier_id=created_s.id, supplier_update=s_up, current_user=self.user, db=self.db)
        self.assertEqual(updated_s.phone, "01999887766")
        self.assertEqual(updated_s.abbreviations.get("Cantor"), "Castor")
        self.assertEqual(updated_s.abbreviations.get("Sun"), "Sunscreen")

        # 4. Delete Supplier
        res_s = delete_supplier(supplier_id=created_s.id, current_user=self.user, db=self.db)
        self.assertEqual(res_s["status"], "SUCCESS")

    def test_03_stock_adjustment_crud(self):
        """Tests manual stock adjustment movement and verifies running balance calculation."""
        # Create temp product variant
        p = Product(tenant_id=self.tenant.id, name="Test Cream")
        self.db.add(p)
        self.db.flush()
        v = ProductVariant(product_id=p.id, cost_price=Decimal("100.00"), retail_price=Decimal("150.00"), current_stock=Decimal("10.00"))
        self.db.add(v)
        self.db.commit()

        # Adjust stock +5
        adj_in = StockAdjustmentCreate(
            variant_id=v.id,
            movement_type="INVENTORY_ADJUSTMENT",
            quantity_change=Decimal("5.00"),
            unit_cost=Decimal("100.00"),
            notes="Physical inventory recount +5"
        )
        movement = adjust_stock(adj=adj_in, current_user=self.user, db=self.db)
        self.assertEqual(movement.quantity_change, Decimal("5.00"))
        self.assertEqual(movement.running_balance, Decimal("15.00"))

        # Verify variant current_stock is updated
        self.db.refresh(v)
        self.assertEqual(v.current_stock, Decimal("15.00"))

        # Cleanup
        self.db.delete(p)
        self.db.commit()

    def test_04_memo_manual_and_line_crud(self):
        """Tests creating manual memo, saving draft lines, adding line, and deleting line."""
        # 1. Create Manual Memo
        memo_in = MemoManualCreate(
            memo_number="MANUAL-999",
            memo_date="19/11/24",
            lines=[
                MemoLineCreate(
                    parsed_name="Vaseline Cocoa",
                    parsed_variant="50ml",
                    parsed_qty=Decimal("2.00"),
                    parsed_unit_price=Decimal("150.00"),
                    parsed_line_total=Decimal("300.00")
                )
            ]
        )
        res = create_manual_memo(memo_in=memo_in, current_user=self.user, db=self.db)
        memo_id = res.memo_id

        memo = self.db.query(Memo).filter(Memo.id == memo_id).first()
        self.assertEqual(memo.memo_number, "MANUAL-999")
        self.assertEqual(len(memo.lines), 1)
        self.assertEqual(memo.extracted_total, Decimal("300.00"))

        # 2. Add New Line
        new_l = MemoLineCreate(
            parsed_name="Sunscreen Cream",
            parsed_variant="SH",
            parsed_qty=Decimal("1.00"),
            parsed_unit_price=Decimal("1050.00"),
            parsed_line_total=Decimal("1050.00")
        )
        add_res = add_memo_line(memo_id=memo.id, line_in=new_l, current_user=self.user, db=self.db)
        self.assertEqual(add_res["status"], "SUCCESS")
        line2_id = uuid.UUID(add_res["line_id"])

        # 3. Save Draft Lines
        draft_in = MemoLinesSaveDraftRequest(
            lines=[
                MemoLineUpdate(
                    id=memo.lines[0].id,
                    parsed_name="Vaseline Cocoa 50ml",
                    parsed_qty=Decimal("3.00"),
                    parsed_unit_price=Decimal("150.00"),
                    parsed_line_total=Decimal("450.00")
                )
            ]
        )
        draft_res = save_memo_lines_draft(memo_id=memo.id, draft_data=draft_in, current_user=self.user, db=self.db)
        self.assertEqual(draft_res["status"], "SUCCESS")

        # 4. Delete Line
        del_line_res = delete_memo_line(memo_id=memo.id, line_id=line2_id, current_user=self.user, db=self.db)
        self.assertEqual(del_line_res["status"], "SUCCESS")

        # 5. Delete Memo
        del_memo_res = delete_memo(memo_id=memo.id, current_user=self.user, db=self.db)
        self.assertEqual(del_memo_res["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
