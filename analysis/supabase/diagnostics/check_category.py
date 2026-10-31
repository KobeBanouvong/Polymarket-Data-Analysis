
import sys
from pathlib import Path
import pandas as pd

# 1. PROJECT SETUP
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

print("CHECK POLYMARKET CATEGORIES")

# 2. SQL QUERY
# Check whether Supabase contains official categories or tags

query = """
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'events'
  AND (
      column_name ILIKE '%categor%'
      OR column_name ILIKE '%tag%'
  )
ORDER BY ordinal_position;
"""

# 3. CONNECT TO SUPABASE
print("\nConnecting to Supabase...")

with connect_supabase() as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

# 4. DISPLAY RESULTS
df = pd.DataFrame(rows, columns=columns)

if df.empty:
    print("\nNo category or tag columns found.")
else:
    print("\nCategory/tag columns found:")
    print(df.to_string(index=False))

print("\nDatabase check complete.")
