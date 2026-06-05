"""
M5Paperboy — daily fintech/legal news fetcher.
Runs via GitHub Actions, writes articles.json to the repo for GitHub Pages hosting.
"""

import anthropic
import json
import os
from datetime import datetime, timezone

SYSTEM_PROMPT = """You are a legal and regulatory intelligence analyst specialising in fintech,
payments, and financial services law — with a focus on APAC markets and cross-border payments.

Your job is to surface the most relevant recent news for a senior fintech product lawyer at Airwallex.
Airwallex is a global payments and financial infrastructure company, headquartered in Melbourne,
with major operations across APAC, Europe, and the US.

Relevant topics include:
- Payment service provider licensing and regulatory updates (ASIC, MAS, HKMA, FCA, FINTRAC, etc.)
- Cross-border payments regulation and FX controls
- Stablecoin and crypto regulation affecting payments infrastructure
- Card scheme rules changes (Visa, Mastercard)
- Open banking and data portability regulation
- Enforcement actions against payment companies or fintechs
- Airwallex news (funding, partnerships, regulatory approvals, enforcement)
- Competitor news (Wise, Stripe, Adyen, Revolut, etc.) that signals regulatory trends
- FATF / AML / sanctions developments relevant to payment companies

Return ONLY a JSON array. No preamble, no explanation, no markdown fences.
Each object must have exactly these fields:
  "title": string (the article headline, max 80 chars)
  "source": string (publication name, e.g. "Reuters", "ASIC", "Financial Times")
  "date": string (ISO 8601 date, e.g. "2026-06-06")
  "summary": string (2 sentences max, plain English, why this matters to Airwallex)
  "url": string (direct URL to the article)
  "region": string (one of: "APAC", "Europe", "Americas", "Global")
  "tags": array of strings (2-4 tags, e.g. ["licensing", "MAS", "Singapore"])

Return between 5 and 10 articles. Prioritise freshness (last 7 days) and direct relevance.
Do not include paywalled articles where the URL leads to a login wall with no preview.
"""

USER_PROMPT = f"""Today is {datetime.now(timezone.utc).strftime('%A, %d %B %Y')}.

Search for the most important fintech, payments, and financial services legal/regulatory news
from the last 7 days. Focus on developments that matter to a product lawyer at Airwallex.

Return the results as a JSON array per your instructions."""


def fetch_articles() -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
    )

    # Extract the final text block (after any tool use)
    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text

    # Strip any accidental markdown fences
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    articles = json.loads(text)
    return articles[:10]  # hard cap at 10


def main():
    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Got {len(articles)} articles.")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/articles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Written to docs/articles.json")


if __name__ == "__main__":
    main()
