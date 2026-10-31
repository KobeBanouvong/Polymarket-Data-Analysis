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

FILENAME = "events-2026-05-30T21.parquet"
TEMP_FILE = OUTPUT_DIR / "temp_full_activity.parquet"


# ============================================================
# 1. DOWNLOAD FULL CLOUD FRONT FILE
# ============================================================

def download_file():

    print("=" * 65)
    print("DOWNLOADING FULL CLOUD FRONT FILE")
    print("=" * 65)

    response = connect_cloudfront(FILENAME)

    total_bytes = 0

    try:
        with open(TEMP_FILE, "wb") as f:

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


# ============================================================
# 2. ANALYZE MINUTE-LEVEL ACTIVITY
# ============================================================

def analyze_activity(con):

    print("\n" + "=" * 65)
    print("FULL DATASET: MINUTE-LEVEL ACTIVITY")
    print("=" * 65)

    # Group events into one-minute intervals.
    # ts_ms contains Unix timestamps in milliseconds.

    activity = con.execute(
        """
        SELECT
            CAST(FLOOR(ts_ms / 60000) AS BIGINT)
                AS minute_id,

            COUNT(*) AS event_count,

            COUNT(DISTINCT market) AS active_markets,

            COUNT(DISTINCT asset_id) AS active_assets,

            SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END)
                AS buy_events,

            SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END)
                AS sell_events

        FROM events

        WHERE ts_ms IS NOT NULL

        GROUP BY minute_id
        ORDER BY minute_id
        """
    ).df()

    activity["timestamp"] = pd.to_datetime(
        activity["minute_id"] * 60000,
        unit="ms",
        utc=True
    )

    activity["buy_share_pct"] = (
        activity["buy_events"]
        / activity["event_count"] * 100
    )

    activity.to_csv(
        OUTPUT_DIR / "full_minute_activity.csv",
        index=False
    )

    print("\nMinute-level activity summary:")

    print(
        activity[
            [
                "event_count",
                "active_markets",
                "active_assets",
                "buy_share_pct"
            ]
        ].describe().to_string()
    )

    print("\nMost active minute:")

    busiest = activity.loc[
        activity["event_count"].idxmax()
    ]

    print(
        f"{busiest['timestamp']}: "
        f"{busiest['event_count']:,} events"
    )

    print("\nLeast active minute:")

    quietest = activity.loc[
        activity["event_count"].idxmin()
    ]

    print(
        f"{quietest['timestamp']}: "
        f"{quietest['event_count']:,} events"
    )

    return activity


# ============================================================
# 3. ANALYZE MARKET CONCENTRATION BY MINUTE
# ============================================================

def analyze_minute_concentration(con):

    print("\n" + "=" * 65)
    print("MINUTE-LEVEL MARKET CONCENTRATION")
    print("=" * 65)

    # First count events for each market in each minute.
    # Then calculate the largest market's share.

    concentration = con.execute(
        """
        WITH market_minute AS (

            SELECT
                CAST(FLOOR(ts_ms / 60000) AS BIGINT)
                    AS minute_id,

                market,

                COUNT(*) AS market_events

            FROM events

            WHERE
                ts_ms IS NOT NULL
                AND market IS NOT NULL

            GROUP BY
                minute_id,
                market
        )

        SELECT
            minute_id,

            SUM(market_events) AS total_market_events,

            MAX(market_events) AS top_market_events,

            COUNT(*) AS active_markets,

            100.0 * MAX(market_events)
                / SUM(market_events)
                AS top_market_share_pct

        FROM market_minute

        GROUP BY minute_id
        ORDER BY minute_id
        """
    ).df()

    concentration["timestamp"] = pd.to_datetime(
        concentration["minute_id"] * 60000,
        unit="ms",
        utc=True
    )

    concentration.to_csv(
        OUTPUT_DIR / "full_minute_concentration.csv",
        index=False
    )

    print("\nConcentration summary:")

    print(
        concentration[
            [
                "top_market_share_pct",
                "active_markets"
            ]
        ].describe().to_string()
    )

    return concentration


# ============================================================
# 4. CREATE VISUALIZATIONS
# ============================================================

def create_plots(activity, concentration):

    print("\n" + "=" * 65)
    print("CREATING VISUALIZATIONS")
    print("=" * 65)

    # --------------------------------------------------------
    # CHART 1: EVENTS PER MINUTE
    # --------------------------------------------------------

    plt.figure(figsize=(12, 6))

    plt.plot(
        activity["timestamp"],
        activity["event_count"],
        linewidth=2
    )

    plt.title(
        "Polymarket Event Activity by Minute\n"
        "May 30, 2026 | 21:00–22:00 UTC"
    )

    plt.xlabel("Time (UTC)")
    plt.ylabel("Number of Events")

    plt.grid(alpha=0.3)
    plt.xticks(rotation=30)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "full_minute_activity.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # CHART 2: ACTIVE MARKETS PER MINUTE
    # --------------------------------------------------------

    plt.figure(figsize=(12, 6))

    plt.plot(
        activity["timestamp"],
        activity["active_markets"],
        linewidth=2
    )

    plt.title(
        "Number of Active Polymarket Markets by Minute\n"
        "May 30, 2026 | 21:00–22:00 UTC"
    )

    plt.xlabel("Time (UTC)")
    plt.ylabel("Unique Active Markets")

    plt.grid(alpha=0.3)
    plt.xticks(rotation=30)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "full_active_markets.png",
        dpi=150
    )

    plt.close()

    # --------------------------------------------------------
    # CHART 3: TOP MARKET SHARE BY MINUTE
    # --------------------------------------------------------

    plt.figure(figsize=(12, 6))

    plt.plot(
        concentration["timestamp"],
        concentration["top_market_share_pct"],
        linewidth=2
    )

    plt.title(
        "Most Active Market's Share of Events by Minute\n"
        "May 30, 2026 | 21:00–22:00 UTC"
    )

    plt.xlabel("Time (UTC)")
    plt.ylabel("Top Market Share (%)")

    plt.grid(alpha=0.3)
    plt.xticks(rotation=30)
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "full_minute_concentration.png",
        dpi=150
    )

    plt.close()

    print("Saved full_minute_activity.png")
    print("Saved full_active_markets.png")
    print("Saved full_minute_concentration.png")


# ============================================================
# 5. MAIN
# ============================================================

def main():

    con = None

    try:

        download_file()

        con = duckdb.connect()

        # DuckDB reads directly from the Parquet file.
        # Create a view using the full Parquet file
        parquet_path = TEMP_FILE.as_posix().replace("'", "''")

        con.execute(
            f"""
            CREATE VIEW events AS
            SELECT *
            FROM read_parquet('{parquet_path}')
            """
)

        total_rows = con.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        print(f"\nTotal records: {total_rows:,}")

        activity = analyze_activity(con)

        concentration = analyze_minute_concentration(con)

        create_plots(activity, concentration)

        print("\n" + "=" * 65)
        print("ANALYSIS COMPLETE")
        print("=" * 65)

        print(f"Results saved to: {OUTPUT_DIR}")

    finally:

        if con is not None:
            con.close()

        if TEMP_FILE.exists():
            TEMP_FILE.unlink()
            print("Temporary Parquet file removed.")


if __name__ == "__main__":
    main()