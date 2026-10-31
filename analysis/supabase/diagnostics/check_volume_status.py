import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

query = """
SELECT
    active,
    closed,
    archived,
    COUNT(*) AS total_markets,
    COUNT(volume_clob) AS markets_with_volume,
    COUNT(*) - COUNT(volume_clob) AS missing_volume
FROM markets
WHERE slug IS NOT NULL
  AND (
      ('x' || substr(md5(slug), 1, 8))::bit(32)::bigint
      % 10000
  ) < 500
GROUP BY active, closed, archived
ORDER BY total_markets DESC;
"""

with connect_supabase() as conn:
    df = pd.read_sql_query(query, conn)

df["missing_pct"] = (
    df["missing_volume"] / df["total_markets"] * 100
).round(2)

print("\nVOLUME AVAILABILITY BY MARKET STATUS")
print("-" * 80)
print(df.to_string(index=False))