import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# --- CONFIG ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

# The target: Public foreclosure listings for SB County
# We use headers to look like a real browser to avoid being blocked
SEARCH_URL = "https://www.foreclosure.com/listing/search?q=San+Bernardino+County%2C+CA"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def run_cloud_harvest():
    print("📡 Cloud Harvester starting: Searching for NOD/Trustee Sales...")
    
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the listing containers (this selector depends on the target site)
        listings = soup.find_all('div', class_='listing-item') 
        
        if not listings:
            print("⚠️ No listings found in this pass. Site structure may have changed.")
            return

        for item in listings:
            try:
                # Extracting raw text
                address = item.find('div', class_='address').text.strip()
                price = item.find('div', class_='price').text.strip()
                type_tag = item.find('span', class_='type').text.upper()

                # Logic to identify the specific stage you want
                if "DEFAULT" in type_tag:
                    stage = "NOD"
                elif "SALE" in type_tag or "AUCTION" in type_tag:
                    stage = "TRUSTEE SALE"
                else:
                    stage = "PRE-FORECLOSURE"

                # Data package for Supabase
                # Note: For a live map, you'd usually pass address through a Geocoder
                # Here we use city-center offsets for SB County for visualization
                lead = {
                    "address": address,
                    "city": "San Bernardino County",
                    "amount": price,
                    "stage": stage,
                    "lat": 34.10 + (os.urandom(1)[0]/2550), # Slight variance
                    "lng": -117.28 + (os.urandom(1)[0]/2550)
                }

                # Push to Supabase
                supabase.table('listings').upsert(lead, on_conflict='address').execute()
                print(f"✅ Harvested {stage}: {address}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"❌ Harvester Error: {e}")

if __name__ == "__main__":
    run_cloud_harvest()
