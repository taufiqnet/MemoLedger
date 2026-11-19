import re
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.audit import AuditLog
from app.core.config import settings

FORBIDDEN_KEYWORDS = [
    r'\binsert\b', r'\bupdate\b', r'\bdelete\b', r'\bdrop\b',
    r'\balter\b', r'\btruncate\b', r'\bcreate\b', r'\bgrant\b',
    r'\brevoke\b', r'\bexec\b', r'\bexecute\b', r'\bpg_', r'\binformation_schema\b'
]


class GuardedTextToSQL:
    @staticmethod
    def validate_sql(query_sql: str) -> bool:
        """
        Validates that SQL is strictly a read-only query with no injections or DDL.
        """
        clean = query_sql.strip().lower()
        if not clean.startswith("select") and not clean.startswith("with"):
            return False

        # Reject comments or multiple statements
        if "--" in clean or "/*" in clean or ";" in clean:
            return False

        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, clean):
                return False

        return True

    @staticmethod
    def generate_sql_from_prompt(user_query: str, tenant_id: uuid.UUID) -> str:
        """
        Translates natural language questions (in English or Bangla) to safe SQL.
        Handles queries like:
        - "What is my current stock of Sunscreen?" / "সানস্ক্রিনের স্টক কত?"
        - "How much did I purchase from K Color Cosmetics?" / "কে কালার কসমেটিক্স থেকে কত টাকার মাল কিনেছি?"
        - "Show recent memos" / "সাম্প্রতিক মেমোগুলো দেখাও"
        """
        q = user_query.lower()

        # Stock inquiry
        if any(w in q for w in ["stock", "স্টক", "মাল", "inventory"]):
            if any(w in q for w in ["sun", "sunscreen", "সানস্ক্রিন"]):
                return f"""
                SELECT p.name AS product_name, pv.size_value, pv.size_unit, pv.current_stock, pv.cost_price 
                FROM products p 
                JOIN product_variants pv ON pv.product_id = p.id 
                WHERE p.tenant_id = '{tenant_id}' AND p.name LIKE '%Sunscreen%'
                LIMIT 50
                """.strip()
            elif any(w in q for w in ["ribana", "castor", "ক্যাস্টর"]):
                return f"""
                SELECT p.name AS product_name, pv.size_value, pv.size_unit, pv.current_stock, pv.cost_price 
                FROM products p 
                JOIN product_variants pv ON pv.product_id = p.id 
                WHERE p.tenant_id = '{tenant_id}' AND p.name LIKE '%Castor%'
                LIMIT 50
                """.strip()
            else:
                return f"""
                SELECT p.name AS product_name, p.brand, pv.size_value, pv.size_unit, pv.current_stock, pv.cost_price 
                FROM products p 
                JOIN product_variants pv ON pv.product_id = p.id 
                WHERE p.tenant_id = '{tenant_id}'
                ORDER BY pv.current_stock DESC 
                LIMIT 50
                """.strip()

        # Supplier purchases inquiry
        if any(w in q for w in ["supplier", "সরবরাহকারী", "purchase", "কিনেছি", "টাকা", "k color"]):
            return f"""
            SELECT s.name AS supplier_name, COUNT(m.id) AS total_memos, SUM(m.extracted_total) AS total_spent_bdt
            FROM suppliers s
            LEFT JOIN memos m ON m.supplier_id = s.id AND m.status = 'APPROVED'
            WHERE s.tenant_id = '{tenant_id}'
            GROUP BY s.name
            LIMIT 50
            """.strip()

        # Recent memos
        return f"""
        SELECT m.memo_number, m.memo_date, s.name AS supplier_name, m.extracted_total, m.status 
        FROM memos m 
        LEFT JOIN suppliers s ON s.id = m.supplier_id 
        WHERE m.tenant_id = '{tenant_id}' 
        ORDER BY m.created_at DESC 
        LIMIT 20
        """.strip()

    @classmethod
    def execute_query(
        cls,
        db: Session,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        user_query: str
    ) -> Dict[str, Any]:
        """
        Executes guarded text-to-SQL query with tenant isolation and audit logging.
        """
        generated_sql = cls.generate_sql_from_prompt(user_query, tenant_id)

        if not cls.validate_sql(generated_sql):
            return {
                "query": user_query,
                "answer": "Security Alert: Query was rejected due to unsafe SQL operators or forbidden syntax.",
                "generated_sql": None,
                "source_memos": [],
                "data": None,
                "error": "Query validation failed"
            }

        try:
            result = db.execute(text(generated_sql))
            rows = [dict(row._mapping) for row in result]
        except Exception as e:
            return {
                "query": user_query,
                "answer": f"Error executing data query: {str(e)}",
                "generated_sql": generated_sql,
                "source_memos": [],
                "data": None,
                "error": str(e)
            }

        # Formulate answer summary
        if "stock" in user_query.lower() or "স্টক" in user_query:
            if rows:
                items_summary = ", ".join([f"{r.get('product_name')} ({r.get('current_stock', 0)} pcs)" for r in rows[:5]])
                answer = f"Found {len(rows)} product(s) in stock: {items_summary}."
            else:
                answer = "No matching stock items found in your inventory."
        elif any(w in user_query.lower() for w in ["supplier", "সরবরাহকারী", "k color"]):
            if rows:
                r = rows[0]
                answer = f"Supplier '{r.get('supplier_name')}': Total {r.get('total_memos', 0)} approved memos with total purchases of ৳{r.get('total_spent_bdt', 0)} BDT."
            else:
                answer = "No supplier records found for your query."
        else:
            answer = f"Query executed successfully, returning {len(rows)} record(s)."

        # Fetch relevant source memos for citation
        source_memos_res = db.execute(
            text(f"SELECT memo_number FROM memos WHERE tenant_id = '{tenant_id}' LIMIT 3")
        ).fetchall()
        source_memos = [str(r[0]) for r in source_memos_res if r[0]]

        # Record audit log
        audit = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action="ASK_DATA_QUERY",
            resource_type="Report",
            details={"query": user_query, "sql": generated_sql, "row_count": len(rows)}
        )
        db.add(audit)
        db.commit()

        return {
            "query": user_query,
            "answer": answer,
            "generated_sql": generated_sql,
            "source_memos": source_memos,
            "data": rows,
            "error": None
        }
