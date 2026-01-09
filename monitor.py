import os
import time
import json
import re
import csv
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# ==================================================
# ENVIRONMENT VARIABLES (REQUIRED)
# ==================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID. "
        "Set them in your .env file."
    )

# ==================================================
# USER CONFIG
# ==================================================

SEARCH_URLS = [
    "https://www.facebook.com/marketplace/search/?query=iphone",
]

MAX_PRICE = 200
CHECK_INTERVAL = 300              # seconds (5 min)
HEARTBEAT_EVERY = 1               # heartbeat every N scans

DEFAULT_RESALE = 250

PROFIT_GREEN = 80
PROFIT_YELLOW = 30

SEEN_FILE = "seen.json"
CSV_FILE = "deals.csv"

BLOCK_KEYWORDS = [
    "icloud",
    "activation lock",
    "google locked",
    "mdm",
    "financed",
    "stolen",
    "scam",
    "parts only",
]

REPAIR_COSTS = {
    "cracked": 35,
    "screen": 35,
    "lcd": 35,
    "battery": 20,
    "back glass": 40,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
    "Accept-Language": "en-US,en;q=0.9",
}

# ==================================================
# HELPERS
# ==================================================

def utc_now():
    return datetime.now(timezone.utc)

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f)

def ensure_csv():
    if os.path.exists(CSV_FILE):
        return
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp_utc",
            "listing_id",
            "price",
            "repair_est",
            "resale_est",
            "profit_est",
            "grade",
            "model_guess",
            "url"
        ])

def log_csv(row):
    ensure_csv()
    with open(CSV_FILE, "a", newline="") as f:
        csv.writer(f).writerow(row)

def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception as e:
        print(f"⚠ Telegram error: {e}", flush=True)

def extract_price(text):
    m = re.search(r"\$(\d{1,4})", text.replace(",", ""))
    return int(m.group(1)) if m else None

def estimate_repair(text):
    cost = 0
    for k, v in REPAIR_COSTS.items():
        if k in text:
            cost += v
    return cost

def model_guess(text):
    m = re.search(r"(iphone\s+[a-z0-9\s]+)", text)
    return m.group(1).title() if m else "iPhone"

def grade_profit(p):
    if p >= PROFIT_GREEN:
        return "🟢 GOOD"
    if p >= PROFIT_YELLOW:
        return "🟡 OK"
    return "🔴 SKIP"

# ==================================================
# CORE SCRAPER
# ==================================================

def scan_marketplace():
    seen = load_seen()
    new_hits = 0

    print("🔍 Scanning Facebook Marketplace…", flush=True)

    for search_url in SEARCH_URLS:
        try:
            r = requests.get(search_url, headers=HEADERS, timeout=20)
        except Exception as e:
            print(f"⚠ Request failed: {e}", flush=True)
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/marketplace/item/" not in href:
                continue

            url = "https://facebook.com" + href.split("?")[0]
            listing_id = url.split("/")[-1]

            if listing_id in seen:
                continue

            text = a.get_text(" ", strip=True).lower()

            if "iphone" not in text:
                continue

            if any(bad in text for bad in BLOCK_KEYWORDS):
                continue

            price = extract_price(text)
            if price is None or price > MAX_PRICE:
                continue

            seen[listing_id] = int(time.time())
            new_hits += 1

            repair = estimate_repair(text)
            resale = DEFAULT_RESALE
            profit = resale - price - repair
            grade = grade_profit(profit)
            model = model_guess(text)

            log_csv([
                utc_now().isoformat(timespec="seconds"),
                listing_id,
                price,
                repair,
                resale,
                profit,
                grade,
                model,
                url,
            ])

            message = (
                "🚨 JUST LISTED\n\n"
                "📱 iPHONE FLIP ALERT\n\n"
                f"{grade}\n"
                f"Model: {model}\n"
                f"Buy: ${price}\n"
                f"Repair est: ${repair}\n"
                f"Resale est: ~${resale}\n"
                f"💰 Est. Profit: ${profit}\n\n"
                f"{url}"
            )

            print(f"📤 Alert sent: {model} @ ${price}", flush=True)
            send_telegram(message)

    save_seen(seen)
    return new_hits

# ==================================================
# MAIN LOOP + HEARTBEAT
# ==================================================

def main():
    print("🚀 iPhone Marketplace Flipper Bot STARTED", flush=True)
    scan_count = 0

    while True:
        scan_count += 1
        hits = scan_marketplace()

        if scan_count % HEARTBEAT_EVERY == 0:
            heartbeat = (
                "🫀 HEARTBEAT\n\n"
                f"Scans run: {scan_count}\n"
                f"New hits last scan: {hits}\n"
                f"UTC time: {utc_now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram(heartbeat)
            print("🫀 Heartbeat sent", flush=True)

        print(f"⏳ Sleeping {CHECK_INTERVAL}s\n", flush=True)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
