from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "supabase" / "outputs"
DATA_DIR = OUTPUT_DIR / "data"
FIGURES_DIR = OUTPUT_DIR / "figures"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

CATEGORY_PATH = DATA_DIR / "market_category_sample.csv"

print("\nPOLYMARKET TRADING VOLUME EDA")

#LOAD EXISTING CATEGORY DATA
if not CATEGORY_PATH.exists():
    raise FileNotFoundError(
        "market_category_sample.csv not found. "
        "Run market_categories.py first."
    )

required_columns = [
    "slug",
    "category",
    "volume_clob",
    "volume_24hr",
    "volume_1wk",
    "volume_1mo",
    "liquidity_clob"
]

df = pd.read_csv(
    CATEGORY_PATH,
    usecols=required_columns
)

if df.empty:
    raise ValueError("Category dataset is empty.")

if df["slug"].duplicated().any():
    raise ValueError("Duplicate market slugs detected.")

print("\nLoading classified market dataset...")

print(f"Markets loaded: {len(df):,}")
print(f"Categories represented: {df['category'].nunique()}")
print(f"Duplicate market slugs: {df['slug'].duplicated().sum():,}")

#CLEAN VOLUME DATA
volume_columns = [
    "volume_clob",
    "volume_24hr",
    "volume_1wk",
    "volume_1mo",
    "liquidity_clob"
]

for column in volume_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    df[column] = df[column].replace(
        [np.inf, -np.inf],
        np.nan
    )

    negative_count = (df[column] < 0).sum()

    if negative_count > 0:
        print(
            f"Warning: {negative_count:,} negative "
            f"values found in {column}"
        )

        df.loc[df[column] < 0, column] = np.nan

print("\nMISSING VALUES")
print("-" * 65)

missing_values = df[volume_columns].isna().sum()

print(missing_values.to_string())

print("\nVOLUME DATA SUMMARY")
print("-" * 65)

print(
    df[volume_columns].describe().to_string()
)


#MISSING VOLUME ANALYSIS BY CATEGORY
missing_summary = (
    df.groupby("category")
    .agg(
        total_markets=("slug", "count"),
        valid_volume=("volume_clob", "count"),
        missing_volume=(
            "volume_clob",
            lambda x: x.isna().sum()
        )
    )
    .reset_index()
)

missing_summary["missing_pct"] = (
    missing_summary["missing_volume"]
    / missing_summary["total_markets"]
    * 100
).round(2)

missing_summary["valid_pct"] = (
    missing_summary["valid_volume"]
    / missing_summary["total_markets"]
    * 100
).round(2)

missing_summary = missing_summary.sort_values(
    "missing_pct",
    ascending=False
)

print("\nMISSING VOLUME BY CATEGORY")
print("-" * 65)

print(missing_summary.to_string(index=False))

missing_summary.to_csv(
    DATA_DIR / "missing_volume_by_category.csv",
    index=False
)



#VALID TRADING VOLUME DATA
# Missing values are excluded, not replaced with zero.
valid_df = df.dropna(
    subset=["volume_clob"]
).copy()

if valid_df.empty:
    raise ValueError(
        "No valid cumulative volume values found."
    )

total_markets = len(df)
valid_markets = len(valid_df)
missing_markets = total_markets - valid_markets

print("\nTRADING VOLUME COVERAGE")
print("-" * 65)

print(f"Total markets: {total_markets:,}")
print(f"Valid volume: {valid_markets:,}")
print(f"Missing volume: {missing_markets:,}")

print(
    f"Volume coverage: "
    f"{valid_markets / total_markets * 100:.2f}%"
)

print(
    f"Markets with zero volume: "
    f"{(valid_df['volume_clob'] == 0).sum():,}"
)



#TRADING VOLUME BY CATEGORY
summary = (
    valid_df.groupby("category")
    .agg(
        market_count=("slug", "count"),
        total_volume=("volume_clob", "sum"),
        average_volume=("volume_clob", "mean"),
        median_volume=("volume_clob", "median"),
        max_volume=("volume_clob", "max")
    )
    .reset_index()
)

total_observed_volume = summary["total_volume"].sum()

