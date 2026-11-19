import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect("postgresql://postgres:19863022@localhost:5432/postgres")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute("SELECT 1 FROM pg_database WHERE datname='memoledger'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE memoledger")
    print("Database 'memoledger' created.")
else:
    print("Database 'memoledger' already exists.")

cur.close()
conn.close()

# Now connect to memoledger database and enable extensions
conn = psycopg2.connect("postgresql://postgres:19863022@localhost:5432/memoledger")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
cur.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
try:
    cur.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    print("pgvector extension enabled.")
except Exception as e:
    print(f"pgvector extension note: {e}")

print("PostgreSQL setup for MemoLedger completed successfully.")
cur.close()
conn.close()
