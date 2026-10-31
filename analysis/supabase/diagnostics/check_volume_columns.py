from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

query = """
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('markets', 'events')
ORDER BY table_name, ordinal_position;
"""

with connect_supabase() as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)

        for table, column, dtype in cursor.fetchall():
            print(f"{table:12} {column:35} {dtype}")