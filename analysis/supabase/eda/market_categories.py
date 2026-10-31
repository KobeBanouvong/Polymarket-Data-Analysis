import sys
import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from database_access.config import connect_supabase

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "supabase" / "outputs"
DATA_DIR = OUTPUT_DIR / "data"
FIGURES_DIR = OUTPUT_DIR / "figures"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_PATH = DATA_DIR / "market_sample_raw.csv"

CATEGORIES = [
    "Sports",
    "Crypto",
    "Politics & Geopolitics",
    "Economics & Business",
    "Esports",
    "Weather & Natural Disasters",
    "Entertainment",
    "Technology & AI",
    "Other / Unclassified"
]

OTHER = "Other / Unclassified"

print("\nPOLYMARKET CATEGORY EDA")

#LOAD MARKET SAMPLE FROM SUPABASE
required_columns = [
    "slug",
    "event_slug",
    "market_title",
    "event_title",
    "condition_id",
    "created_at",
    "start_date",
    "end_date",
    "volume_clob",
    "volume_24hr",
    "volume_1wk",
    "volume_1mo",
    "liquidity_clob",
    "last_trade_price",
    "best_bid",
    "best_ask"
]

if SAMPLE_PATH.exists():
    print("\nChecking cached market sample...")
    df = pd.read_csv(SAMPLE_PATH)

    if not set(required_columns).issubset(df.columns):
        print("Cached sample missing required columns.")
        print("Fetching updated sample...")
        df = None
    else:
        print("Loading cached market sample...")
else:
    df = None

if df is None:

    print("\nConnecting to Supabase...")

    query = """
        SELECT
            m.slug,
            m.event_slug,
            m.title AS market_title,
            e.title AS event_title,
            m.condition_id,
            m.created_at,
            m.start_date,
            m.end_date,
            m.volume_clob,
            m.volume_24hr,
            m.volume_1wk,
            m.volume_1mo,
            m.liquidity_clob,
            m.last_trade_price,
            m.best_bid,
            m.best_ask
        FROM markets AS m
        LEFT JOIN events AS e
            ON m.event_slug = e.slug
        WHERE m.title IS NOT NULL
          AND m.slug IS NOT NULL
          AND (
              ('x' || substr(md5(m.slug), 1, 8))::bit(32)::bigint
              % 10000
          ) < 500
    """

    with connect_supabase() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(SAMPLE_PATH, index=False)

missing = set(required_columns) - set(df.columns)

if missing:
    raise ValueError(f"Missing columns: {missing}")

if df.empty:
    raise ValueError("No markets loaded.")

if df["slug"].duplicated().any():
    raise ValueError("Duplicate market slugs detected.")

print(f"\nMarkets sampled: {len(df):,}")
print(f"Unique events: {df['event_slug'].nunique():,}")
print(f"Duplicate market slugs: {df['slug'].duplicated().sum():,}")



