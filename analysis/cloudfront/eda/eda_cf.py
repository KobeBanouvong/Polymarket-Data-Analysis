import sys
import os
import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Project setup
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_cloudfront

# Configuration
FILENAME = "events-2026-05-30T21.parquet"
SAMPLE_SIZE = 100_000

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_PATH = OUTPUT_DIR / "cloudfront_sample.csv"


# ============================================================
# 1. DOWNLOAD PARQUET FILE
# ============================================================

print("=" * 65)
print("POLYMARKET CLOUDfront EXPLORATORY DATA ANALYSIS")
print("=" * 65)

temporary_path = None

try:
    print(f"\nDownloading: {FILENAME}")

    with connect_cloudfront(FILENAME) as response:

        print("CloudFront connection: SUCCESS")

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

    file_size = os.path.getsize(temporary_path)

    print(f"File size: {file_size / (1024 ** 2):.2f} MB")


    # ========================================================
    # 2. RANDOM SAMPLE
    # ========================================================

    print(f"\nSampling {SAMPLE_SIZE:,} records...")

    con = duckdb.connect()

    try:
        total_records = con.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [temporary_path]
        ).fetchone()[0]

        sample_size = min(SAMPLE_SIZE, total_records)

        # Reservoir sampling selects a random sample of rows.
        sample = con.execute(
            f"""
            SELECT *
            FROM read_parquet(?)
            USING SAMPLE reservoir({int(sample_size)} ROWS)
            """,
        [temporary_path]).df()

    finally:
        con.close()

    print(f"Total records in file: {total_records:,}")
    print(f"Records sampled: {len(sample):,}")
    print(
        f"Sampling percentage: "
        f"{len(sample) / total_records * 100:.2f}%"
    )

    # Save sample for reproducible follow-up analysis.
    sample.to_csv(SAMPLE_PATH, index=False)

    print(f"Sample saved to: {SAMPLE_PATH}")


    # ========================================================
    # 3. DATA CLEANING AND STRUCTURE
    # ========================================================

    print("\n" + "=" * 65)
    print("3. DATA STRUCTURE")
    print("=" * 65)

    print("\nData types:")
    print(sample.dtypes)

    print("\nFirst five records:")
    print(sample.head().to_string(index=False))

    print("\nDataset dimensions:")
    print(f"Rows: {sample.shape[0]:,}")
    print(f"Columns: {sample.shape[1]}")

    print("\nMissing values:")
    missing = sample.isnull().sum().to_frame("missing_count")
    missing["missing_pct"] = (
        missing["missing_count"] / len(sample) * 100
    )

    print(missing.to_string())

    print("\nDuplicate records:")
    duplicates = sample.duplicated().sum()
    print(f"Exact duplicate rows: {duplicates:,}")


    # ========================================================
    # 4. DESCRIPTIVE STATISTICS
    # ========================================================

    print("\n" + "=" * 65)
    print("4. DESCRIPTIVE STATISTICS")
    print("=" * 65)

    numeric_columns = ["ts_ms", "price", "size"]

    stats = sample[numeric_columns].describe().T

    print("\nNumeric summary:")
    print(stats.to_string())

    stats.to_csv(OUTPUT_DIR / "numeric_summary.csv")

    # Investigate price and size separately.
    for column in ["price", "size"]:

        valid = sample[column].dropna()

        print(f"\n{column.upper()} SUMMARY")
        print("-" * 40)

        if len(valid) > 0:
            print(f"Mean:   {valid.mean():,.4f}")
            print(f"Median: {valid.median():,.4f}")
            print(f"Min:    {valid.min():,.4f}")
            print(f"Max:    {valid.max():,.4f}")
            print(f"Std:    {valid.std():,.4f}")


    # ========================================================
    # 5. MARKETS AND ASSETS
    # ========================================================

    print("\n" + "=" * 65)
    print("5. MARKET AND ASSET ACTIVITY")
    print("=" * 65)

    print("\nUnique markets:")
    print(sample["market"].nunique(dropna=True))

    print("\nUnique assets:")
    print(sample["asset_id"].nunique(dropna=True))

    print("\nMost frequently represented markets:")

    top_markets = (
        sample["market"]
        .value_counts()
        .head(10)
        .rename_axis("market")
        .reset_index(name="record_count")
    )

    print(top_markets.to_string(index=False))

    top_markets.to_csv(
        OUTPUT_DIR / "top_markets.csv",
        index=False
    )

    print("\nMost frequently represented assets:")

    top_assets = (
        sample["asset_id"]
        .value_counts()
        .head(10)
        .rename_axis("asset_id")
        .reset_index(name="record_count")
    )

    print(top_assets.to_string(index=False))

    top_assets.to_csv(
        OUTPUT_DIR / "top_assets.csv",
        index=False
    )

    print("\nSide distribution:")

    side_counts = (
        sample["side"]
        .value_counts(dropna=False)
        .rename_axis("side")
        .reset_index(name="record_count")
    )

    side_counts["percentage"] = (
        side_counts["record_count"] / len(sample) * 100
    )

    print(side_counts.to_string(index=False))

    side_counts.to_csv(
        OUTPUT_DIR / "side_distribution.csv",
        index=False
    )


    # ========================================================
    # 6. TIMESTAMP ANALYSIS
    # ========================================================

    print("\n" + "=" * 65)
    print("6. TEMPORAL ANALYSIS")
    print("=" * 65)

    # ts_ms is assumed to be Unix epoch milliseconds.
    sample["timestamp"] = pd.to_datetime(
        sample["ts_ms"],
        unit="ms",
        utc=True,
        errors="coerce"
    )

    valid_timestamps = sample["timestamp"].dropna()

    if not valid_timestamps.empty:

        print(f"Earliest timestamp: {valid_timestamps.min()}")
        print(f"Latest timestamp:   {valid_timestamps.max()}")

        # Count sampled records per minute
        minute_activity = (
        sample.dropna(subset=["timestamp"])
        .set_index("timestamp")
        .resample("1min")
        .size()
        .rename("record_count")
        .reset_index()
    )

        print("\nMinute-level activity summary:")
        print(minute_activity["record_count"].describe())

        minute_activity.to_csv(
            OUTPUT_DIR / "minute_activity.csv",
            index=False
        )

        plt.figure(figsize=(12, 5))

        plt.plot(
            minute_activity["timestamp"],
            minute_activity["record_count"],
            marker="o",
            markersize=3
        )

        plt.title("Polymarket Event Records per Minute")
        plt.xlabel("Timestamp (UTC)")
        plt.ylabel("Sampled Records")
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.savefig(
            OUTPUT_DIR / "minute_activity.png",
            dpi=150
        )

        plt.close()

    else:
        print("No valid timestamps available.")


