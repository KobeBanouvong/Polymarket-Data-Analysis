from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "supabase" / "outputs"
DATA_DIR = OUTPUT_DIR / "data"
FIGURES_DIR = OUTPUT_DIR / "figures"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

FULL_PATH = DATA_DIR / "full_monthly_market_creation.csv"
SAMPLE_PATH = DATA_DIR / "market_category_sample.csv"

print("\nPOLYMARKET MARKET CREATION EDA")

#LOAD FULL DATABASE MONTHLY COUNTS
print("\nLoading full Supabase monthly counts...")

full = pd.read_csv(FULL_PATH)

full["creation_month"] = pd.to_datetime(
    full["creation_month"],
    format="%Y-%m",
    errors="raise"
)

full["market_count"] = pd.to_numeric(
    full["market_count"],
    errors="raise"
).astype(int)

full = full.sort_values("creation_month")

if full["creation_month"].duplicated().any():
    raise ValueError("Duplicate months in full database data.")

print(f"Full database markets: {full['market_count'].sum():,}")
print(f"Months represented: {len(full)}")


#LOAD CLASSIFIED 5% SAMPLE
print("\nLoading classified market sample...")

sample = pd.read_csv(
    SAMPLE_PATH,
    usecols=["slug", "category", "created_at"]
)

if sample["slug"].duplicated().any():
    raise ValueError("Duplicate market slugs detected.")

sample["created_at"] = pd.to_datetime(
    sample["created_at"],
    errors="coerce",
    utc=True
)

missing_dates = sample["created_at"].isna().sum()

if missing_dates:
    print(f"Warning: {missing_dates:,} missing creation dates.")

sample = sample.dropna(subset=["created_at"]).copy()

sample["creation_month"] = (
    sample["created_at"]
    .dt.tz_localize(None)
    .dt.to_period("M")
    .dt.to_timestamp()
)

print(f"Sample markets: {len(sample):,}")
print(f"Categories: {sample['category'].nunique()}")


#PREPARE MONTHLY CATEGORY COUNTS
category_monthly = (
    sample.groupby(["creation_month", "category"])
    .size()
    .rename("market_count")
    .reset_index()
)

category_monthly["creation_month"] = (
    category_monthly["creation_month"].dt.strftime("%Y-%m")
)

category_monthly.to_csv(
    DATA_DIR / "monthly_creation_by_category.csv",
    index=False
)

pivot_counts = (
    category_monthly.pivot(
        index="creation_month",
        columns="category",
        values="market_count"
    )
    .fillna(0)
)

# Include all months represented in the full database
all_months = full["creation_month"].dt.strftime("%Y-%m")

pivot_counts = pivot_counts.reindex(
    all_months,
    fill_value=0
)

pivot_counts = pivot_counts.astype(int)


#CATEGORY COMPOSITION
monthly_totals = pivot_counts.sum(axis=1)

pivot_pct = (
    pivot_counts
    .div(monthly_totals.replace(0, np.nan), axis=0)
    .mul(100)
    .fillna(0)
)

pivot_pct.to_csv(
    DATA_DIR / "monthly_category_composition.csv",
    index_label="creation_month"
)


#CHART 1 - FULL DATABASE MARKET CREATION
fig, ax = plt.subplots(figsize=(13, 6))

labels = full["creation_month"].dt.strftime("%Y-%m")

bars = ax.bar(
    labels,
    full["market_count"],
    color="#277DA1"
)

ax.set_title(
    "Polymarket: Monthly Market Creation (Full Database)",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlabel("Creation Month")
ax.set_ylabel("Number of Markets Created")

ax.tick_params(axis="x", rotation=45)
ax.grid(axis="y", alpha=0.25)
ax.set_axisbelow(True)

# Highlight the final partial month
last_bar = bars[-1]
last_bar.set_color("#F4A261")

ax.annotate(
    "Partial month",
    xy=(
        last_bar.get_x() + last_bar.get_width() / 2,
        last_bar.get_height()
    ),
    xytext=(0, 10),
    textcoords="offset points",
    ha="center",
    fontsize=9
)

ax.text(
    0,
    -0.23,
    "Source: Supabase markets table | October 2026 incomplete",
    transform=ax.transAxes,
    fontsize=9,
    color="gray"
)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "monthly_market_creation.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


#CHART 2 - MONTHLY CREATION BY CATEGORY
fig, ax = plt.subplots(figsize=(14, 7))

pivot_counts.plot(
    kind="area",
    stacked=True,
    ax=ax,
    linewidth=0
)

ax.set_title(
    "Polymarket: Monthly Market Creation by Category (5% Sample)",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlabel("Creation Month")
ax.set_ylabel("Sampled Markets Created")

ax.legend(
    title="Category",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

ax.tick_params(axis="x", rotation=45)
ax.grid(axis="y", alpha=0.2)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "monthly_creation_by_category.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


#CHART 3 - CATEGORY COMPOSITION OVER TIME
# Exclude months with no sampled markets.
valid_months = (
    (monthly_totals > 0)
    & (pivot_pct.index >= "2026-05")
)

composition_plot = pivot_pct.loc[valid_months]

fig, ax = plt.subplots(figsize=(14, 7))

composition_plot.plot(
    kind="area",
    stacked=True,
    ax=ax,
    linewidth=0
)

ax.set_title(
    "Polymarket: Category Composition Over Time (5% Sample)",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlabel("Creation Month")
ax.set_ylabel("Percentage of Sampled New Markets")

ax.set_ylim(0, 100)

ax.legend(
    title="Category",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

ax.tick_params(axis="x", rotation=45)
ax.grid(axis="y", alpha=0.2)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "monthly_category_composition.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


#FULL DATABASE VS SAMPLE COMPARISON
sample_monthly = (
    sample.groupby("creation_month")
    .size()
    .rename("sample_count")
    .reset_index()
)

comparison = full.merge(
    sample_monthly,
    left_on="creation_month",
    right_on="creation_month",
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

comparison["creation_month"] = (
    comparison["creation_month"].dt.strftime("%Y-%m")
)

comparison.to_csv(
    DATA_DIR / "market_creation_sample_comparison.csv",
    index=False
)


#FINAL SUMMARY
peak = full.loc[full["market_count"].idxmax()]

print("\nFULL DATABASE MARKET CREATION SUMMARY")
print("-" * 65)
print(f"Total markets: {full['market_count'].sum():,}")
print(f"Sampled markets: {len(sample):,}")
print(f"Peak month: {peak['creation_month'].strftime('%Y-%m')}")
print(f"Peak month count: {peak['market_count']:,}")
print("\nFULL DATABASE VS SAMPLE")
print("-" * 65)
print(comparison.to_string(index=False))
print("\nVisualizations generated")


