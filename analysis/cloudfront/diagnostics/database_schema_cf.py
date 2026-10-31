import truststore
truststore.inject_into_ssl()

import sys
import os
import tempfile
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_cloudfront


# CloudFront Parquet file to inspect
FILENAME = "events-2026-05-30T21.parquet"


print("CLOUDFRONT DATABASE SCHEMA")
print(f"File: {FILENAME}")

temporary_path = None

try:
    # Connect to CloudFront and download the Parquet file
    with connect_cloudfront(FILENAME) as response:

        print("Connection: SUCCESS")

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

    # Read the Parquet schema
    parquet_file = pq.ParquetFile(temporary_path)

    schema_rows = []

    for field in parquet_file.schema_arrow:
        schema_rows.append({
            "column_name": field.name,
            "data_type": str(field.type),
            "is_nullable": field.nullable
        })

    df = pd.DataFrame(
        schema_rows,
        columns=[
            "column_name",
            "data_type",
            "is_nullable"
        ]
    )

    print(f"\nTotal columns: {len(df)}")
    print(f"Total records: {parquet_file.metadata.num_rows:,}")

    print("\nCOLUMNS")
    print("-" * 65)
    print(df.to_string(index=False))

    parquet_file.close()

    # Save schema to CSV
    output_dir = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "cloudfront_schema.csv"
    df.to_csv(output_path, index=False)

    print(f"\nSchema saved to: {output_path}")

except Exception as error:
    print(f"\nCloudFront error: {error}")

finally:
    # Clean up the temporary Parquet file
    if temporary_path and os.path.exists(temporary_path):
        try:
            os.remove(temporary_path)
        except OSError as error:
            print(f"Warning: Could not delete temporary file: {error}")