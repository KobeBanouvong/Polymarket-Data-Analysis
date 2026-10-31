import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import (
    connect_cloudfront,
    connect_supabase,
)
FILENAME = "events-2026-05-30T21.parquet"

print("\nSTATS 414 - CLOUDFRONT EVENT INSPECTION")
print("=" * 65)


#DOWNLOAD CLOUDFRONT PARQUET FILE
with tempfile.TemporaryDirectory() as temp_dir:

    file_path = Path(temp_dir) / FILENAME

    print("\nDownloading CloudFront Parquet file...")

    with connect_cloudfront(FILENAME) as response:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    f.write(chunk)

    print("Download complete.")

    #CONNECT TO DUCKDB
    con = duckdb.connect()

    try:
        # Register local Parquet file as a DuckDB view.
        # DuckDB does not support parameters in CREATE VIEW.

        safe_path = str(file_path).replace("'", "''")

        con.execute(f"""
            CREATE VIEW events AS
            SELECT *
            FROM read_parquet('{safe_path}')
        """)


        #EVENT SUMMARY
        print("\nEVENT SUMMARY")
        print("-" * 65)

        summary = con.execute("""
            SELECT
                COUNT(*) AS total_records,
                COUNT(DISTINCT market) AS unique_markets,
                COUNT(DISTINCT asset_id) AS unique_assets,
                MIN(ts_ms) AS earliest_timestamp,
                MAX(ts_ms) AS latest_timestamp,
                COUNT(*) FILTER (
                    WHERE size = 0
                ) AS zero_size,
                COUNT(*) FILTER (
                    WHERE size > 0
                ) AS positive_size
            FROM events
        """).df()

        print(summary.to_string(index=False))

        #BUY VS SELL DISTRIBUTION
        print("\nSIDE DISTRIBUTION")
        print("-" * 65)

        sides = con.execute("""
            SELECT
                side,
                COUNT(*) AS records,
                AVG(price) AS avg_price,
                AVG(size) AS avg_size
            FROM events
            GROUP BY side
            ORDER BY records DESC
        """).df()

        print(sides.to_string(index=False))

     
        #TIMESTAMP RANGE
        print("\nTIMESTAMP RANGE (UTC)")
        print("-" * 65)

        times = con.execute("""
            SELECT
                to_timestamp(
                    MIN(ts_ms) / 1000.0
                ) AS earliest,
                to_timestamp(
                    MAX(ts_ms) / 1000.0
                ) AS latest
            FROM events
        """).df()

        print(times.to_string(index=False))

    
        #SAMPLE CLOUDFRONT MARKET IDS
        print("\nSAMPLE CLOUDFRONT MARKET IDS")
        print("-" * 65)

        market_ids = con.execute("""
            SELECT DISTINCT market
            FROM events
            WHERE market IS NOT NULL
            LIMIT 10
        """).df()

        print(market_ids.to_string(index=False))

      
        #MATCH CLOUDFRONT IDS TO SUPABASE
        print("\nMATCHING CLOUDFRONT MARKETS TO SUPABASE")
        print("-" * 65)

        ids = market_ids["market"].tolist()

        if ids:

            query = """
                SELECT
                    slug,
                    title,
                    condition_id,
                    volume_clob
                FROM markets
                WHERE condition_id = ANY(%s)
            """

            with connect_supabase() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (ids,))

                    rows = cursor.fetchall()

                    columns = [
                        col[0]
                        for col in cursor.description
                    ]

            matched_df = pd.DataFrame(
                rows,
                columns=columns
            )

            print(f"CloudFront IDs checked: {len(ids)}")
            print(f"Matching Supabase records: {len(matched_df)}")

            if not matched_df.empty:

                print("\nMATCHED MARKETS")
                print("-" * 65)

                print(
                    matched_df.to_string(
                        index=False
                    )
                )

            else:
                print(
                    "\nNo matching condition IDs found."
                )

        else:
            print("No CloudFront market IDs available.")

    finally:
        con.close()