#CATEGORY KEYWORDS
category_patterns = {

    "Sports": [
        r"\bnba\b", r"\bwnba\b", r"\bnfl\b",
        r"\bmlb\b", r"\bnhl\b", r"\bmls\b",
        r"\bsoccer\b", r"\bfootball\b",
        r"\bbasketball\b", r"\bbaseball\b",
        r"\btennis\b", r"\bgolf\b",
        r"\bnascar\b", r"\bformula 1\b",
        r"\bf1\b", r"\bgrand prix\b",
        r"\brugby\b", r"\bcricket\b",
        r"\bkbo\b", r"\buefa\b",
        r"\bwimbledon\b", r"\batp\b",
        r"\bwta\b", r"\bitf\b",
        r"\bdavis cup\b", r"\bpickleball\b",
        r"\bm\d{2}\b", r"\bw\d{2}\b",
        r"\bspread\b", r"\bhandicap\b",
        r"\bmoneyline\b", r"\bexact score\b",
        r"\bexact margin\b", r"\bgoalscorer\b",
        r"\bgoals?\b", r"\btotal corners\b",
        r"\bboth teams to score\b",
        r"\bshots? on target\b",
        r"\b\d+\+?\s+shots?\b",
        r"\bassists?\b", r"\btouchdown\b",
        r"\bpick.six\b", r"\bovertime\b",
        r"\brushing yards\b",
        r"\bpassing yards\b",
        r"\breceiving yards\b",
        r"\btotal bases\b", r"\bhome runs\b",
        r"\btop batter\b", r"\bmost sixes\b",
        r"\bhalftime\b", r"\bfirst half\b",
        r"\bsecond half\b", r"\bstarting 11\b",
        r"\bend in a draw\b",
        r"\bneither team to score\b",
        r"\bset \d+\b", r"\bmatch\b",
        r"\bo/u\b", r"\bover/under\b",
        r"\bworld cup\b", r"\bplayoffs?\b",
        r"\bchampionship\b",
        r"\bquarterfinals?\b",
        r"\bsemi.?finals?\b",
        r"\bfirst inning\b",
        r"\b\d+(?:st|nd|rd|th) inning\b",
        r"\b[1-4]q\b",
        r"\bufc\b", r"\bmma\b",
        r"\bpga tour\b", r"\bdp world tour\b",
        r"\bfight night\b",
        r"\bplayer props?\b",
        r"\bfirst team to score\b",
        r"\bhighest scoring quarter\b",
        r"\bfc\b", r"\bafc\b",
        r"\bfk\b", r"\bcalcio\b",
        r"\bstuttgart open\b",
        r"\batp challenger\b",
        r"\btennis open\b",
        r"\bcopa am[eé]rica\b",
        r"\bkorn ferry tour\b",
        r"\bdana white.s contender series\b"
    ],

    "Crypto": [
        r"\bbitcoin\b", r"\bbtc\b",
        r"\bethereum\b", r"\beth\b",
        r"\bsolana\b", r"\bsol\b",
        r"\bdogecoin\b", r"\bdoge\b",
        r"\bxrp\b", r"\bbnb\b",
        r"\bzcash\b", r"\bcrypto\b",
        r"\bhyperliquid\b", r"\bmetamask\b",
        r"\bblockchain\b", r"\bstablecoin\b",
        r"\bdefi\b", r"\bfdv\b",
        r"\bfully diluted valuation\b",
        r"\bhype up or down\b",
        r"\bmemecoin\b",
        r"\btoken launch\b"
    ],

    "Politics & Geopolitics": [
        r"\belections?\b",
        r"\bpresident\b", r"\bpresidential\b",
        r"\bcongress\b", r"\bsenate\b",
        r"\bgovernor\b", r"\bmayor\b",
        r"\bparliament\b", r"\bprime minister\b",
        r"\brepublicans?\b", r"\bdemocrats?\b",
        r"\bballot\b", r"\bwhite house\b",
        r"\btrump\b", r"\bbiden\b",
        r"\bzelenskyy\b", r"\bputin\b",
        r"\bmamdani\b", r"\bted cruz\b",
        r"\bspeaker of the house\b",
        r"\bhouse seats\b",
        r"\bgovernment shutdown\b",
        r"\bexecutive order\b",
        r"\blegislation\b", r"\bsanctions?\b",
        r"\bceasefire\b", r"\bpeace deal\b",
        r"\bpeace talks\b", r"\bmilitary\b",
        r"\binvasion\b", r"\bannex\b",
        r"\bnato\b", r"\bdiplomatic\b",
        r"\bembargo\b", r"\btrade war\b",
        r"\bukraine\b", r"\brussia\b",
        r"\biran\b", r"\bminister\b",
        r"\bcabinet\b", r"\bgovernment\b"
    ],

    "Economics & Business": [
        r"\bgdp\b", r"\binflation\b",
        r"\binterest rates?\b",
        r"\bfederal reserve\b",
        r"\brecession\b", r"\bunemployment\b",
        r"\bstock market\b", r"\bstock price\b",
        r"\bshare price\b", r"\bearnings\b",
        r"\brevenue\b", r"\bdividend\b",
        r"\bipo\b", r"\bnasdaq\b",
        r"\bs&p 500\b", r"\bmarket cap\b",
        r"\bmarket capitalization\b",
        r"\bcentral bank\b", r"\bnikkei\b",
        r"\bcrude oil\b", r"\bpmi\b",
        r"\bforex\b", r"\bexchange rate\b",
        r"\btreasury yields?\b",
        r"\bconsumer price index\b",
        r"\brichest person\b",
        r"\bmedian home value\b",
        r"\bhousing prices?\b",
        r"\bhome prices?\b",
        r"\betf\b", r"\bnon.gaap\b",
        r"\bjolts\b",
        r"\bjob openings\b",
        r"\bnonfarm payrolls?\b",
        r"\bxagusd\b",
        r"\bxauusd\b",
        r"\bsilver price\b",
        r"\bgold price\b",
        r"\bcommodity prices?\b",
        r"\b(?:usd|eur|gbp|jpy)/[a-z]{3}\b"
    ],

    "Esports": [
        r"\bcounter.strike\b",
        r"\bcs2\b",
        r"\bleague of legends\b",
        r"\blol\b",
        r"\bdota\b",
        r"\bvalorant\b",
        r"\besports?\b",
        r"\bmap \d+\b",
        r"\bslay a dragon\b",
        r"\bbo[135]\b",
        r"\besea advanced\b",
        r"\bblast premier\b",
        r"\bintel extreme masters\b"
    ],

    "Weather & Natural Disasters": [
        r"\btemperature\b",
        r"\brain\b", r"\brainfall\b",
        r"\bsnow\b", r"\bsnowfall\b",
        r"\bhurricane\b", r"\btornado\b",
        r"\bweather\b", r"\bheatwave\b",
        r"\bprecipitation\b",
        r"\bearthquakes?\b",
        r"\btsunami\b", r"\bflood\b",
        r"\bwildfire\b", r"\bwind speed\b"
    ],

    "Entertainment": [
        r"\balbum\b", r"\bgrammy\b",
        r"\boscar\b", r"\bmovie\b",
        r"\bfilm\b", r"\bbillboard\b",
        r"\bspotify\b", r"\bbox office\b",
        r"\bcelebrity\b", r"\bmtv\b",
        r"\bvideo music awards\b",
        r"\bjames bond\b", r"\bmrbeast\b",
        r"\bbig brother\b",
        r"\bstreaming show\b",
        r"\bnetflix show\b",
        r"\bnetflix movie\b",
        r"\bgame awards\b",
        r"\bgrand theft auto\b",
        r"\btv show\b",
        r"\bmost viewed\b",
        r"\boscars\b",
        r"\bacademy awards\b",
        r"\bbest director\b"
    ],

    "Technology & AI": [
        r"\bartificial intelligence\b",
        r"\bai model\b", r"\bai lab\b",
        r"\bai agent\b", r"\bchatgpt\b",
        r"\bopenai\b", r"\banthropic\b",
        r"\bclaude\b", r"\bdeepseek\b",
        r"\bmistral\b", r"\bfrontiermath\b",
        r"\bbenchmark\b", r"\bllm\b",
        r"\bmachine learning\b",
        r"\bneural network\b",
        r"\bwwdc\b", r"\bapple keynote\b",
        r"\bai training\b",
        r"\bperplexity\b"
    ]
}


