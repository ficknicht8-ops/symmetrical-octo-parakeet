import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# --- AUTH SETUP ---
# These must be in your GitHub Secrets
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

# --- TARGET DATA SOURCE ---
# We are targeting the San Bernardino County search on Foreclosure.com
TARGET_URL = "https://www.foreclosure.com/listing/search?q=San+Bernardino+County%2C+CA"

# Headers make the cloud harvester look like a real person browsing on a phone
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/04.1'
}

def harvest_real_data():
    print(f"📡 Harvesting San Bernardino County NOD/TS leads...")
    
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            print(f"❌ Site blocked the cloud harvester (Status: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This finds the listing blocks on the page
        listings = soup.find_all('div', class_='listing-item')
        
        if not listings:
            print("⚠️ No listings found. The site structure might have changed.")
            return

        for item in listings:
            try:
                # Extracting raw data from the site
                raw_address = item.find('div', class_='address').get_text(strip=True)
                raw_price = item.find('div', class_='price').get_text(strip=True)
                raw_type = item.find('span', class_='type').get_text(strip=True).upper()

                # --- FILTERING LOGIC ---
                # We categorize based on keywords found on the site
                if "DEFAULT" in raw_type or "NOD" in raw_type:
                    stage = "NOTICE OF DEFAULT"
                elif "SALE" in raw_type or "AUCTION" in raw_type:
                    stage = "TRUSTEE SALE"
                else:
                    stage = "PRE-FORECLOSURE"

                # --- GEOCODING (Visualization) ---
                # Since we don't have a Google Maps API key, we center them 
                # in the SB County area with slight variations so pins don't stack.
                import random
                lat = 34.10 + random.uniform(-0.15, 0.15)
                lng = -117.28 + random.uniform(-0.15, 0.15)

                lead = {
                    "address": raw_address,
                    "city": "San Bernardino County",
                    "amount": raw_price,
                    "stage": stage,
                    "lat": lat,
                    "lng": lng
                }

                # Push to Supabase - 'on_conflict' prevents duplicate addresses
                supabase.table('listings').upsert(lead, on_conflict='address').execute()
                print(f"✅ Saved {stage}: {raw_address}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    harvest_real_data()
