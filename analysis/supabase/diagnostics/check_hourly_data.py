import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

print("\nSTATS 414 - HOURLY DATA CHECK")
print("=" * 60)

with connect_supabase() as conn:
    with conn.cursor() as cursor:

        # Check whether any records exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM market_hourly
            )
        """)

        has_data = cursor.fetchone()[0]

        print(f"\nHourly data exists: {has_data}")

        if has_data:
            cursor.execute("""
                SELECT
                    market_slug,
                    hour,
                    volume,
                    trade_count
                FROM market_hourly
                LIMIT 5
            """)

            print("\nSAMPLE RECORDS")
            print("-" * 60)

            for row in cursor.fetchall():
                print(row)

        else:
            print("\nThe market_hourly table is empty.")
            print("We cannot use it for EDA 2 or EDA 3.")