#COMPILE KEYWORDS AND CONTEXT PATTERNS
compiled_patterns = {
    category: [
        re.compile(pattern, re.IGNORECASE)
        for pattern in patterns
    ]
    for category, patterns in category_patterns.items()
}

financial_tickers = re.compile(
    r"\((?:AAPL|MSFT|TSLA|META|NFLX|NVDA|"
    r"AMZN|GOOGL|GOOG|MU|ABNB|SPY|MSTR|"
    r"KO|OPEN|SKHY)\)",
    re.IGNORECASE
)

financial_context = re.compile(
    r"\b(?:stock|shares?|earnings|revenue|"
    r"market cap|trading day|trading week|"
    r"finish week)\b",
    re.IGNORECASE
)

technology_context = re.compile(
    r"\b(?:ai model|ai lab|ai agent|"
    r"frontiermath|chatgpt|model benchmark)\b",
    re.IGNORECASE
)

strong_sports_context = re.compile(
    r"\b(?:"
    r"total corners|corner kicks?|"
    r"shots? on target|"
    r"player props?|"
    r"moneyline|"
    r"both teams to score|"
    r"first team to score|"
    r"total goals?|"
    r"goal scorer|goalscorer|"
    r"touchdowns?|"
    r"rushing yards|passing yards|receiving yards|"
    r"total bases|home runs|"
    r"first inning|"
    r"copa am[eé]rica|"
    r"korn ferry tour|"
    r"dana white.s contender series"
    r")\b",
    re.IGNORECASE
)

sports_match_pattern = re.compile(
    r"\bvs\.?\s+",
    re.IGNORECASE
)

