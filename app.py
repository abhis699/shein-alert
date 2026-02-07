import requests
import time
import json
import os
import threading
from flask import Flask

# ==========================
# CONFIG
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

API_URL = "https://www.sheinindia.in/api/category/sverse-5939-37961?fields=SITE&currentPage=1&pageSize=45&format=json&query=%3Arelevance&gridColumns=5&advfilter=true&platform=Desktop&showAdsOnNextPage=false&is_ads_enable_plp=true&displayRatings=true&segmentIds=&&store=shein"

CHECK_INTERVAL = 15  # ⚡ Fast mode
DATA_FILE = "products.json"

# ==========================
# FAST SESSION (Speed Boost)
# ==========================

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

# ==========================
# FLASK (Railway keep alive)
# ==========================

app = Flask(__name__)

@app.route("/")
def home():
    return "SHEINVERSE BOT RUNNING ⚡"

def run_web():
    app.run(host="0.0.0.0", port=8000)

threading.Thread(target=run_web, daemon=True).start()

# ==========================
# STORAGE
# ==========================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

stored_products = load_data()

# ==========================
# TELEGRAM
# ==========================

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    session.post(url, data=payload, timeout=10)

def send_photo(caption, image_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    session.post(url, data=payload, timeout=15)

# ==========================
# VOUCHER LOGIC
# ==========================

def voucher_text(price_value):
    if price_value < 500:
        return "🎟 Use ₹500 Voucher"
    elif price_value < 1000:
        return "🎟 Use ₹1000 Voucher"
    else:
        return "🎟 Eligible for ₹1000 Voucher"

# ==========================
# PRICE FIX (Accurate)
# ==========================

def get_correct_price(product):
    offer = product.get("offerPrice", {})
    regular = product.get("price", {})

    offer_value = offer.get("value")
    regular_value = regular.get("value")

    if offer_value and regular_value:
        if offer_value < regular_value:
            return offer_value, offer.get("displayformattedValue")
        else:
            return regular_value, regular.get("displayformattedValue")
    elif offer_value:
        return offer_value, offer.get("displayformattedValue")
    elif regular_value:
        return regular_value, regular.get("displayformattedValue")
    else:
        return 0, "₹0"

# ==========================
# SIZE EXTRACTION
# ==========================

def extract_sizes(product):
    sizes = set()
    variants = product.get("skuList") or product.get("variantOptions") or []

    for v in variants:
        size = v.get("size") or v.get("sizeName") or v.get("value")
        in_stock = v.get("inStock")

        if size:
            if in_stock is None:
                sizes.add(size)
            elif in_stock:
                sizes.add(size)

    return sizes

# ==========================
# MAIN MONITOR LOOP
# ==========================

print("🚀 SHEINVERSE BOT STARTED (LIGHTNING MODE)")

while True:
    try:
        start_time = time.time()

        response = session.get(API_URL, headers=HEADERS, timeout=15)
        data = response.json()

        products = data.get("products", [])

        for p in products:

            code = str(p.get("code"))
            name = p.get("name")

            price_value, display_price = get_correct_price(p)

            image = None
            imgs = p.get("images", [])
            if imgs:
                image = imgs[0].get("url")

            link = "https://www.sheinindia.in" + p.get("url", "")

            current_sizes = extract_sizes(p)

            previous_data = stored_products.get(code)

            # NEW PRODUCT
            if code not in stored_products:

                stored_products[code] = {
                    "sizes": list(current_sizes)
                }
                save_data(stored_products)

                caption = f"""🆕 <b>NEW PRODUCT</b>

🛍 <b>{name}</b>
💰 {display_price}
📦 Sizes: {", ".join(current_sizes) if current_sizes else "Available"}

{voucher_text(price_value)}

🔗 {link}
"""

                if image:
                    send_photo(caption, image)
                else:
                    send_message(caption)

            # EXISTING PRODUCT
            else:
                old_sizes = set(previous_data.get("sizes", []))

                sold_out = old_sizes - current_sizes
                restocked = current_sizes - old_sizes

                if sold_out:
                    send_message(f"""⚠️ <b>SIZE SOLD OUT</b>

🛍 <b>{name}</b>
❌ Sold Out: {", ".join(sold_out)}

🔗 {link}
""")

                if restocked:
                    send_message(f"""🔁 <b>SIZE RESTOCKED</b>

🛍 <b>{name}</b>
✅ Restocked: {", ".join(restocked)}

🔗 {link}
""")

                stored_products[code]["sizes"] = list(current_sizes)
                save_data(stored_products)

        # Smart sleep adjustment
        elapsed = time.time() - start_time
        sleep_time = max(0, CHECK_INTERVAL - elapsed)
        time.sleep(sleep_time)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
