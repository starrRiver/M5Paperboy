"""
M5Paperboy — daily news fetcher.
Sections: Fintech & Payments, Case Law, Financial Times RSS.
"""

import anthropic
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FT_RSS_URL = "https://www.ft.com/myft/following/8754710d-d3c1-4457-9263-f9b89b5b8840.rss"

YESTERDAY = (datetime.now(timezone.utc) - timedelta(days=1))
YESTERDAY_STR = YESTERDAY.strftime("%A, %d %B %Y")
LAST_30 = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%d %B %Y")

# ── System prompts ─────────────────────────────────────────────────────────────

FINTECH_SYSTEM = """You are a legal and regulatory intelligence analyst specialising in fintech,
payments, and financial services law, with a focus on APAC markets and cross-border payments.

Your reader is a senior product lawyer at Airwallex — a global payments and financial
infrastructure company headquartered in Melbourne, with major operations across APAC, Europe,
and the US.

Relevant topics:
- Payment service provider licensing and regulatory updates (ASIC, MAS, HKMA, FCA, FINTRAC,
  RBI, PBOC, BoT, BSP, OJK, JFSA, etc.)
- Cross-border payments regulation and FX controls
- Card scheme rule changes (Visa, Mastercard, UnionPay)
- Open banking and data portability regulation
- Enforcement actions against payment companies or fintechs
- Airwallex news (regulatory approvals, enforcement, partnerships, funding)
- Competitor moves (Wise, Stripe, Adyen, Revolut, PayPal, etc.) that signal regulatory trends
- AML / sanctions / FATF developments relevant to payment companies
- Embedded finance and BaaS regulation

EXCLUDE: general cryptocurrency or blockchain news unless it directly concerns stablecoin
payment regulation, CBDC infrastructure, or crypto licensing rules that affect payment
companies operating in that space. Do not include speculative crypto price or market news.

Return ONLY a JSON array. No preamble, no markdown fences.
Each object must have exactly:
  "title": string (headline, max 90 chars)
  "source": string (publication or regulator name)
  "date": string (YYYY-MM-DD)
  "summary": string (300-400 word article in newspaper prose, collated from multiple sources:
    (1) lede with specific names, numbers, dates;
    (2) full regulatory/legal detail — rules, thresholds, deadlines, penalties, exact provisions;
    (3) reactions, context, analyst views, how this fits the broader trend;
    (4) Airwallex-specific angle — licensing exposure, product impact, competitive signal,
    or legal precedent a product lawyer must act on.)
  "url": string (direct URL)
  "region": string (one of: "APAC", "Europe", "Americas", "Global")
  "tags": array of 2-4 strings

Return between 0 and 10 articles. If nothing significant was published yesterday, return [].
Do not pad with old or marginal stories."""

CASELAW_SYSTEM = """You are a commercial law clerk preparing a daily case law digest for a
senior in-house lawyer at a fintech company.

Cover recent judgments in:
- Company law (directors' duties, corporate governance, shareholder rights, corporate liability)
- Contract law (interpretation, implied terms, exclusion clauses, breach, remedies, good faith)

Jurisdictions: England & Wales, Australia, Singapore, Hong Kong, New Zealand, Canada, Ireland.
Courts: High Court / Supreme Court / Court of Appeal / equivalent superior courts only.
Time window: last 30 days.

Return ONLY a JSON array. No preamble, no markdown fences.
Each object must have exactly:
  "title": string (case name and neutral citation, e.g. "Smith v Jones [2026] UKSC 4")
  "source": string (court name, e.g. "UK Supreme Court")
  "date": string (YYYY-MM-DD judgment date)
  "summary": string (200-300 word digest: (1) facts in 2-3 sentences; (2) legal issue(s);
    (3) holding and key reasoning; (4) significance for commercial practitioners —
    what this changes or clarifies, and relevance to fintech/payments if any.)
  "url": string (link to judgment or BAILII/LawCite/official court website)
  "region": string (jurisdiction, e.g. "England & Wales")
  "tags": array of 2-4 strings (e.g. ["directors-duties", "company-law", "UK"])

Return between 0 and 5 cases. If no significant judgments in the last 30 days, return []."""


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_text(response):
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:]
    if text.endswith("```"):
        text = text[:text.rindex("```")]
    return text.strip()


def two_step_search(client, system_prompt, search_prompt, json_prompt, max_searches=15):
    """Search step then JSON extraction step."""
    search_resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": search_prompt}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches}],
    )
    search_summary = extract_text(search_resp)
    print(f"  Search done ({len(search_summary)} chars).")

    json_resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=16000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": search_prompt},
            {"role": "assistant", "content": search_resp.content},
            {"role": "user", "content": json_prompt},
        ],
    )
    text = strip_fences(extract_text(json_resp))
    print(f"  JSON done (first 100 chars): {text[:100]}")
    return json.loads(text)