# ============================================================
# 7. PRICE AND SIZE DISTRIBUTIONS
# ============================================================

        print("\n" + "=" * 65)
        print("7. PRICE AND SIZE DISTRIBUTIONS")
        print("=" * 65)


# ------------------------------------------------------------
# PRICE DISTRIBUTION
# ------------------------------------------------------------

        prices = pd.to_numeric(
            sample["price"],
            errors="coerce"
        )

        prices = prices[np.isfinite(prices)]

        if not prices.empty:

            plt.figure(figsize=(9, 5))

            plt.hist(
                prices,
                bins=50
            )

            plt.title("Distribution of Polymarket Prices")
            plt.xlabel("Price")
            plt.ylabel("Frequency")
            plt.tight_layout()

            plt.savefig(
                OUTPUT_DIR / "price_distribution.png",
                dpi=150
            )

            plt.close()

            print("\nPrice distribution saved.")


    # ============================================================
    # 7. SIZE DISTRIBUTION
    # ============================================================

    print("\n" + "=" * 65)
    print("7. SIZE DISTRIBUTION")
    print("=" * 65)

    sizes = sample["size"].dropna()

    print("\nSize distribution diagnostics:")
    print(f"Zero-size records: {(sizes == 0).sum():,}")
    print(f"Positive-size records: {(sizes > 0).sum():,}")
    print(f"Negative-size records: {(sizes < 0).sum():,}")

    # Log-transform sizes (log1p handles zeros)
    log_sizes = np.log1p(sizes[sizes >= 0])

    plt.figure(figsize=(10, 5))

    plt.hist(
        log_sizes,
        bins=60,
        edgecolor="black",
        alpha=0.75
    )

    plt.title("Distribution of Polymarket Event Sizes")
    plt.xlabel("Log(1 + Event Size)")
    plt.ylabel("Number of Records")

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "size_distribution.png",
        dpi=150
    )

    plt.close()


# ------------------------------------------------------------
# OPTIONAL: SIZE DISTRIBUTION AFTER LOG TRANSFORMATION
# ------------------------------------------------------------

# log1p handles zeros and compresses extreme values.
# This is useful for understanding the shape of the distribution.

    if not sizes.empty and (sizes >= 0).all():

            log_sizes = np.log1p(sizes)

            plt.figure(figsize=(9, 5))

            plt.hist(
                log_sizes,
                bins=50
            )

            plt.title("Distribution of log(1 + Size)")
            plt.xlabel("log(1 + Size)")
            plt.ylabel("Frequency")
            plt.tight_layout()

            plt.savefig(
                OUTPUT_DIR / "log_size_distribution.png",
                dpi=150
            )

            plt.close()

            print("Log-transformed size distribution saved.")



    # ========================================================
    # 8. PRICE BY SIDE
    # ========================================================

    print("\n" + "=" * 65)
    print("8. PRICE BY SIDE")
    print("=" * 65)

    price_by_side = (
        sample.groupby("side", dropna=False)["price"]
        .agg(["count", "mean", "median", "std", "min", "max"])
    )

    print(price_by_side.to_string())

    price_by_side.to_csv(
        OUTPUT_DIR / "price_by_side.csv"
    )

    print("\n" + "=" * 65)
    print("EDA COMPLETE")
    print("=" * 65)

    print(f"Outputs saved in: {OUTPUT_DIR}")


except Exception as error:
    print(f"\nEDA error: {error}")
    raise

finally:
    if temporary_path and os.path.exists(temporary_path):
        try:
            os.remove(temporary_path)
        except OSError as error:
            print(f"Warning: Could not delete temporary file: {error}")
    # ============================================================
    # 9. BUY VS SELL PRICE BOXPLOT
    # ============================================================

    print("\n" + "=" * 65)
    print("9. BUY VS SELL PRICE BOXPLOT")
    print("=" * 65)

    # Filter to valid BUY/SELL records with nonmissing prices
    boxplot_data = sample[
        sample["side"].isin(["BUY", "SELL"])
        & sample["price"].notna()
    ].copy()

    buy_prices = boxplot_data.loc[
        boxplot_data["side"] == "BUY", "price"
    ]

    sell_prices = boxplot_data.loc[
        boxplot_data["side"] == "SELL", "price"
    ]

    plt.figure(figsize=(9, 6))

    plt.boxplot(
        [buy_prices, sell_prices],
        tick_labels=["BUY", "SELL"],
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 2}
    )

    plt.title("Polymarket Price Distribution by Side")
    plt.xlabel("Side")
    plt.ylabel("Price")
    plt.ylim(0, 1)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "price_by_side_boxplot.png",
        dpi=150
    )

    plt.close()

    print("Boxplot saved to:", OUTPUT_DIR / "price_by_side_boxplot.png")