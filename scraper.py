import os
import re
import requests
import random
import logging
from decimal import Decimal, InvalidOperation
from bs4 import BeautifulSoup
from supabase import create_client

# --- CONFIG / AUTH SETUP ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

TARGET_URL = "https://www.foreclosure.com/listing/search?q=San+Bernardino+County%2C+CA"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/04.1'
}

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("harvest")

# --- Helpers ---
def parse_amount(raw_price: str):
    """
    Convert strings like "$123,456" to Decimal('123456.00').
    Returns Decimal or None.
    """
    if not raw_price:
        return None
    cleaned = re.sub(r'[^\d.]', '', raw_price)
    if cleaned == '':
        return None
    try:
        # Keep cents if present; Decimal is preferred for money
        return Decimal(cleaned)
    except InvalidOperation:
        logger.warning("Failed to parse price: %s", raw_price)
        return None

def validate_env():
    if not URL or not KEY:
        logger.error("SUPABASE_URL or SUPABASE_KEY missing in environment")
        return False
    return True

def smoke_db():
    """
    Minimal DB check: attempt a simple RPC or select via PostgREST.
    This uses a light call to ensure credentials are valid.
    """
    try:
        # A lightweight call - list tables isn't available directly; use a simple select
        res = supabase.table('listings').select('id').limit(1).execute()
        # supabase client returns a dict-like response; check for error
        if res.get('error'):
            logger.error("DB smoke test error: %s", res['error'])
            return False
        logger.info("DB smoke test OK")
        return True
    except Exception as e:
        logger.exception("DB smoke test exception: %s", e)
        return False

# --- Scraper ---
def harvest_real_data():
    logger.info("📡 Harvesting San Bernardino County NOD/TS leads...")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            logger.error("Site blocked or returned non-200 (Status: %s)", response.status_code)
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all('div', class_='listing-item')

        if not listings:
            logger.warning("No listings found. Check if site structure changed.")
            return

        for idx, item in enumerate(listings, start=1):
            try:
                addr_node = item.find('div', class_='address')
                price_node = item.find('div', class_='price')
                type_node = item.find('span', class_='type')

                raw_address = addr_node.get_text(strip=True) if addr_node else None
                raw_price = price_node.get_text(strip=True) if price_node else None
                raw_type = type_node.get_text(strip=True).upper() if type_node else ''

                if not raw_address:
                    logger.warning("Skipping listing #%s: missing address", idx)
                    continue

                # Categorize stage
                if "DEFAULT" in raw_type or "NOD" in raw_type:
                    stage = "NOTICE OF DEFAULT"
                elif "SALE" in raw_type or "AUCTION" in raw_type:
                    stage = "TRUSTEE SALE"
                else:
                    stage = "PRE-FORECLOSURE"

                # Random coords in SB County (placeholder) - keep as floats
                lat = 34.10 + random.uniform(-0.15, 0.15)
                lng = -117.28 + random.uniform(-0.15, 0.15)

                amount = parse_amount(raw_price)

                lead = {
                    "address": raw_address,
                    "city": "San Bernardino County",
                    # supabase client will serialize Decimal as string; Postgres will accept numeric strings
                    "amount": amount if amount is None else str(amount),
                    "stage": stage,
                    "lat": float(lat),
                    "lng": float(lng)
                }

                # Upsert and check response
                try:
                    res = supabase.table('listings').upsert(lead, on_conflict='address').execute()
                    if isinstance(res, dict) and res.get('error'):
                        logger.error("Upsert error for %s: %s", raw_address, res['error'])
                    else:
                        logger.info("✅ Saved %s: %s", stage, raw_address)
                except Exception as upsert_exc:
                    logger.exception("Exception during upsert for %s: %s", raw_address, upsert_exc)

            except Exception as e:
                logger.exception("⚠️ Skipped listing #%s due to exception: %s", idx, e)
                continue

    except Exception as e:
        logger.exception("❌ Critical Error during harvesting: %s", e)

if __name__ == "__main__":
    if not validate_env():
        raise SystemExit("Missing environment variables")
    if not smoke_db():
        raise SystemExit("DB smoke test failed")
    harvest_real_data()