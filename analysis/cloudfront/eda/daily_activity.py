import truststore
truststore.inject_into_ssl()

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import pyarrow.parquet as pq

# ============================================================
# PROJECT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_cloudfront

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATE = "2026-05-30"

# ============================================================
# 1. DOWNLOAD AND COUNT RECORDS
# ============================================================

print("\n" + "=" * 65)
print("POLYMARKET DAILY EVENT ACTIVITY")
print("=" * 65)

hourly_counts = []

for hour in range(24):

    filename = f"events-{DATE}T{hour:02d}.parquet"
    temporary_path = OUTPUT_DIR / f"temp_hour_{hour:02d}.parquet"

    print(f"\nProcessing: {filename}")

    record_count = None

    try:
        with connect_cloudfront(filename) as response:
            with open(temporary_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        # Read metadata without keeping a ParquetFile open
        metadata = pq.read_metadata(temporary_path)
        record_count = metadata.num_rows

        print(f"Records: {record_count:,}")

        if record_count == 0:
            print("WARNING: File contains zero records.")

    except Exception as e:
        print(f"ERROR processing hour {hour}: {e}")

    finally:
        # Clean up temporary file
        try:
            if temporary_path.exists():
                temporary_path.unlink()
        except OSError as e:
            print(f"WARNING: Could not delete temporary file: {e}")

        # Append exactly one result per hour
        hourly_counts.append({
            "hour": hour,
            "timestamp": pd.Timestamp(
                f"{DATE} {hour:02d}:00:00",
                tz="UTC"
            ),
            "record_count": record_count
        })

# ============================================================
# 2. CREATE DATAFRAME
# ============================================================

daily_activity = pd.DataFrame(hourly_counts)

print("\n" + "=" * 65)
print("HOURLY ACTIVITY SUMMARY")
print("=" * 65)

print(daily_activity.to_string(index=False))

print("\nDescriptive statistics (available hours only):")
print(daily_activity["record_count"].describe())

daily_activity.to_csv(
    OUTPUT_DIR / "daily_activity.csv",
    index=False
)

# ============================================================
# 3. PLOT HOURLY ACTIVITY
# ============================================================

valid_activity = daily_activity.dropna(subset=["record_count"])

plt.figure(figsize=(12, 5))

plt.plot(
    valid_activity["hour"],
    valid_activity["record_count"],
    marker="o",
    linewidth=2,
    markersize=6
)

plt.title(f"Polymarket Event Activity by Hour ({DATE})")
plt.xlabel("Hour of Day (UTC)")
plt.ylabel("Number of Event Records")

plt.xticks(range(24))
plt.grid(True, alpha=0.3)

plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "daily_activity.png",
    dpi=150
)

plt.close()

print("\nDaily activity chart saved to:")
print(OUTPUT_DIR / "daily_activity.png")

print("\nEDA COMPLETE")