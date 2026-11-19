import pytest
from app.core.database import SessionLocal
from app.models.tenant import Tenant
from app.services.chat.text_to_sql import GuardedTextToSQL


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_sql_validator_rejects_malicious_input():
    # Injection attempts
    assert GuardedTextToSQL.validate_sql("DROP TABLE users;") is False
    assert GuardedTextToSQL.validate_sql("SELECT * FROM products; DELETE FROM memos;") is False
    assert GuardedTextToSQL.validate_sql("SELECT * FROM products -- comment") is False
    assert GuardedTextToSQL.validate_sql("UPDATE product_variants SET current_stock = 9999") is False
    assert GuardedTextToSQL.validate_sql("INSERT INTO users (email) VALUES ('hacker@evil.com')") is False
    assert GuardedTextToSQL.validate_sql("SELECT * FROM information_schema.tables") is False

    # Valid read-only queries
    assert GuardedTextToSQL.validate_sql("SELECT name, current_stock FROM products LIMIT 10") is True
    assert GuardedTextToSQL.validate_sql("WITH cte AS (SELECT * FROM memos) SELECT * FROM cte") is True


def test_execute_guarded_query(db_session):
    tenant = db_session.query(Tenant).filter(Tenant.slug == "dhaka-cosmetics-mart").first()
    assert tenant is not None

    res = GuardedTextToSQL.execute_query(
        db=db_session,
        tenant_id=tenant.id,
        user_id=None,
        user_query="সানস্ক্রিনের স্টক কত?"
    )
    assert res["error"] is None
    assert "Sunscreen" in res["answer"] or "stock" in res["answer"].lower()
    assert res["generated_sql"] is not None
    assert "LIMIT 50" in res["generated_sql"]
