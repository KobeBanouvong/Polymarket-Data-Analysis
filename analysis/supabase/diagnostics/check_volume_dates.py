import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

query = """
SELECT
    DATE_TRUNC('month', created_at) AS creation_month,
    COUNT(*) AS total_markets,
    COUNT(volume_clob) AS markets_with_volume,
    COUNT(*) - COUNT(volume_clob) AS missing_volume
FROM markets
WHERE slug IS NOT NULL
  AND created_at IS NOT NULL
  AND (
      ('x' || substr(md5(slug), 1, 8))::bit(32)::bigint
      % 10000
  ) < 500
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY creation_month;
"""

with connect_supabase() as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

df = pd.DataFrame(rows, columns=columns)

df["missing_pct"] = (
    df["missing_volume"]
    / df["total_markets"]
    * 100
).round(2)

print("\nVOLUME AVAILABILITY BY CREATION MONTH")
print("-" * 85)
print(df.to_string(index=False))