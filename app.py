import requests
import time
import json
import os
import threading
import random
from flask import Flask

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961?fields=SITE&currentPage=1&pageSize=45&format=json&query=%3Arelevance&gridColumns=5&advfilter=true&platform=Desktop&showAdsOnNextPage=false&is_ads_enable_plp=true&displayRatings=true&segmentIds=&&store=shein"

NORMAL_MIN = 15
NORMAL_MAX = 25
FLASH_INTERVAL = 5
FLASH_DURATION = 120  # seconds

DATA_FILE = "products.json"

# ================= STEALTH HEADERS =================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Windows NT 10.0; WOW64)",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Connection": "keep-alive",
        "Referer": "https://www.sheinindia.in/",
        "Cache-Control": "no-cache",
    }

session = requests.Session()

# ================= FLASK KEEP ALIVE =================

app = Flask(__name__)

@app.route("/")
def home():
    return "SHEINVERSE BOT RUNNING ⚡"

def run_web():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_web, daemon=True).start()

# ================= STORAGE =================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

stored_products = load_data()

# ================= TELEGRAM =================

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        session.post(url, data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

def send_photo(caption, image_url):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        session.post(url, data={
            "chat_id": CHANNEL_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }, timeout=15)
    except:
        pass

# ================= HELPERS =================

def get_price(product):
    offer = product.get("offerPrice", {})
    regular = product.get("price", {})
    if offer.get("displayformattedValue"):
        return offer["displayformattedValue"]
    if regular.get("displayformattedValue"):
        return regular["displayformattedValue"]
    return "Price N/A"

def extract_sizes(product):
    sizes = set()
    variants = product.get("skuList") or []
    for v in variants:
        size = v.get("sizeName") or v.get("size")
        if v.get("inStock"):
            sizes.add(size)
    return sizes

# ================= SAFE FETCH =================

def fetch_products():
    for attempt in range(3):
        try:
            response = session.get(API_URL, headers=get_headers(), timeout=15)

            if response.status_code == 429:
                print("⚠ Rate limited, backing off...")
                time.sleep(10)
                continue

            if response.status_code != 200:
                return None

            if "application/json" not in response.headers.get("Content-Type", ""):
                return None

            return response.json()

        except:
            time.sleep(3)
    return None

# ================= MAIN LOOP =================

print("🚀 ENTERPRISE MODE ACTIVATED")

flash_mode_until = 0

while True:
    try:
        now = time.time()
        in_flash = now < flash_mode_until

        data = fetch_products()
        if not data:
            time.sleep(5)
            continue

        products = data.get("products", [])

        activity_detected = False

        for p in products:

            code = str(p.get("code"))
            name = p.get("name")
            price = get_price(p)
            link = "https://www.sheinindia.in" + p.get("url", "")

            image = None
            imgs = p.get("images", [])
            if imgs:
                image = imgs[0].get("url")

            current_sizes = extract_sizes(p)
            old_data = stored_products.get(code)

            # NEW PRODUCT
            if code not in stored_products:

                stored_products[code] = {"sizes": list(current_sizes)}
                save_data(stored_products)

                caption = f"""🆕 <b>NEW PRODUCT</b>

🛍 <b>{name}</b>
💰 {price}
📦 Sizes: {", ".join(current_sizes) if current_sizes else "Available"}

🔗 {link}
"""

                if image:
                    send_photo(caption, image)
                else:
                    send_message(caption)

                activity_detected = True

            else:
                old_sizes = set(old_data.get("sizes", []))
                sold_out = old_sizes - current_sizes
                restocked = current_sizes - old_sizes

                if restocked:
                    send_message(f"""🔁 <b>SIZE RESTOCKED</b>

🛍 <b>{name}</b>
💰 {price}
✅ Restocked: {", ".join(restocked)}

🔗 {link}
""")
                    activity_detected = True

                if sold_out:
                    send_message(f"""⚠ <b>SIZE SOLD OUT</b>

🛍 <b>{name}</b>
❌ Sold Out: {", ".join(sold_out)}

🔗 {link}
""")

                stored_products[code]["sizes"] = list(current_sizes)
                save_data(stored_products)

        # 🚀 ACTIVATE FLASH MODE
        if activity_detected:
            flash_mode_until = time.time() + FLASH_DURATION
            print("⚡ FLASH MODE ACTIVATED")

        # Sleep logic
        if in_flash:
            sleep_time = FLASH_INTERVAL + random.uniform(0.5, 1.5)
        else:
            sleep_time = random.randint(NORMAL_MIN, NORMAL_MAX)

        time.sleep(sleep_time)

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)