summary["volume_share_pct"] = (
    summary["total_volume"]
    / total_observed_volume
    * 100
    if total_observed_volume > 0
    else 0.0
)

summary = summary.merge(
    missing_summary[
        [
            "category",
            "total_markets",
            "missing_pct"
        ]
    ],
    on="category",
    how="left"
)

summary = summary.sort_values(
    "total_volume",
    ascending=False
)

print("\nTRADING VOLUME BY CATEGORY")
print("-" * 65)

print(
    summary.to_string(
        index=False,
        float_format=lambda x: f"{x:,.2f}"
    )
)

summary.to_csv(
    DATA_DIR / "trading_volume_by_category.csv",
    index=False
)



#GRAPH 1 - TOTAL OBSERVED TRADING VOLUME
chart = summary.sort_values("total_volume")

fig, ax = plt.subplots(figsize=(12, 7))

ax.barh(
    chart["category"],
    chart["total_volume"] / 1_000_000,
    color="#277DA1"
)

ax.set_xlabel("Reported Cumulative Volume (Millions)")

ax.set_title(
    "Observed Trading Volume by Market Category",
    fontsize=15,
    fontweight="bold"
)

ax.grid(axis="x", alpha=0.2)
ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "total_volume_by_category.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)



#GRAPH 2 - AVERAGE VS MEDIAN VOLUME
chart = summary.sort_values("average_volume")

fig, ax = plt.subplots(figsize=(12, 7))

y = np.arange(len(chart))

ax.barh(
    y - 0.2,
    chart["average_volume"],
    height=0.4,
    label="Average",
    color="#277DA1"
)

ax.barh(
    y + 0.2,
    chart["median_volume"],
    height=0.4,
    label="Median",
    color="#F9C74F"
)

ax.set_yticks(y)
ax.set_yticklabels(chart["category"])

ax.set_xlabel("Reported Cumulative Volume per Market")

ax.set_title(
    "Average vs Median Trading Volume by Category",
    fontsize=15,
    fontweight="bold"
)

ax.legend()

ax.grid(axis="x", alpha=0.2)
ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "average_median_volume.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)



#GRAPH 3 - VOLUME DISTRIBUTION
fig, ax = plt.subplots(figsize=(12, 7))

categories = summary["category"].tolist()

data = [
    valid_df.loc[
        valid_df["category"] == category,
        "volume_clob"
    ].values
    for category in categories
]

ax.boxplot(
    data,
    tick_labels=categories,
    showfliers=False
)

ax.set_yscale("symlog", linthresh=1)

ax.set_ylabel(
    "Reported Cumulative Volume (Symmetric Log Scale)"
)

ax.set_title(
    "Trading Volume Distribution by Category",
    fontsize=15,
    fontweight="bold"
)

plt.xticks(rotation=35, ha="right")

ax.grid(axis="y", alpha=0.2)
ax.set_axisbelow(True)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "volume_distribution.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)



#GRAPH 4 - MISSING VOLUME BY CATEGORY
chart = missing_summary.sort_values(
    "missing_pct",
    ascending=True
)

fig, ax = plt.subplots(figsize=(12, 7))

bars = ax.barh(
    chart["category"],
    chart["missing_pct"],
    color="#F9844A"
)

ax.set_xlabel("Markets Missing Volume (%)")

ax.set_title(
    "Missing Trading Volume Data by Category",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlim(0, 110)

for bar in bars:

    width = bar.get_width()

    ax.text(
        width + 1,
        bar.get_y() + bar.get_height() / 2,
        f"{width:.1f}%",
        va="center",
        fontsize=10
    )

ax.grid(axis="x", alpha=0.2)
ax.set_axisbelow(True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

plt.savefig(
    FIGURES_DIR / "missing_volume_by_category.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)


#EXPORT CLEANED DATA
df.to_csv(
    DATA_DIR / "market_volume_sample.csv",
    index=False
)

print("\nVisualizations generated.")

print("\n" + "=" * 65)
print("EDA 2 COMPLETE")
print("=" * 65)

print(f"\nCSV results saved to: {DATA_DIR}")
print(f"Figures saved to: {FIGURES_DIR}")
