from pathlib import Path
import sys
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

DATA_DIR = (
    PROJECT_ROOT / "analysis" / "supabase" / "outputs" / "data"
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

print("\nFULL DATABASE MARKET CREATION CHECK")

#CONNECT AND QUERY SUPABASE
query = """
    SELECT
        DATE_TRUNC('month', created_at) AS creation_month,
        COUNT(*) AS market_count
    FROM markets
    WHERE created_at IS NOT NULL
    GROUP BY DATE_TRUNC('month', created_at)
    ORDER BY creation_month
"""

print("\nConnecting to Supabase...")
print("Querying monthly market creation counts...")

with connect_supabase() as conn:
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

df = pd.DataFrame(rows, columns=columns)

if df.empty:
    raise ValueError("No market creation records returned.")


#FORMAT RESULTS
df["creation_month"] = pd.to_datetime(
    df["creation_month"],
    utc=True
).dt.strftime("%Y-%m")

df["market_count"] = df["market_count"].astype(int)

print("\nFULL DATABASE MONTHLY MARKET CREATION")
print("-" * 65)
print(df.to_string(index=False))


#COMPARE WITH 5% SAMPLE
sample_path = DATA_DIR / "monthly_market_creation.csv"

if sample_path.exists():
    sample = pd.read_csv(sample_path)

    sample = sample.rename(
        columns={"market_count": "sample_count"}
    )

    comparison = df.merge(
        sample,
        on="creation_month",
        how="left"
    )

    comparison["sample_count"] = (
        comparison["sample_count"]
        .fillna(0)
        .astype(int)
    )

    comparison["sample_pct"] = (
        comparison["sample_count"]
        / comparison["market_count"]
        * 100
    ).round(2)

    print("\nFULL DATABASE VS 5% SAMPLE")
    print("-" * 65)
    print(comparison.to_string(index=False))

    comparison.to_csv(
        DATA_DIR / "market_creation_sample_comparison.csv",
        index=False
    )


#SUMMARY
total = df["market_count"].sum()
peak = df.loc[df["market_count"].idxmax()]

print("\nSUMMARY")
print("-" * 65)

print(f"Total markets with creation dates: {total:,}")
print(f"Months represented: {len(df)}")
print(f"Peak month: {peak['creation_month']}")
print(f"Markets created in peak month: {peak['market_count']:,}")


output_path = DATA_DIR / "full_monthly_market_creation.csv"
df.to_csv(output_path, index=False)
print(f"\nSaved: {output_path}")

