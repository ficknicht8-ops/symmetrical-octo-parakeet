import random
import time
import os
from supabase import create_client

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

cities = [
    {"name": "Apple Valley", "lat": 34.5008, "lng": -117.1859},
    {"name": "Ontario", "lat": 34.0633, "lng": -117.6509},
    {"name": "San Bernardino", "lat": 34.1083, "lng": -117.2898},
    {"name": "Victorville", "lat": 34.5361, "lng": -117.2911},
    {"name": "Hesperia", "lat": 34.4264, "lng": -117.3009}
]

def harvest():
    city = random.choice(cities)
    data = {
        "address": f"{random.randint(100, 9999)} Cloud Lane",
        "city": city["name"],
        "amount": f"${random.randint(5000, 450000):,}",
        "lat": city["lat"] + random.uniform(-0.05, 0.05),
        "lng": city["lng"] + random.uniform(-0.05, 0.05),
        "stage": "NOD"
    }
    try:
        supabase.table("listings").insert(data).execute()
        print(f"🚀 Harvested: {data['address']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    for _ in range(5):
        harvest()
        time.sleep(1)

