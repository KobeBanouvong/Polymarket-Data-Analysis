from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sample = pd.read_csv(
    OUTPUT_DIR / "cloudfront_sample.csv",
    dtype={"market": str, "asset_id": str}
)

# ============================================================
# 1. MARKET ACTIVITY
# ============================================================

market_counts = sample["market"].value_counts()

total_events = len(sample)
total_markets = len(market_counts)

print("=" * 60)
print("MARKET ACTIVITY CONCENTRATION")
print("=" * 60)

print(f"Total sampled events: {total_events:,}")
print(f"Unique markets: {total_markets:,}")

# ============================================================
# 2. CONCENTRATION METRICS
# ============================================================

top_1_pct_count = max(1, int(np.ceil(total_markets * 0.01)))
top_5_pct_count = max(1, int(np.ceil(total_markets * 0.05)))

top_1_share = (
    market_counts.head(top_1_pct_count).sum()
    / total_events * 100
)

top_5_share = (
    market_counts.head(top_5_pct_count).sum()
    / total_events * 100
)

top_10_share = (
    market_counts.head(10).sum()
    / total_events * 100
)

print(f"\nTop 10 markets: {top_10_share:.2f}% of events")
print(f"Top 1% of markets: {top_1_share:.2f}% of events")
print(f"Top 5% of markets: {top_5_share:.2f}% of events")

print(f"\nMedian events per market: {market_counts.median():.0f}")
print(f"Mean events per market: {market_counts.mean():.2f}")

# ============================================================
# 3. GINI COEFFICIENT
# ============================================================

values = np.sort(market_counts.values.astype(float))
n = len(values)

gini = (
    2 * np.sum(np.arange(1, n + 1) * values)
    / (n * np.sum(values))
    - (n + 1) / n
)

print(f"\nGini coefficient: {gini:.4f}")

# ============================================================
# 4. CONCENTRATION CURVE
# ============================================================

cumulative_events = market_counts.cumsum() / total_events * 100
market_percentiles = np.arange(1, total_markets + 1) / total_markets * 100

plt.figure(figsize=(10, 6))

plt.plot(
    market_percentiles,
    cumulative_events,
    linewidth=2,
    label="Observed concentration"
)

plt.plot(
    [0, 100],
    [0, 100],
    linestyle="--",
    color="gray",
    label="Equal activity"
)

plt.xlabel("Top X% of Markets")
plt.ylabel("Cumulative Share of Events (%)")
plt.title("Concentration of Polymarket Event Activity")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "market_concentration.png",
    dpi=150
)

plt.close()

# ============================================================
# 5. SAVE RESULTS
# ============================================================

market_summary = market_counts.reset_index()
market_summary.columns = ["market", "event_count"]

market_summary["event_share_pct"] = (
    market_summary["event_count"] / total_events * 100
)

market_summary.to_csv(
    OUTPUT_DIR / "market_concentration.csv",
    index=False
)

print("\nSaved market_concentration.png")
print("Saved market_concentration.csv")