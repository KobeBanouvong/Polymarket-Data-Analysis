import truststore
truststore.inject_into_ssl()

import os
import tempfile
import duckdb
import pandas as pd
import pyarrow.parquet as pq
from config import connect_supabase, connect_cloudfront



print("POLYMARKET DATABASE OVERVIEW")

#SUPABASE DATABASE
print("\n1. SUPABASE DATABASE")
try:
    with connect_supabase() as conn:
        with conn.cursor() as cursor:

            print("Connection: SUCCESS")

            # Get available tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            tables = [row[0] for row in cursor.fetchall()]

            print(f"\nAvailable tables: {len(tables)}")

            for table in tables:

                print(f"\nTable: {table}")

                # Estimated row counts
                cursor.execute("""
                    SELECT reltuples::BIGINT
                    FROM pg_class
                    WHERE oid = to_regclass(%s)
                """, (f"public.{table}",))

                result = cursor.fetchone()
                count = result[0] if result else None

                print(f"Estimated records: {count:,}"
                      if count is not None
                      else "Estimated records: Unknown")

                # Column information
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))

                columns = cursor.fetchall()

                print("Columns:")
                for name, dtype in columns:
                    print(f"  {name}: {dtype}")

                # Sample data
                # Table names come from the database catalog,
                # not user input.
                from psycopg2 import sql

                cursor.execute(
                    sql.SQL("SELECT * FROM {} LIMIT 5").format(
                        sql.Identifier("public", table)
                    )
                )

                samples = cursor.fetchall()
                column_names = [
                    desc[0] for desc in cursor.description
                ]

                print("\nSample records:")
                if samples:
                    df = pd.DataFrame(
                        samples,
                        columns=column_names
                    )
                    print(df.to_string(index=False))
                else:
                    print("  No records found.")

except Exception as error:
    print(f"Supabase error: {error}")



#CLOUDFRONT DATABASE
print("\n\n2. CLOUDFRONT DATA")
filename = "events-2026-05-30T21.parquet"
temporary_path = None

try:
    print(f"Sample file: {filename}")

    with connect_cloudfront(filename) as response:

        print("Connection: SUCCESS")

        # Download sample file to a temporary location
        with tempfile.NamedTemporaryFile(
            suffix=".parquet",
            delete=False
        ) as temp_file:

            temporary_path = temp_file.name

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    temp_file.write(chunk)

    # Read Parquet metadata without loading all rows
    parquet_file = pq.ParquetFile(temporary_path)

    file_size = os.path.getsize(temporary_path)

    print(f"File size: {file_size / (1024 ** 2):.2f} MB")
    print(f"Total records: {parquet_file.metadata.num_rows:,}")

    print("\nColumns:")
    for field in parquet_file.schema_arrow:
        print(f"  {field.name}: {field.type}")

    parquet_file.close()

    # Read only five sample records
    con = duckdb.connect()

    try:
        sample = con.execute(
            "SELECT * FROM read_parquet(?) LIMIT 5",
            [temporary_path]
        ).df()

        print("\nSample records:")
        print(sample.to_string(index=False))

    finally:
        con.close()

except Exception as error:
    print(f"CloudFront error: {error}")

finally:
    if temporary_path and os.path.exists(temporary_path):
        try:
            os.remove(temporary_path)
        except PermissionError:
            print("Temporary file could not be deleted.")

