import truststore
truststore.inject_into_ssl()

import sys
from pathlib import Path

import duckdb
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# PROJECT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_cloudfront

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HOURS = [20, 21, 22, 23]
DATE = "2026-05-30"


# ============================================================
# DOWNLOAD AND ANALYZE EACH HOURLY FILE
# ============================================================

def analyze_hour(hour):

    filename = f"events-{DATE}T{hour:02d}.parquet"
    temp_file = OUTPUT_DIR / f"temp_hour_{hour:02d}.parquet"

    print("\n" + "=" * 65)
    print(f"PROCESSING {filename}")
    print("=" * 65)

    con = None

    try:
        # Download the complete hourly Parquet file.
        response = connect_cloudfront(filename)

        total_bytes = 0

        try:
            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)
        finally:
            response.close()

        print(
            f"Downloaded: {total_bytes / (1024 ** 2):,.2f} MB"
        )

        # Connect DuckDB and register the file.
        con = duckdb.connect()

        parquet_path = temp_file.as_posix().replace("'", "''")

        con.execute(
            f"""
            CREATE VIEW events AS
            SELECT *
            FROM read_parquet('{parquet_path}')
            """
        )

        # Calculate metrics using every row in this hourly file.
        result = con.execute(
            """
            WITH market_counts AS (
                SELECT
                    market,
                    COUNT(*) AS event_count
                FROM events
                WHERE market IS NOT NULL
                GROUP BY market
            ),

            top_market AS (
                SELECT
                    MAX(event_count) AS max_market_events
                FROM market_counts
            ),

            market_summary AS (
                SELECT
                    COUNT(*) AS unique_markets
                FROM market_counts
            )

            SELECT
                COUNT(*) AS total_events,

                COUNT(DISTINCT asset_id)
                    AS unique_assets,

                SUM(
                    CASE WHEN side = 'BUY'
                    THEN 1 ELSE 0 END
                ) AS buy_events,

                SUM(
                    CASE WHEN side = 'SELL'
                    THEN 1 ELSE 0 END
                ) AS sell_events

            FROM events
            """
        ).fetchone()

        total_events, unique_assets, buys, sells = result

        unique_markets = con.execute(
            """
            SELECT COUNT(DISTINCT market)
            FROM events
            WHERE market IS NOT NULL
            """
        ).fetchone()[0]

        max_market_events = con.execute(
            """
            SELECT MAX(event_count)
            FROM (
                SELECT market, COUNT(*) AS event_count
                FROM events
                WHERE market IS NOT NULL
                GROUP BY market
            )
            """
        ).fetchone()[0]

        market_event_total = con.execute(
            """
            SELECT COUNT(*)
            FROM events
            WHERE market IS NOT NULL
            """
        ).fetchone()[0]

        top_market_share = (
            max_market_events / market_event_total * 100
            if market_event_total else None
        )

        buy_share = (
            buys / total_events * 100
            if total_events else None
        )

        row = {
            "date": DATE,
            "hour_utc": hour,
            "total_events": total_events,
            "unique_markets": unique_markets,
            "unique_assets": unique_assets,
            "buy_events": buys,
            "sell_events": sells,
            "buy_share_pct": buy_share,
            "top_market_events": max_market_events,
            "top_market_share_pct": top_market_share,
        }

        print(f"Total events: {total_events:,}")
        print(f"Unique markets: {unique_markets:,}")
        print(f"Unique assets: {unique_assets:,}")
        print(f"BUY events: {buys:,}")
        print(f"SELL events: {sells:,}")
        print(f"BUY share: {buy_share:.2f}%")
        print(f"Top market share: {top_market_share:.2f}%")

        return row

    finally:
        if con is not None:
            con.close()

        if temp_file.exists():
            temp_file.unlink()


# ============================================================
# CREATE SUMMARY AND CHARTS
# ============================================================

def main():

    results = []

    for hour in HOURS:
        try:
            results.append(analyze_hour(hour))

        except Exception as e:
            print(f"\nERROR processing hour {hour:02d}: {e}")
            print("This hour will be excluded from the results.")

    if not results:
        print("No hourly files were successfully analyzed.")
        return

    df = pd.DataFrame(results).sort_values("hour_utc")

    csv_path = OUTPUT_DIR / "hourly_activity_full.csv"
    df.to_csv(csv_path, index=False)

    print("\n" + "=" * 65)
    print("HOURLY SUMMARY")
    print("=" * 65)

    print(
        df[
            [
                "hour_utc",
                "total_events",
                "unique_markets",
                "unique_assets",
                "buy_share_pct",
                "top_market_share_pct",
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # CHART 1: EVENTS PER HOUR
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["hour_utc"],
        df["total_events"],
        marker="o",
        linewidth=2
    )

    plt.xticks(HOURS, [f"{h}:00" for h in df["hour_utc"]])
    plt.xlabel("Hour (UTC)")
    plt.ylabel("Number of Events")
    plt.title("Polymarket Event Activity by Hour")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "hourly_events_full.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # CHART 2: UNIQUE MARKETS PER HOUR
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["hour_utc"],
        df["unique_markets"],
        marker="o",
        linewidth=2
    )

    plt.xticks(HOURS, [f"{h}:00" for h in df["hour_utc"]])
    plt.xlabel("Hour (UTC)")
    plt.ylabel("Unique Active Markets")
    plt.title("Active Markets by Hour")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "hourly_markets_full.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # CHART 3: TOP MARKET SHARE
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["hour_utc"],
        df["top_market_share_pct"],
        marker="o",
        linewidth=2
    )

    plt.xticks(HOURS, [f"{h}:00" for h in df["hour_utc"]])
    plt.xlabel("Hour (UTC)")
    plt.ylabel("Top Market's Share of Events (%)")
    plt.title("Market Concentration by Hour")
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "hourly_concentration_full.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # CHART 4: BUY SHARE
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["hour_utc"],
        df["buy_share_pct"],
        marker="o",
        linewidth=2
    )

    plt.axhline(
        50,
        linestyle="--",
        color="gray",
        label="50%"
    )

    plt.xticks(HOURS, [f"{h}:00" for h in df["hour_utc"]])
    plt.xlabel("Hour (UTC)")
    plt.ylabel("BUY Events (%)")
    plt.title("BUY Share of Events by Hour")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "hourly_buy_share_full.png",
        dpi=150
    )

    plt.close()

    print("\nAnalysis complete.")
    print(f"CSV saved to: {csv_path}")
    print(f"Charts saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()