sports_team_pattern = re.compile(
    r"\b(?:"
    r"fc|afc|fk|cf|sc|"
    r"marlins|diamondbacks|"
    r"nba|nfl|mlb|nhl|"
    r"tennis|basketball|baseball|soccer"
    r")\b",
    re.IGNORECASE
)


#CLASSIFY MARKETS
def classify_market(row):

    market_title = (
        str(row["market_title"])
        if pd.notna(row["market_title"])
        else ""
    )

    event_title = (
        str(row["event_title"])
        if pd.notna(row["event_title"])
        else ""
    )

    text = f"{market_title} {event_title}"

    matches = [
        category
        for category, patterns in compiled_patterns.items()
        if any(pattern.search(text) for pattern in patterns)
    ]

    original_matches = matches.copy()

    # Esports first to prevent incorrect Sports assignment
    if "Esports" in matches:
        return "Esports", original_matches

    # Strong sports context
    if strong_sports_context.search(text):
        return "Sports", original_matches

    # Recognizable sports matchups
    if (
        sports_match_pattern.search(text)
        and sports_team_pattern.search(text)
    ):
        return "Sports", original_matches

    # Financial ticker
    if financial_tickers.search(text):
        return "Economics & Business", original_matches

    # Technology context
    if technology_context.search(text):
        return "Technology & AI", original_matches

    # Financial context
    if (
        financial_context.search(text)
        and "Economics & Business" in matches
    ):
        return "Economics & Business", original_matches

    # Crypto and finance overlap
    if "Crypto" in matches:
        if "Economics & Business" in matches:
            matches.remove("Economics & Business")

    if len(matches) == 1:
        return matches[0], original_matches

    return OTHER, original_matches



#SAVE PREVIOUS CLASSIFICATIONS
previous_path = DATA_DIR / "market_category_sample.csv"

if previous_path.exists():

    previous = pd.read_csv(
        previous_path,
        usecols=["slug", "category"]
    ).rename(columns={"category": "old_category"})

else:
    previous = None


#CLASSIFY MARKETS
print("\nClassifying markets...")

results = df.apply(classify_market, axis=1)

df["category"] = results.apply(lambda x: x[0])

df["matched_categories"] = results.apply(
    lambda x: ", ".join(x[1])
)

df["match_count"] = results.apply(
    lambda x: len(x[1])
)

df["classification_review_needed"] = (
    (df["match_count"] != 1)
    | (df["category"] == OTHER)
)


#EVENT-LEVEL CLASSIFICATION
def classify_event(group):

    titles = group["event_title"].dropna()

    event_title = (
        str(titles.iloc[0])
        if not titles.empty
        else ""
    )

    if event_title.strip():

        category, matches = classify_market(
            pd.Series({
                "market_title": "",
                "event_title": event_title
            })
        )

        if category != OTHER:
            return category

    votes = (
        group.loc[
            group["category"] != OTHER,
            "category"
        ]
        .value_counts()
    )

    if votes.empty:
        return OTHER

    if len(votes) > 1 and votes.iloc[0] == votes.iloc[1]:
        return OTHER

    return votes.index[0]


print("\nClassifying unique events...")

event_labels = (
    df.dropna(subset=["event_slug"])
    .groupby("event_slug", sort=False)
    .apply(classify_event, include_groups=False)
    .rename("event_category")
    .reset_index()
)

df = df.merge(
    event_labels,
    on="event_slug",
    how="left",
    validate="many_to_one"
)

print(f"Unique events classified: {len(event_labels):,}")


#MARKET CATEGORY DISTRIBUTION
category_counts = (
    df["category"]
    .value_counts()
    .reindex(CATEGORIES, fill_value=0)
    .rename_axis("category")
    .reset_index(name="market_count")
)

category_counts["percentage"] = (
    category_counts["market_count"]
    / len(df) * 100
).round(2)

print("\nMARKET DISTRIBUTION BY CATEGORY")
print("-" * 65)
print(category_counts.to_string(index=False))

assert category_counts["market_count"].sum() == len(df)



#UNIQUE EVENT DISTRIBUTION
event_counts = (
    event_labels["event_category"]
    .value_counts()
    .reindex(CATEGORIES, fill_value=0)
    .rename_axis("category")
    .reset_index(name="unique_events")
)

