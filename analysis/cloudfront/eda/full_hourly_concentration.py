import truststore
truststore.inject_into_ssl()

import sys
import csv
import time
from datetime import date, timedelta
from pathlib import Path

# --------------------------------------------------
# PROJECT SETUP
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_cloudfront

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

START_DATE = date(2026, 5, 1)
END_DATE = date(2026, 6, 30)

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "cloudfront" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cloudfront_hourly_availability.csv"


# --------------------------------------------------
# CHECK ONE HOURLY FILE
# --------------------------------------------------

def check_hourly_file(filename):
    response = None

    try:
        response = connect_cloudfront(filename)

        status = response.status_code

        # Record the file size if the server provides it.
        size_bytes = response.headers.get("Content-Length")

        return {
            "filename": filename,
            "status_code": status,
            "accessible": status == 200,
            "size_bytes": size_bytes,
            "error": ""
        }

    except Exception as e:
        return {
            "filename": filename,
            "status_code": None,
            "accessible": False,
            "size_bytes": None,
            "error": str(e)
        }

    finally:
        if response is not None:
            response.close()


# --------------------------------------------------
# CHECK ALL 24 HOURS FOR EACH DATE
# --------------------------------------------------

def main():
    results = []
    complete_days = []

    total_days = (END_DATE - START_DATE).days + 1
    current_date = START_DATE

    print(f"Checking dates from {START_DATE} through {END_DATE}")
    print(f"Total dates to check: {total_days}")
    print("Testing all 24 hourly files for each date...\n")

    for day_number in range(total_days):
        current_date = START_DATE + timedelta(days=day_number)

        accessible_hours = 0
        status_counts = {}

        for hour in range(24):
            filename = (
                f"events-{current_date.isoformat()}T{hour:02d}.parquet"
            )

            result = check_hourly_file(filename)
            result["date"] = current_date.isoformat()
            result["hour_utc"] = hour

            results.append(result)

            if result["accessible"]:
                accessible_hours += 1

            status = result["status_code"]
            status_label = str(status) if status is not None else "ERROR"
            status_counts[status_label] = (
                status_counts.get(status_label, 0) + 1
            )

            # Brief pause between requests.
            time.sleep(0.1)

        print(
            f"{current_date}: {accessible_hours}/24 accessible | "
            f"Statuses: {status_counts}"
        )

        if accessible_hours == 24:
            complete_days.append(current_date.isoformat())
            print(f"  *** COMPLETE DAY FOUND: {current_date} ***")

        # Save progress after every date in case the run is interrupted.
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "date",
                "hour_utc",
                "filename",
                "status_code",
                "accessible",
                "size_bytes",
                "error"
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    if complete_days:
        print("Dates with all 24 hourly files accessible:")
        for day in complete_days:
            print(f"  {day}")
    else:
        print("No dates had all 24 hourly files accessible.")
        print("Review the CSV to see which hours were accessible.")

    print(f"\nDetailed results saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    main()