"""
M5Paperboy — M5Paper S3 firmware (MicroPython)
Fetches articles.json from GitHub Pages and renders on e-ink display.

Flash this file as main.py using M5Burner or Thonny.
Edit WIFI_SSID, WIFI_PASSWORD, and ARTICLES_URL below before flashing.
"""

import network
import urequests
import ujson
import time
from m5stack import *
from m5stack_ui import *
from uiflow import *

# ── Configuration ──────────────────────────────────────────────────────────────
WIFI_SSID     = "YOUR_WIFI_NAME"       # Replace with your WiFi name
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"   # Replace with your WiFi password
ARTICLES_URL  = "https://YOUR_GITHUB_USERNAME.github.io/M5Paperboy/articles.json"
# ───────────────────────────────────────────────────────────────────────────────

SCREEN_W = 960
SCREEN_H = 540
MARGIN   = 20
LINE_H   = 22

# Colours (e-paper: only black/white meaningful)
BLACK = 0x000000
WHITE = 0xFFFFFF
GRAY  = 0x888888


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    return wlan.isconnected()


def fetch_articles():
    resp = urequests.get(ARTICLES_URL, timeout=15)
    data = ujson.loads(resp.text)
    resp.close()
    return data


def wrap_text(text, max_chars):
    """Break text into lines of at most max_chars characters."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_article(screen, article, index, total):
    screen.clean_screen()
    y = MARGIN

    # ── Header bar ────────────────────────────────────────────────────────────
    screen.draw_line(MARGIN, y + LINE_H + 4, SCREEN_W - MARGIN, y + LINE_H + 4, BLACK)
    screen.draw_string(
        f"M5Paperboy  •  {article.get('date', '')}  •  {index}/{total}",
        MARGIN, y, BLACK, WHITE, font=FONT_MONT_14
    )
    y += LINE_H + 12

    # ── Region / source pill ──────────────────────────────────────────────────
    region = article.get("region", "")
    source = article.get("source", "")
    screen.draw_string(f"[{region}]  {source}", MARGIN, y, GRAY, WHITE, font=FONT_MONT_14)
    y += LINE_H + 6

    # ── Headline ─────────────────────────────────────────────────────────────
    title_lines = wrap_text(article.get("title", ""), 55)
    for line in title_lines[:3]:
        screen.draw_string(line, MARGIN, y, BLACK, WHITE, font=FONT_MONT_22)
        y += 28
    y += 6

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_lines = wrap_text(article.get("summary", ""), 80)
    for line in summary_lines[:6]:
        screen.draw_string(line, MARGIN, y, BLACK, WHITE, font=FONT_MONT_14)
        y += LINE_H
    y += 8

    # ── Tags ──────────────────────────────────────────────────────────────────
    tags = "  #".join(article.get("tags", []))
    if tags:
        screen.draw_string(f"#{tags}", MARGIN, y, GRAY, WHITE, font=FONT_MONT_14)
        y += LINE_H + 4

    # ── Footer: navigation hint ───────────────────────────────────────────────
    screen.draw_line(MARGIN, SCREEN_H - 36, SCREEN_W - MARGIN, SCREEN_H - 36, BLACK)
    screen.draw_string(
        "BTN-A: previous    BTN-B: next    BTN-C: refresh",
        MARGIN, SCREEN_H - 24, GRAY, WHITE, font=FONT_MONT_14
    )

    screen.push()  # flush to e-ink panel


def show_message(screen, line1, line2=""):
    screen.clean_screen()
    screen.draw_string(line1, MARGIN, SCREEN_H // 2 - 20, BLACK, WHITE, font=FONT_MONT_22)
    if line2:
        screen.draw_string(line2, MARGIN, SCREEN_H // 2 + 10, GRAY, WHITE, font=FONT_MONT_14)
    screen.push()


def main():
    screen = M5Screen()
    screen.set_screen_bg_color(WHITE)

    show_message(screen, "M5Paperboy", "Connecting to WiFi...")

    if not connect_wifi():
        show_message(screen, "WiFi failed", "Check SSID and password in firmware.")
        return

    show_message(screen, "M5Paperboy", "Fetching today's news...")

    try:
        data = fetch_articles()
    except Exception as e:
        show_message(screen, "Fetch failed", str(e))
        return

    articles = data.get("articles", [])
    if not articles:
        show_message(screen, "No articles found", "Try again later.")
        return

    index = 0
    render_article(screen, articles[index], index + 1, len(articles))

    while True:
        if btnA.wasPressed():
            index = max(0, index - 1)
            render_article(screen, articles[index], index + 1, len(articles))

        if btnB.wasPressed():
            index = min(len(articles) - 1, index + 1)
            render_article(screen, articles[index], index + 1, len(articles))

        if btnC.wasPressed():
            show_message(screen, "Refreshing...", "Fetching latest articles.")
            try:
                data = fetch_articles()
                articles = data.get("articles", [])
                index = 0
                render_article(screen, articles[index], index + 1, len(articles))
            except Exception as e:
                show_message(screen, "Refresh failed", str(e))

        time.sleep(0.1)


main()
