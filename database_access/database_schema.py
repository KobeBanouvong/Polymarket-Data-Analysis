import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

query = """
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position
"""

print("SUPABASE DATABASE SCHEMA")
with connect_supabase() as conn:
    df = pd.read_sql_query(query, conn)

for table_name, group in df.groupby("table_name", sort=False):
    print(f"\nTABLE: {table_name}")
    print("-" * 65)
    print(
        group[
            ["column_name", "data_type", "is_nullable"]
        ].to_string(index=False)
    )

output_path = (
    PROJECT_ROOT
    / "database_access"
    / "database_schema.csv"
)

df.to_csv(output_path, index=False)

print(f"\nSchema saved to: {output_path}")
