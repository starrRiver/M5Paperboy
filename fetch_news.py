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
  "summary": string (6-8 sentences in plain English: what happened, which regulator or company is involved, what the rule or enforcement action requires, key dates or numbers, and why this matters specifically to Airwallex — e.g. licensing exposure, operational impact, competitive signal, or precedent risk)
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


def extract_text(response) -> str:
    """Pull all text blocks out of a response and join them."""
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


def strip_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]  # drop the opening ``` line
    if text.endswith("```"):
        text = text[:text.rindex("```")]
    return text.strip()


def fetch_articles() -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    # Step 1: use web_search to gather raw news
    search_prompt = (
        f"Today is {today}. Search for the most important fintech, payments, and financial "
        "services legal/regulatory news from the last 7 days. Focus on: payment licensing, "
        "APAC regulators (ASIC, MAS, HKMA), cross-border payments, FX regulation, AML/sanctions, "
        "and news about Airwallex, Wise, Stripe, Revolut, or Adyen. "
        "Gather at least 10 relevant articles. For each, note the headline, source, date, URL, and a brief description."
    )

    search_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": search_prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
    )
    search_summary = extract_text(search_response)
    print(f"Search step done. Summary length: {len(search_summary)} chars.")

    # Step 2: convert the gathered info into strict JSON
    json_prompt = (
        "Based on the articles you just found, produce the final JSON array now. "
        "Return ONLY the JSON array — no explanation, no markdown fences. "
        "Each object must have: title, source, date (YYYY-MM-DD), summary (2 sentences), url, region, tags."
    )

    json_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": search_prompt},
            {"role": "assistant", "content": search_response.content},
            {"role": "user", "content": json_prompt},
        ],
    )

    text = strip_fences(extract_text(json_response))
    print(f"JSON step done. Raw output (first 200 chars): {text[:200]}")

    articles = json.loads(text)
    return articles[:10]


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
