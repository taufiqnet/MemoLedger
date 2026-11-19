import uuid
from app.workers.celery_app import celery
from app.core.database import SessionLocal
from app.services.extraction.pipeline import MemoExtractionPipeline


@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_memo_task(self, memo_id_str: str):
    """
    Background worker job for memo processing.
    """
    db = SessionLocal()
    try:
        memo_id = uuid.UUID(memo_id_str)
        pipeline = MemoExtractionPipeline(db=db)
        pipeline.run(memo_id=memo_id)
        return {"status": "SUCCESS", "memo_id": memo_id_str}
    except Exception as exc:
        db.rollback()
        # Retry with exponential backoff on transient errors
        raise self.retry(exc=exc)
    finally:
        db.close()
