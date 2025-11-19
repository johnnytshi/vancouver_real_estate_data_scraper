import os
import json
import time
import csv
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from urllib.parse import parse_qs

load_dotenv()

USERNAME = os.getenv("ZEALTY_USERNAME")
PASSWORD = os.getenv("ZEALTY_PASSWORD")

# Validate credentials at startup
if not USERNAME or not PASSWORD:
    print("ERROR: Missing credentials!")
    print("Please create a .env file with:")
    print("  ZEALTY_USERNAME=your.email@example.com")
    print("  ZEALTY_PASSWORD=your_password_here")
    print("\nYou can copy .env.example to .env and fill in your credentials.")
    exit(1)

def save_to_csv(listings, filename, run_dir):
    """Save listings to a CSV file in the run directory"""
    if not listings:
        print(f"No listings to save for {filename}")
        return
    
    # The columns from the API response
    columns = ['MLS_Number', 'Latitude', 'Longitude', 'Date', 'Unknown1', 'Address', 
               'Neighborhood', 'Price', 'Description', 'Property_Type', 'Stories', 
               'Unknown2', 'Bedrooms', 'Bathrooms', 'Unknown3', 'Unknown4', 'Unknown5']
    
    filepath = os.path.join(run_dir, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(listings)
    
    print(f"Saved {len(listings)} listings to {filepath}")
    
    # Print a sample
    if len(listings) > 0:
        print(f"\nSample listing from {filename}:")
        sample = listings[0]
        for i, col in enumerate(columns):
            if i < len(sample):
                value = str(sample[i])[:100]
                print(f"  {col}: {value}")

def run():
    import hashlib
    
    # Create run directory with timestamp
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join("data", f"run-{run_timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    print(f"Created run directory: {run_dir}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        print("Navigating to login page...")
        page.goto("https://www.zealty.ca/sign-in")

        print("Filling credentials...")
        page.fill("#email", USERNAME)
        page.fill("#password", PASSWORD)
        
        print("Clicking sign in...")
        page.click("button:has-text('Sign In')")
        
        print("Waiting for login to complete...")
        time.sleep(5)

        print("Extracting session data...")
        # Just load the map page to establish session
        page.goto("https://www.zealty.ca/map.html")
        
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        # Try to compute token by inspecting page JavaScript or just use MD5 of SQL
        def compute_token(sql_text):
            # The token might be MD5 hash of SQL + some salt
            # Let's try MD5 of the SQL itself
            return hashlib.md5(sql_text.encode()).hexdigest()

        # Common headers for direct POSTs
        headers = {
            "accept": "*/*",
            "accept-language": "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "dnt": "1",
            "origin": "https://www.zealty.ca",
            "referer": "https://www.zealty.ca/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }

        # Helper to perform the POST
        def fetch_rows(sql_query, sold_flag):
            print(f"  Posting query for '{sold_flag}'...")
            token_s = compute_token(sql_query)
            resp = context.request.post(
                "https://bcrealestatemap.ca/svcFetchDB.php",
                headers=headers,
                form={
                    "sql": sql_query,
                    "sold": sold_flag,
                    "from": "dmap",
                    "s": token_s,
                },
                timeout=60_000,
            )
            print(f"  Response status: {resp.status}")
            if not resp.ok:
                print(f"  Request failed: {resp.status} {resp.status_text()}")
                return []
            try:
                data = resp.json()
            except Exception as e:
                print(f"  Non-JSON response: {e}")
                return []
            rows = data.get("rows") or []
            print(f"  Received {len(rows)} rows")
            return rows

        # Compute date ranges
        today = datetime.utcnow().date()
        last_12m_start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")
        last_30d_start = (today - timedelta(days=30)).strftime("%Y-%m-%d")

        # Metro Vancouver bounds - break into grid to get more than 500 results
        # Overall bounds: lat 49.0 to 49.5, lon -123.3 to -122.5
        def generate_grid_boxes(lat_min, lat_max, lon_min, lon_max, divisions=3):
            """Split area into smaller boxes to bypass 500 row limit"""
            lat_step = (lat_max - lat_min) / divisions
            lon_step = (lon_max - lon_min) / divisions
            boxes = []
            for i in range(divisions):
                for j in range(divisions):
                    box_lat_min = lat_min + (i * lat_step)
                    box_lat_max = lat_min + ((i + 1) * lat_step)
                    box_lon_min = lon_min + (j * lon_step)
                    box_lon_max = lon_min + ((j + 1) * lon_step)
                    boxes.append((box_lat_min, box_lat_max, box_lon_min, box_lon_max))
            return boxes

        # Metro Vancouver area grid
        metro_boxes = generate_grid_boxes(49.0, 49.5, -123.3, -122.5, divisions=3)
        
        # Property type filter SQL fragment
        property_filter = "((propertyClassCode = 0) OR (propertyClassCode = 1 AND type IN('Apartment/Condo','Apartment','Condo Apartment')) OR (propertyClassCode = 1 AND type NOT IN('Apartment/Condo','Apartment','Condo Apartment')) OR (propertyClassCode = 3) OR (propertyClassCode = 4) OR (propertyClassCode = 2))"

        # ===== FOR SALE - TODAY =====
        print("\n" + "="*60)
        print("COLLECTING FOR SALE LISTINGS (TODAY) [direct API]")
        print("="*60)
        
        for_sale_listings = []
        for idx, (lat_min, lat_max, lon_min, lon_max) in enumerate(metro_boxes, 1):
            print(f"  Fetching grid box {idx}/{len(metro_boxes)}...")
            sql = f"SELECT * FROM *** WHERE (latitude BETWEEN {lat_min} AND {lat_max}) AND (longitude BETWEEN {lon_min} AND {lon_max}) AND {property_filter} ORDER BY GREATEST(listingDate, listingPricePrevDate) DESC LIMIT 500"
            rows = fetch_rows(sql, "active")
            for_sale_listings.extend(rows)
        
        # Deduplicate by MLS_Number (first column)
        seen = set()
        unique_for_sale = []
        for row in for_sale_listings:
            mls = row[0] if row else None
            if mls and mls not in seen:
                seen.add(mls)
                unique_for_sale.append(row)
        
        print(f"Total For Sale listings captured: {len(unique_for_sale)} (deduped from {len(for_sale_listings)})")
        save_to_csv(unique_for_sale, "for_sale_today.csv", run_dir)

        # ===== SOLDS - LAST 12 MONTHS =====
        print("\n" + "="*60)
        print("COLLECTING SOLD LISTINGS (LAST 12 MONTHS) [direct API]")
        print("="*60)
        
        solds_listings = []
        for idx, (lat_min, lat_max, lon_min, lon_max) in enumerate(metro_boxes, 1):
            print(f"  Fetching grid box {idx}/{len(metro_boxes)}...")
            sql = f"SELECT * FROM *** WHERE (latitude BETWEEN {lat_min} AND {lat_max}) AND (longitude BETWEEN {lon_min} AND {lon_max}) AND {property_filter} AND (entryDate BETWEEN '{last_12m_start}' AND '{today_str}') ORDER BY entryDate DESC LIMIT 500"
            rows = fetch_rows(sql, "sold")
            solds_listings.extend(rows)
        
        seen = set()
        unique_solds = []
        for row in solds_listings:
            mls = row[0] if row else None
            if mls and mls not in seen:
                seen.add(mls)
                unique_solds.append(row)
        
        print(f"Total Sold listings captured: {len(unique_solds)} (deduped from {len(solds_listings)})")
        save_to_csv(unique_solds, "solds_last_12_months.csv", run_dir)

        # ===== EXPIRED - LAST 30 DAYS =====
        print("\n" + "="*60)
        print("COLLECTING EXPIRED LISTINGS (LAST 30 DAYS) [direct API]")
        print("="*60)
        
        expired_listings = []
        for idx, (lat_min, lat_max, lon_min, lon_max) in enumerate(metro_boxes, 1):
            print(f"  Fetching grid box {idx}/{len(metro_boxes)}...")
            sql = f"SELECT * FROM *** WHERE (latitude BETWEEN {lat_min} AND {lat_max}) AND (longitude BETWEEN {lon_min} AND {lon_max}) AND {property_filter} AND (entryDate BETWEEN '{last_30d_start}' AND '{today_str}') ORDER BY entryDate DESC LIMIT 500"
            rows = fetch_rows(sql, "expired")
            expired_listings.extend(rows)
        
        seen = set()
        unique_expired = []
        for row in expired_listings:
            mls = row[0] if row else None
            if mls and mls not in seen:
                seen.add(mls)
                unique_expired.append(row)
        
        print(f"Total Expired listings captured: {len(unique_expired)} (deduped from {len(expired_listings)})")
        save_to_csv(unique_expired, "expired_last_30_days.csv", run_dir)
        
        browser.close()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"For Sale (Today): {len(unique_for_sale) if 'unique_for_sale' in locals() else 0} listings")
    print(f"Solds (Last 12 Months): {len(unique_solds) if 'unique_solds' in locals() else 0} listings")
    print(f"Expired (Last 30 Days): {len(unique_expired) if 'unique_expired' in locals() else 0} listings")

if __name__ == "__main__":
    run()
