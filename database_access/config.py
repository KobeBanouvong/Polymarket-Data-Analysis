
import os
import certifi
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

# Locate the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load credentials from .env
load_dotenv(PROJECT_ROOT / ".env", override=True)


# Supabase PostgreSQL connection
def connect_supabase():
    return psycopg2.connect(
        host="aws-0-us-west-2.pooler.supabase.com",
        port=6543,
        dbname="postgres",
        user="polymarketdatabase.merbqatlxbrcvtbnuaqe",
        password=os.environ["POLYMARKET_PASSWORD"],
        sslmode="require",
        connect_timeout=15
    )


def connect_cloudfront(filename, check_only=False):
    url = "https://d1yyqbluk0oz0t.cloudfront.net/" + filename

    response = requests.get(
        url,
        auth=(
            "polymarketdatabase",
            os.environ["POLYMARKET_PASSWORD"]
        ),
        stream=True,
        timeout=30
    )

    # In discovery mode, return 403/404 responses so we can
    # distinguish access denied from files not found.
    if check_only:
        return response

    response.raise_for_status()
    return response