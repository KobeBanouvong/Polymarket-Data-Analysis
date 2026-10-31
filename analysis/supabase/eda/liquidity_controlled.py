from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#File PATH
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT / "analysis" / "supabase" / "outputs" / "data"
)

FIGURES_DIR = (
    PROJECT_ROOT / "analysis" / "supabase" / "outputs" / "figures"
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = DATA_DIR / "market_category_sample.csv"

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Cannot find market sample: {INPUT_FILE}"
    )

#LOAD DATA
print("\nSTATS 414 - CONTROLLED LIQUIDITY ANALYSIS")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

required_columns = [
    "category",
    "created_at",
    "liquidity_clob"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

print(f"\nTotal sampled markets: {len(df):,}")

# Focus on Sports and Crypto
df = df[
    df["category"].isin(["Sports", "Crypto"])
].copy()

print(f"Sports and Crypto markets: {len(df):,}")


# CLEAN DATA
df["liquidity_clob"] = pd.to_numeric(
    df["liquidity_clob"],
    errors="coerce"
)

df["created_at"] = pd.to_datetime(
    df["created_at"],
    errors="coerce",
    utc=True
)

valid = (
    df["liquidity_clob"].notna()
    & np.isfinite(df["liquidity_clob"])
    & (df["liquidity_clob"] >= 0)
    & df["created_at"].notna()
)

print(f"Missing or invalid observations: {(~valid).sum():,}")

df = df.loc[valid].copy()

df["creation_month"] = (
    df["created_at"].dt.strftime("%Y-%m")
)

print(f"Valid observations: {len(df):,}")

#OVERALL LIQUIDITY COMPARISON
print("\nOVERALL LIQUIDITY COMPARISON")
print("-" * 70)

overall = (
    df.groupby("category")["liquidity_clob"]
    .agg(
        count="count",
        median="median",
        mean="mean"
    )
    .round(2)
)

print(overall.to_string())

#LIQUIDITY BY CREATION MONTH
monthly_summary = (
    df.groupby(["creation_month", "category"])
    .agg(
        markets=("liquidity_clob", "size"),
        median_liquidity=("liquidity_clob", "median"),
        mean_liquidity=("liquidity_clob", "mean")
    )
    .reset_index()
)

monthly_summary.to_csv(
    DATA_DIR / "liquidity_controlled_by_month.csv",
    index=False
)

# 6. IDENTIFY COMPARABLE MONTHS
counts = monthly_summary.pivot(
    index="creation_month",
    columns="category",
    values="markets"
).fillna(0)

MIN_MARKETS = 30

valid_months = counts.index[
    (counts.get("Sports", 0) >= MIN_MARKETS)
    & (counts.get("Crypto", 0) >= MIN_MARKETS)
]

print("\nCOMPARABLE CREATION MONTHS")
print("-" * 70)

if len(valid_months) == 0:
    raise ValueError(
        "No months have at least 30 valid markets "
        "in both Sports and Crypto."
    )

print(", ".join(valid_months))

controlled = df[
    df["creation_month"].isin(valid_months)
].copy()


#CONTROLLED COMPARISON
print("\nLIQUIDITY IN COMPARABLE MONTHS")
print("-" * 70)

controlled_summary = (
    controlled.groupby("category")["liquidity_clob"]
    .agg(
        count="count",
        median="median",
        mean="mean"
    )
    .round(2)
)

print(controlled_summary.to_string())

controlled_summary.to_csv(
    DATA_DIR / "liquidity_controlled_summary.csv"
)


#MONTHLY MEDIAN COMPARISON
monthly = monthly_summary[
    monthly_summary["creation_month"].isin(valid_months)
].copy()

comparison = monthly.pivot(
    index="creation_month",
    columns="category",
    values="median_liquidity"
)

comparison = comparison[
    ["Sports", "Crypto"]
].sort_index()

comparison["crypto_to_sports_ratio"] = (
    comparison["Crypto"]
    / comparison["Sports"].replace(0, np.nan)
)

print("\nMONTHLY MEDIAN LIQUIDITY")
print("-" * 70)
print(comparison.round(2).to_string())

comparison.to_csv(
    DATA_DIR / "liquidity_controlled_comparison.csv"
)

crypto_higher = (
    comparison["Crypto"] > comparison["Sports"]
).sum()

print("\nKEY FINDINGS")
print("-" * 70)

print(
    f"Crypto had higher median liquidity in "
    f"{crypto_higher} of {len(comparison)} comparable months."
)


#CREATE CHART
fig, ax = plt.subplots(figsize=(12, 6))

colors = {
    "Sports": "#277DA1",
    "Crypto": "#F4A261"
}

for category in ["Sports", "Crypto"]:
    ax.plot(
        comparison.index,
        comparison[category],
        marker="o",
        markersize=7,
        linewidth=2.5,
        color=colors[category],
        label=category
    )

ax.set_title(
    "Median Liquidity by Creation Month: Sports vs. Crypto",
    fontsize=16,
    fontweight="bold",
    pad=16
)

ax.set_xlabel(
    "Market Creation Month",
    fontsize=11
)

ax.set_ylabel(
    "Median Liquidity",
    fontsize=11
)

ax.legend(
    frameon=False,
    fontsize=11
)

ax.grid(
    axis="y",
    alpha=0.2,
    linestyle="--"
)

ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.xticks(
    rotation=45,
    ha="right"
)

fig.text(
    0.08,
    0.01,
    "Source: Supabase | ~5% market sample | "
    "Months with at least 30 valid markets per category",
    fontsize=9,
    color="gray"
)

plt.tight_layout(
    rect=[0, 0.05, 1, 1]
)

chart_path = (
    FIGURES_DIR / "liquidity_controlled_comparison.png"
)

plt.savefig(
    chart_path,
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close(fig)


print("\nFILES GENERATED")
print("-" * 70)

print(f"Chart: {chart_path}")
print(
    f"CSV: {DATA_DIR / 'liquidity_controlled_by_month.csv'}"
)
print(
    f"CSV: {DATA_DIR / 'liquidity_controlled_summary.csv'}"
)
print(
    f"CSV: {DATA_DIR / 'liquidity_controlled_comparison.csv'}"
)

print("\nAnalysis complete!")
