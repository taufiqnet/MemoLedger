import hashlib
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.models.memo import Memo
from app.services.extraction.pipeline import MemoExtractionPipeline
from app.services.storage import storage_service
import uuid

db = SessionLocal()
tenant = db.query(Tenant).first()

with open('data/uploads/memo_3508.jpg', 'rb') as f:
    img_data = f.read()

s3_key, sha256 = storage_service.upload_bytes(img_data, f"memos/{uuid.uuid4()}.jpg")

memo = Memo(
    tenant_id=tenant.id,
    image_s3_key=s3_key,
    image_hash=sha256,
    status='UPLOADED'
)
db.add(memo)
db.commit()
db.refresh(memo)

pipeline = MemoExtractionPipeline(db=db)
updated_memo = pipeline.run(memo.id)

print(f"Memo ID: {updated_memo.id}, status: {updated_memo.status}")
print(f"Memo number: {updated_memo.memo_number}, Supplier: {updated_memo.supplier.name if updated_memo.supplier else None}")
print(f"Lines count: {len(updated_memo.lines)}")
for l in updated_memo.lines:
    print(f"Line #{l.line_number}: parsed_name='{l.parsed_name}', raw='{l.raw_text}', qty={l.parsed_qty}, rate={l.parsed_unit_price}, total={l.parsed_line_total}, match_conf={l.match_confidence}")
