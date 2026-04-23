# src/data/fetch_wikipedia.py
import requests
import os

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "articles")

WIKIPEDIA_TOPICS = [
    {
        "title": "Stock market",
        "slug": "Stock_market",
        "filename": "wikipedia_stock_market.txt"
    },
    {
        "title": "Bond (finance)",
        "slug": "Bond_(finance)",
        "filename": "wikipedia_bonds.txt"
    },
    {
        "title": "Exchange-traded fund",
        "slug": "Exchange-traded_fund",
        "filename": "wikipedia_etf.txt"
    },
    {
        "title": "Mutual fund",
        "slug": "Mutual_fund",
        "filename": "wikipedia_mutual_fund.txt"
    },
    {
        "title": "Compound interest",
        "slug": "Compound_interest",
        "filename": "wikipedia_compound_interest.txt"
    },
    {
        "title": "Portfolio (finance)",
        "slug": "Portfolio_(finance)",
        "filename": "wikipedia_portfolio.txt"
    },
    {
        "title": "Individual retirement account",
        "slug": "Individual_retirement_account",
        "filename": "wikipedia_ira.txt"
    },
    {
        "title": "401(k)",
        "slug": "401(k)",
        "filename": "wikipedia_401k.txt"
    },
]


def fetch_wikipedia_summary(slug: str) -> str:
    """
    Fetches the introduction/summary section of a Wikipedia article
    using the Wikipedia REST API. Returns plain text.
    """
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    headers = {"User-Agent": "FinnieFinanceBot/1.0 (educational project)"}

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"  Failed to fetch {slug}: HTTP {response.status_code}")
        return ""

    data = response.json()
    extract = data.get("extract", "")
    page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
    return extract, page_url


def fetch_wikipedia_sections(slug: str) -> str:
    """
    Fetches fuller content from Wikipedia using the parse API.
    Returns plain text of the article's intro + key sections.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": False,
        "explaintext": True,
        "titles": slug.replace("_", " "),
        "format": "json",
        "exsectionformat": "plain",
        "exlimit": 1,
    }
    headers = {"User-Agent": "FinnieFinanceBot/1.0 (educational project)"}

    response = requests.get(url, params=params, headers=headers, timeout=15)
    if response.status_code != 200:
        return ""

    data = response.json()
    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if page_id == "-1":
            return ""
        text = page_data.get("extract", "")
        # Limit to first 8000 chars to keep it focused
        return text[:8000]
    return ""


def save_article(topic: dict):
    """
    Fetches Wikipedia content and saves it as a .txt file
    in the articles directory with proper TITLE and SOURCE markers.
    """
    print(f"Fetching: {topic['title']}...")

    try:
        summary, page_url = fetch_wikipedia_summary(topic["slug"])
        full_text = fetch_wikipedia_sections(topic["slug"])

        if not summary and not full_text:
            print(f"  No content found for {topic['title']}")
            return

        # Use full text if available, fall back to summary
        content = full_text if full_text else summary

        # Clean up excessive newlines
        lines = [line.strip() for line in content.split("\n")]
        lines = [l for l in lines if l]
        clean_content = "\n\n".join(lines[:60])  # max 60 paragraphs

        # Format with metadata for RAG citation
        article_text = f"""TITLE: {topic['title']}
SOURCE: Wikipedia
URL: https://en.wikipedia.org/wiki/{topic['slug']}

{clean_content}
"""
        filepath = os.path.join(ARTICLES_DIR, topic["filename"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(article_text)

        print(f"  Saved: {topic['filename']} ({len(clean_content)} chars)")

    except Exception as e:
        print(f"  Error fetching {topic['title']}: {e}")


def fetch_all():
    """Fetches all Wikipedia articles and saves them."""
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    print(f"Saving articles to: {os.path.abspath(ARTICLES_DIR)}\n")

    for topic in WIKIPEDIA_TOPICS:
        save_article(topic)

    print(f"\nDone! Fetched {len(WIKIPEDIA_TOPICS)} Wikipedia articles.")


if __name__ == "__main__":
    fetch_all()