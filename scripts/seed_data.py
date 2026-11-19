import os
import sys
import uuid
import hashlib
from decimal import Decimal

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User
from app.models.supplier import Supplier, SupplierProfile
from app.models.product import Product, ProductVariant, ProductAlias
from app.models.memo import Memo
from app.services.matching.embeddings import vector_embedder
from app.services.storage import storage_service
from app.services.extraction.pipeline import MemoExtractionPipeline


import time

def wait_for_db(max_retries=15, delay=2):
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
                conn.commit()
                print("[*] Database is ready.")
                return True
        except Exception as e:
            print(f"[*] Waiting for database to be ready ({i+1}/{max_retries})... {e}")
            time.sleep(delay)
    return False

def seed():
    print("--- Starting MemoLedger Database Seeding ---")
    if not wait_for_db():
        print("[!] Could not connect to database, aborting seed.")
        sys.exit(1)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Demo Tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
        if not tenant:
            tenant = Tenant(
                name="Dhaka Cosmetics Mart",
                slug="dhaka-cosmetics-mart",
                settings={"currency": "BDT", "locale": "bn_BD"}
            )
            db.add(tenant)
            db.flush()
            print(f"[+] Created Tenant: {tenant.name} ({tenant.id})")
        else:
            print(f"[*] Tenant exists: {tenant.name}")

        # 2. Seed Demo Owner User
        user = db.query(User).filter(User.email == "owner@dhakacosmetics.com").first()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email="owner@dhakacosmetics.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Mahmudur Rahman",
                role="owner",
                is_active=True
            )
            db.add(user)
            db.flush()
            print(f"[+] Created Owner User: {user.email}")
        else:
            print(f"[*] Owner User exists: {user.email}")

        # 3. Seed Supplier: K Color Cosmetics
        supplier = db.query(Supplier).filter(
            Supplier.tenant_id == tenant.id,
            Supplier.name == "K Color Cosmetics"
        ).first()

        if not supplier:
            supplier = Supplier(
                tenant_id=tenant.id,
                name="K Color Cosmetics",
                phone="01862-321300, 01835-865331",
                address="121, Mokim Katara, Morium Plaza (2nd floor), Shop 29, 34, 35, Chawkbazar, Dhaka",
                extra_data={"wholesale": True, "location": "Chawkbazar"}
            )
            db.add(supplier)
            db.flush()

            profile = SupplierProfile(
                supplier_id=supplier.id,
                abbreviations={
                    "Sun": "Sunscreen",
                    "Vase": "Vaseline",
                    "Cantor": "Castor",
                    "Sali": "Salicylic",
                    "Mas": "Mascara",
                    "Lip": "Lipstick"
                },
                column_conventions={"item_col": 0, "qty_col": 1, "price_col": 2},
                typical_price_ranges={"sunscreen": 1050, "vaseline": 150}
            )
            db.add(profile)
            db.flush()
            print(f"[+] Created Supplier: {supplier.name} with learned abbreviations")
        else:
            print(f"[*] Supplier exists: {supplier.name}")

        # 4. Seed Canonical Products & Variants
        catalog_data = [
            {
                "name": "Sunscreen",
                "brand": "Sun",
                "type": "Skin Care",
                "variants": [
                    {"size_value": "625", "size_unit": "ml", "variant_code": "SH", "cost": 1050, "retail": 1250, "stock": 10},
                    {"size_value": "100", "size_unit": "ml", "variant_code": "SH", "cost": 350, "retail": 450, "stock": 5}, # Test size isolation
                ]
            },
            {
                "name": "Emeli Lip Gloss",
                "brand": "Emeli",
                "type": "Lip Makeup",
                "variants": [
                    {"size_value": "1", "size_unit": "pc", "variant_code": "928", "cost": 140, "retail": 190, "stock": 15}
                ]
            },
            {
                "name": "Bath Salt",
                "brand": "Bath Care",
                "type": "Body Care",
                "variants": [
                    {"size_value": "1", "size_unit": "pc", "variant_code": None, "cost": 150, "retail": 220, "stock": 8}
                ]
            },
            {
                "name": "W7 Eye Shadow",
                "brand": "W7",
                "type": "Eye Makeup",
                "variants": [
                    {"size_value": "1", "size_unit": "pc", "variant_code": None, "cost": 360, "retail": 480, "stock": 12}
                ]
            },
            {
                "name": "BOB: Mascara",
                "brand": "BOB",
                "type": "Eye Makeup",
                "variants": [
                    {"size_value": "1", "size_unit": "pc", "variant_code": "13", "cost": 210, "retail": 290, "stock": 20}
                ]
            },
            {
                "name": "Vaseline Jelly Cocoa Butter",
                "brand": "Vaseline",
                "type": "Skin Care",
                "variants": [
                    {"size_value": "50", "size_unit": "ml", "variant_code": "J Cocoa", "cost": 150, "retail": 200, "stock": 15},
                    {"size_value": "100", "size_unit": "ml", "variant_code": "J Cocoa", "cost": 280, "retail": 350, "stock": 6}, # Different size must never merge!
                ]
            },
            {
                "name": "Ribana Castor Oil",
                "brand": "Ribana",
                "type": "Hair & Skin Oil",
                "variants": [
                    {"size_value": "200", "size_unit": "ml", "variant_code": None, "cost": 550, "retail": 700, "stock": 14}
                ]
            },
            {
                "name": "Cosrx Salicylic Acid Daily Gentle Cleanser",
                "brand": "Cosrx",
                "type": "Facial Cleanser",
                "variants": [
                    {"size_value": "150", "size_unit": "ml", "variant_code": "F", "cost": 900, "retail": 1150, "stock": 7}
                ]
            }
        ]

        variant_lookup = {}
        for item in catalog_data:
            prod = db.query(Product).filter(
                Product.tenant_id == tenant.id,
                Product.name == item["name"]
            ).first()
            if not prod:
                prod = Product(
                    tenant_id=tenant.id,
                    name=item["name"],
                    brand=item["brand"],
                    product_type=item["type"],
                    description=f"Authentic {item['brand']} cosmetic item."
                )
                db.add(prod)
                db.flush()

            for v in item["variants"]:
                cand_code = v["variant_code"]
                size_v = v["size_value"]
                existing_variant = db.query(ProductVariant).filter(
                    ProductVariant.product_id == prod.id,
                    ProductVariant.size_value == size_v,
                    ProductVariant.variant_code == cand_code
                ).first()

                if not existing_variant:
                    text_for_emb = f"{prod.brand} {prod.name} {size_v or ''} {cand_code or ''}".strip()
                    emb = vector_embedder.embed_text(text_for_emb)
                    existing_variant = ProductVariant(
                        product_id=prod.id,
                        size_value=size_v,
                        size_unit=v["size_unit"],
                        variant_code=cand_code,
                        cost_price=Decimal(str(v["cost"])),
                        retail_price=Decimal(str(v["retail"])),
                        current_stock=Decimal(str(v["stock"])),
                        embedding=emb
                    )
                    db.add(existing_variant)
                    db.flush()
                
                key = f"{prod.name}_{size_v}_{cand_code}"
                variant_lookup[key] = existing_variant

        db.commit()
        print(f"[+] Seeded {len(catalog_data)} products and all variants with vector embeddings.")

        # 5. Seed Supplier Product Aliases
        alias_seed = [
            ("Sun", supplier.id, variant_lookup["Sunscreen_625_SH"].id),
            ("Vase", supplier.id, variant_lookup["Vaseline Jelly Cocoa Butter_50_J Cocoa"].id),
            ("Cantor", supplier.id, variant_lookup["Ribana Castor Oil_200_None"].id),
            ("Castor", supplier.id, variant_lookup["Ribana Castor Oil_200_None"].id),
            ("Caster", supplier.id, variant_lookup["Ribana Castor Oil_200_None"].id),
            ("Cosrx Sali", supplier.id, variant_lookup["Cosrx Salicylic Acid Daily Gentle Cleanser_150_F"].id),
        ]

        for alias_txt, supp_id, var_id in alias_seed:
            existing_a = db.query(ProductAlias).filter(
                ProductAlias.tenant_id == tenant.id,
                ProductAlias.supplier_id == supp_id,
                ProductAlias.alias_text == alias_txt
            ).first()
            if not existing_a:
                db.add(ProductAlias(
                    tenant_id=tenant.id,
                    supplier_id=supp_id,
                    product_variant_id=var_id,
                    alias_text=alias_txt,
                    confidence=1.0,
                    source="SYSTEM_SEED"
                ))
        db.commit()
        print("[+] Seeded Supplier-scoped aliases.")

        # 6. Seed Sample Memo using the uploaded reference image
        sample_img_path = os.path.join(os.path.dirname(__file__), "..", "evaluation", "dataset", "sample_memos", "k_color_memo_sample.jpg")
        if os.path.exists(sample_img_path):
            with open(sample_img_path, "rb") as f:
                img_bytes = f.read()
            img_hash = hashlib.sha256(img_bytes).hexdigest()

            sample_memo = db.query(Memo).filter(Memo.image_hash == img_hash).first()
            if not sample_memo:
                s3_key = f"memos/{tenant.id}/k_color_sample_3508.jpg"
                storage_service.upload_bytes(img_bytes, s3_key)
                sample_memo = Memo(
                    tenant_id=tenant.id,
                    supplier_id=supplier.id,
                    memo_number="3508",
                    memo_date="১৯/১১/২৪",
                    image_s3_key=s3_key,
                    image_hash=img_hash,
                    status="PROCESSING"
                )
                db.add(sample_memo)
                db.commit()
                db.refresh(sample_memo)

                # Run extraction pipeline
                pipeline = MemoExtractionPipeline(db=db)
                pipeline.run(sample_memo.id)
                print(f"[+] Sample Memo #3508 processed! Extracted {len(sample_memo.lines)} lines. Status: {sample_memo.status}")
            else:
                print(f"[*] Sample Memo #3508 already exists (Status: {sample_memo.status})")

    finally:
        db.close()
    print("--- Database Seeding Complete ---")


if __name__ == "__main__":
    seed()