total_unique_events = len(event_labels)

event_counts["event_percentage"] = (
    event_counts["unique_events"]
    / total_unique_events * 100
).round(2)

print("\nUNIQUE EVENTS BY CATEGORY")
print("-" * 65)
print(event_counts.to_string(index=False))

assert (
    event_counts["unique_events"].sum()
    == total_unique_events
)


#MARKET VS EVENT COMPARISON
comparison = category_counts.merge(
    event_counts,
    on="category",
    how="left"
)

print("\nMARKETS VS UNIQUE EVENTS")
print("-" * 65)
print(comparison.to_string(index=False))


#VISUALIZATIONS
def save_bar_chart(data, column, title, filename):

    chart_data = data.sort_values(
        column,
        ascending=False
    )

    fig, ax = plt.subplots(figsize=(12, 7))

    bars = ax.barh(
        chart_data["category"],
        chart_data[column],
        color="#277DA1"
    )

    ax.invert_yaxis()

    ax.set_xlabel(
        column.replace("_", " ").title()
    )

    ax.set_title(
        title,
        fontsize=16,
        fontweight="bold"
    )

    max_value = max(chart_data[column].max(), 1)

    for bar in bars:

        width = bar.get_width()

        ax.text(
            width + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{int(width):,}",
            va="center",
            fontsize=10
        )

    ax.set_xlim(0, max_value * 1.2)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(
        axis="x",
        alpha=0.2,
        linestyle="--"
    )

    ax.set_axisbelow(True)

    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / filename,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)


save_bar_chart(
    category_counts,
    "market_count",
    "Polymarket Markets by Inferred Category",
    "market_category_distribution.png"
)

save_bar_chart(
    event_counts,
    "unique_events",
    "Unique Events by Inferred Category",
    "event_category_distribution.png"
)

print("\nVisualizations generated.")


#CLASSIFICATION COVERAGE
classified_count = (
    df["category"] != OTHER
).sum()

unclassified_count = (
    df["category"] == OTHER
).sum()

coverage = (
    classified_count / len(df) * 100
)

ambiguous = df[
    df["match_count"] > 1
].copy()

review_needed = df[
    df["classification_review_needed"]
].copy()

print("\nCLASSIFICATION COVERAGE")
print("-" * 65)

print(f"Classified markets: {classified_count:,}")
print(f"Unclassified markets: {unclassified_count:,}")
print(f"Classification coverage: {coverage:.2f}%")
print(f"Multiple category matches: {len(ambiguous):,}")
print(f"Flagged for review: {len(review_needed):,}")



#BEFORE VS AFTER COMPARISON
if previous is not None:

    comparison_df = df[["slug", "category"]].merge(
        previous.drop_duplicates("slug"),
        on="slug",
        how="left",
        validate="one_to_one"
    )

    changed = comparison_df[
        comparison_df["old_category"].notna()
        & (
            comparison_df["category"]
            != comparison_df["old_category"]
        )
    ].copy()

    print("\nCLASSIFICATION CHANGES")
    print("-" * 65)

    print(f"Markets with changed categories: {len(changed):,}")

    changes_summary = (
        changed.groupby(
            ["old_category", "category"]
        )
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    print("\nMost common category changes:")
    print(changes_summary.head(15).to_string(index=False))

    changed.to_csv(
        DATA_DIR / "classification_changes.csv",
        index=False
    )

    changes_summary.to_csv(
        DATA_DIR / "classification_changes_summary.csv",
        index=False
    )



#RESULTS CSV
category_counts.to_csv(DATA_DIR / "market_category_counts.csv",index=False)
event_counts.to_csv(DATA_DIR / "event_category_counts.csv",index=False)
comparison.to_csv(DATA_DIR / "market_event_comparison.csv",index=False)
df.to_csv(DATA_DIR / "market_category_sample.csv",index=False)
ambiguous.to_csv(DATA_DIR / "ambiguous_markets.csv",index=False)
df[df["category"] == OTHER].to_csv(DATA_DIR / "unclassified_markets.csv",index=False)
event_labels.to_csv(DATA_DIR / "event_category_labels.csv",index=False)
review_needed.to_csv(DATA_DIR / "classification_review.csv",index=False)
print(f"\nCSV results saved to: {DATA_DIR}")
print(f"Figures saved to: {FIGURES_DIR}")

