import sys, os
sys.path.insert(0, os.path.abspath("."))
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.memo import Memo, MemoLine
from app.services.extraction.pipeline import MemoExtractionPipeline

memo_uuid = uuid.UUID("6dba6c9e-f663-42d0-aa3f-1c7ea503a6f2")

for port in [5432, 5433]:
    try:
        engine = create_engine(f"postgresql://postgres:19863022@localhost:{port}/memoledger")
        Session = sessionmaker(bind=engine)
        db = Session()
        memo = db.query(Memo).filter(Memo.id == memo_uuid).first()
        if memo:
            print(f"[+] Found memo {memo_uuid} on port {port}. Cleaning old lines...")
            db.query(MemoLine).filter(MemoLine.memo_id == memo_uuid).delete()
            memo.memo_number = None
            memo.extracted_total = 0
            memo.written_total = 0
            db.commit()

            print(f"[*] Running extraction pipeline for memo {memo_uuid}...")
            pipeline = MemoExtractionPipeline(db=db)
            updated = pipeline.run(memo_id=memo.id)
            print(f"[✓] Extracted: Memo #{updated.memo_number}, Lines: {len(updated.lines)}, Total: {updated.extracted_total}")
            for l in updated.lines:
                print(f"    - Line {l.line_number}: {l.raw_text} -> {l.parsed_name} | Qty: {l.parsed_qty} | Total: {l.parsed_line_total}")
        else:
            print(f"[-] Memo {memo_uuid} not on port {port}")
        db.close()
    except Exception as e:
        print(f"Error on port {port}: {e}")
