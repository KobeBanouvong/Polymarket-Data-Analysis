import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from config import connect_supabase, connect_cloudfront

#Test 1: Supabase
print("Testing Supabase connection...")

try:
    conn = connect_supabase()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM markets;")
    count = cur.fetchone()[0]

    print("Supabase connected successfully!")
    print(f"Total markets: {count:,}")

    cur.close()
    conn.close()

except Exception as e:
    print("Supabase connection failed:", e)


#Test 2:Cloud Front
print("\nTesting CloudFront connection...")

try:
    response = connect_cloudfront(
        "events-2026-05-30T21.parquet"
    )

    print("CloudFront connected successfully!")
    print("Status code:", response.status_code)

    response.close()

except Exception as e:
    print("CloudFront connection failed:", e)

