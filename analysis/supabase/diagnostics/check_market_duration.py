from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = (
    PROJECT_ROOT
    / "analysis"
    / "supabase"
    / "outputs"
    / "data"
    / "market_category_sample.csv"
)

print("\nSTATS 414 - MARKET DURATION DIAGNOSTIC")
print("=" * 65)


# LOAD EXISTING DATA
df = pd.read_csv(
    DATA_PATH,
    usecols=[
        "slug",
        "category",
        "start_date",
        "end_date",
        "created_at"
    ]
)

print(f"\nTotal markets: {len(df):,}")

#CHECK DATE COMPLETENESS
date_columns = [
    "start_date",
    "end_date",
    "created_at"
]

for column in date_columns:
    df[column] = pd.to_datetime(
        df[column],
        errors="coerce",
        utc=True
    )

print("\nDATE COMPLETENESS")
print("-" * 65)

for column in date_columns:
    valid = df[column].notna().sum()
    missing = df[column].isna().sum()

    print(
        f"{column}: "
        f"{valid:,} valid | "
        f"{missing:,} missing | "
        f"{valid / len(df) * 100:.2f}% coverage"
    )


#CALCULATE MARKET DURATION
df["duration_days"] = (
    df["end_date"] - df["start_date"]
).dt.total_seconds() / 86400

valid_dates = df["duration_days"].notna()

negative = (df["duration_days"] < 0).sum()
zero = (df["duration_days"] == 0).sum()
positive = (df["duration_days"] > 0).sum()

print("\nDURATION VALIDATION")
print("-" * 65)

print(f"Markets with both dates: {valid_dates.sum():,}")
print(f"Negative durations: {negative:,}")
print(f"Zero-day durations: {zero:,}")
print(f"Positive durations: {positive:,}")


#DURATION SUMMARY
valid_df = df.loc[
    df["duration_days"] >= 0
].copy()

print("\nDURATION SUMMARY (DAYS)")
print("-" * 65)

if not valid_df.empty:
    print(
        valid_df["duration_days"]
        .describe(
            percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
        )
        .to_string()
    )
else:
    print("No valid market durations found.")


#COMPLETENESS BY CATEGORY
category_summary = (
    df.groupby("category")
    .agg(
        total_markets=("slug", "count"),
        valid_durations=(
            "duration_days",
            lambda x: (x >= 0).sum()
        )
    )
    .reset_index()
)

category_summary["coverage_pct"] = (
    category_summary["valid_durations"]
    / category_summary["total_markets"]
    * 100
).round(2)

category_summary = category_summary.sort_values(
    "coverage_pct",
    ascending=False
)

print("\nDURATION COVERAGE BY CATEGORY")
print("-" * 65)
print(category_summary.to_string(index=False))


