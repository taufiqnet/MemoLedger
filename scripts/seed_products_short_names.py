from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.product import Product, ProductVariant
from app.services.matching.embeddings import vector_embedder
from decimal import Decimal
import uuid

db = SessionLocal()
tenant = db.query(Tenant).first()
print(f"Populating products for tenant: {tenant.name} ({tenant.id})")

products_data = [
    # Explicit user requests:
    ("Lilac Brightening Cream", "Lilac B/C", Decimal("600.00")),
    ("Zafran Hair Growth Therapy", "Zafran H/Oil", Decimal("220.00")),
    ("Bath Salt", "Bath Salt", Decimal("150.00")),
    ("Soft Finish Sun Milk", "Soft (f)", Decimal("1000.00")),
    ("YC Cucumber Face Wash", "YC-Cu F/W", Decimal("145.00")),
    ("SASI BB Perfect Powder", "Sasi BB - Powder", Decimal("110.00")),
    
    # Memo items:
    ("Sunscreen Cream 625ml", "Sun 625ml (SH)", Decimal("1050.00")),
    ("Emeli Matte Lipstick", "Emeli Lip (928)", Decimal("140.00")),
    ("W7 Eye Shadow Palette", "W7 Eye", Decimal("200.00")),
    ("BOB Long Lash Mascara", "BOB: Mas (13)", Decimal("210.00")),
    ("Vaseline Jelly Cocoa Butter", "Vase 50ml (J) Co", Decimal("150.00")),
    ("Ribana Organic Castor Oil", "Ribana Castor oil", Decimal("550.00")),
    ("Cosrx Salicylic Acid Gentle Cleanser", "Cosrx Sali (F)", Decimal("900.00")),
    ("Bioaqua Nose Blackhead Strip", "BG N/Strip", Decimal("18.00")),
    ("Kojic Acid Rice Face Wash", "Koj-Rice (F)", Decimal("750.00")),
    ("Dabo All In One Cream", "Dabo. All in 1 (e)", Decimal("600.00")),
    ("Kado 160g Face Wash Powder", "Kado 160g pawd", Decimal("510.00")),
    ("Mango Hair Removal Wax", "Mango Wax", Decimal("600.00")),
    ("Wax Strips Paper", "Wax Paper (s)", Decimal("70.00")),
]

for full_name, short_name, cost_price in products_data:
    existing = db.query(Product).filter(
        Product.tenant_id == tenant.id,
        (Product.name.ilike(full_name)) | (Product.name.ilike(f"%{short_name}%")) | (Product.short_name.ilike(short_name))
    ).first()

    if existing:
        existing.name = full_name
        existing.short_name = short_name
        emb = vector_embedder.embed_text(f"{full_name} {short_name}")
        if existing.variants:
            v = existing.variants[0]
            v.cost_price = cost_price
            v.retail_price = cost_price
            v.embedding = emb
        else:
            var = ProductVariant(
                product_id=existing.id,
                sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
                cost_price=cost_price,
                retail_price=cost_price,
                current_stock=10,
                embedding=emb
            )
            db.add(var)
        print(f"Updated: {full_name} -> Short: '{short_name}'")
    else:
        prod = Product(
            tenant_id=tenant.id,
            name=full_name,
            short_name=short_name,
        )
        db.add(prod)
        db.flush()
        emb = vector_embedder.embed_text(f"{full_name} {short_name}")
        var = ProductVariant(
            product_id=prod.id,
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            cost_price=cost_price,
            retail_price=cost_price,
            current_stock=10,
            embedding=emb
        )
        db.add(var)
        print(f"Created: {full_name} -> Short: '{short_name}'")

db.commit()
print("Total products in database:", db.query(Product).filter(Product.tenant_id == tenant.id).count())
