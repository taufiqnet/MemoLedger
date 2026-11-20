from app.core.database import SessionLocal, engine
from app.models.memo import Memo, MemoLine, ExtractionRun, Correction
from app.models.stock import StockMovement
from app.models.product import Product, ProductVariant
from sqlalchemy import text

def clear_all_upload_data():
    db = SessionLocal()
    try:
        # Check counts before
        memo_count_before = db.query(Memo).count()
        line_count_before = db.query(MemoLine).count()
        movement_count_before = db.query(StockMovement).count()
        product_count_before = db.query(Product).count()
        variant_count_before = db.query(ProductVariant).count()

        print(f"Before reset: {memo_count_before} memos, {line_count_before} memo lines, {movement_count_before} stock movements.")
        print(f"Product catalog (to be preserved): {product_count_before} products, {variant_count_before} variants.")

        # Delete all corrections, extraction runs, memo lines, stock movements, and memos
        db.query(Correction).delete()
        db.query(ExtractionRun).delete()
        db.query(MemoLine).delete()
        db.query(StockMovement).delete()
        db.query(Memo).delete()

        db.commit()

        # Check counts after
        memo_count_after = db.query(Memo).count()
        line_count_after = db.query(MemoLine).count()
        movement_count_after = db.query(StockMovement).count()
        product_count_after = db.query(Product).count()
        variant_count_after = db.query(ProductVariant).count()

        print(f"After reset: {memo_count_after} memos, {line_count_after} memo lines, {movement_count_after} stock movements.")
        print(f"Product catalog safely preserved: {product_count_after} products, {variant_count_after} variants.")
        assert memo_count_after == 0
        assert line_count_after == 0
        assert product_count_after == product_count_before
        print("Upload data reset successful!")
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_upload_data()