# ── Fintech news ───────────────────────────────────────────────────────────────

def fetch_fintech_news(client):
    print("Fetching fintech news...")
    search_prompt = (
        f"Today is {datetime.now(timezone.utc).strftime('%A, %d %B %Y')}. "
        f"Search for fintech, payments, and financial services legal/regulatory news "
        f"published on {YESTERDAY_STR}. "
        "Search multiple sources: regulator websites (ASIC, MAS, HKMA, FCA, etc.), "
        "Reuters, Bloomberg, Financial Times, Law360, Finextra, Payments Dive, "
        "and official government/court publications. "
        "Focus on news directly relevant to a product lawyer at Airwallex. "
        "Exclude general crypto/blockchain speculation. "
        "If nothing significant was published yesterday, that is fine — return an empty list."
    )
    json_prompt = (
        "Based on your research, produce the final JSON array now. "
        "Return ONLY the JSON array — no explanation, no markdown fences. "
        "If you found no relevant articles from yesterday, return []. "
        "Do not include articles from earlier dates to pad the list."
    )
    try:
        articles = two_step_search(client, FINTECH_SYSTEM, search_prompt, json_prompt)
        return articles[:10]
    except Exception as e:
        print(f"  Fintech fetch error: {e}")
        return []


# ── Case law ───────────────────────────────────────────────────────────────────

def fetch_case_law(client):
    print("Fetching case law...")
    search_prompt = (
        f"Today is {datetime.now(timezone.utc).strftime('%A, %d %B %Y')}. "
        f"Search for significant company law and contract law judgments handed down "
        f"since {LAST_30} in England & Wales, Australia, Singapore, Hong Kong, "
        "New Zealand, Canada, and Ireland. "
        "Search BAILII, AustLII, LawNet Singapore, HKLII, the UK Supreme Court website, "
        "and legal news sources (Lexology, Practical Law, Herbert Smith Freehills insights). "
        "Focus on superior court decisions only (Supreme Court, Court of Appeal, High Court). "
        "If no significant judgments in this period, return an empty list."
    )
    json_prompt = (
        "Based on your research, produce the final JSON array of case law digests. "
        "Return ONLY the JSON array — no explanation, no markdown fences. "
        "If you found no significant cases, return []."
    )
    try:
        cases = two_step_search(client, CASELAW_SYSTEM, search_prompt, json_prompt, max_searches=10)
        return cases[:5]
    except Exception as e:
        print(f"  Case law fetch error: {e}")
        return []


# ── FT RSS ─────────────────────────────────────────────────────────────────────

def fetch_ft_rss():
    print("Fetching FT RSS...")
    try:
        resp = requests.get(
            FT_RSS_URL,
            timeout=15,
            headers={"User-Agent": "M5Paperboy/1.0"}
        )
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:10]
        articles = []
        for item in items:
            title   = (item.findtext("title") or "").strip()
            url     = (item.findtext("link") or "").strip()
            desc    = (item.findtext("description") or "").strip()
            pub_raw = (item.findtext("pubDate") or "").strip()
            try:
                date = parsedate_to_datetime(pub_raw).strftime("%Y-%m-%d")
            except Exception:
                date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Strip any HTML tags from description
            import re
            desc = re.sub(r"<[^>]+>", "", desc).strip()

            if title:
                articles.append({
                    "title":   title[:90],
                    "source":  "Financial Times",
                    "date":    date,
                    "summary": desc or title,
                    "url":     url,
                    "region":  "Global",
                    "tags":    ["FT", "myFT"],
                })
        print(f"  Got {len(articles)} FT items.")
        return articles
    except Exception as e:
        print(f"  FT RSS error: {e}")
        return []


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    fintech = fetch_fintech_news(client)
    caselaw = fetch_case_law(client)
    ft      = fetch_ft_rss()

    sections = []
    if fintech:
        sections.append({"id": "fintech", "title": "Fintech & Payments", "articles": fintech})
    if caselaw:
        sections.append({"id": "caselaw", "title": "Case Law",           "articles": caselaw})
    if ft:
        sections.append({"id": "ft",      "title": "Financial Times",    "articles": ft})

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date":         YESTERDAY.strftime("%Y-%m-%d"),
        "sections":     sections,
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/articles.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(s["articles"]) for s in sections)
    print(f"Done. {total} articles across {len(sections)} sections.")


if __name__ == "__main__":
    main()
