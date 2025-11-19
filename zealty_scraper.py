import os
import json
import time
import csv
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from urllib.parse import parse_qs, urlparse

load_dotenv()

USERNAME = os.getenv("ZEALTY_USERNAME")
PASSWORD = os.getenv("ZEALTY_PASSWORD")

def run():
    captured_token = None
    captured_sql = None
    all_listings = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to login page...")
        page.goto("https://www.zealty.ca/sign-in")

        print("Filling credentials...")
        page.fill("#email", USERNAME)
        page.fill("#password", PASSWORD)
        
        # Capture the API request to get the session token
        def handle_response(response):
            nonlocal captured_token, captured_sql, all_listings
            
            if "svcFetchDB.php" in response.url:
                print(f"[CAPTURED] svcFetchDB.php request")
                
                # Extract token from URL
                parsed = urlparse(response.url)
                params = parse_qs(parsed.query)
                if 's' in params:
                    captured_token = params['s'][0]
                    print(f"   Token: {captured_token}")
                
                # Get the SQL query from POST data
                post_data = response.request.post_data
                if post_data:
                    post_params = parse_qs(post_data)
                    if 'sql' in post_params:
                        captured_sql = post_params['sql'][0]
                        print(f"   SQL: {captured_sql[:100]}...")
                
                # Parse the response
                try:
                    body = response.json()
                    if 'rows' in body and body['rows']:
                        print(f"   Found {len(body['rows'])} listings in this batch")
                        all_listings.extend(body['rows'])
                except:
                    pass

        page.on("response", handle_response)

        print("Clicking sign in...")
        page.click("button:has-text('Sign In')")
        
        print("Waiting for login to complete...")
        time.sleep(5)

        print("Navigating to map...")
        page.goto("https://www.zealty.ca/map.html")
        
        print("Waiting for map data to load...")
        page.wait_for_load_state("networkidle")
        time.sleep(10)
        
        # Interact with map to trigger more API calls
        print("Interacting with map to load more listings...")
        page.mouse.move(500, 500)
        page.mouse.down()
        page.mouse.move(600, 600)
        page.mouse.up()
        time.sleep(5)

        browser.close()

    print(f"\nTotal listings captured: {len(all_listings)}")
    
    if all_listings:
        # Save to CSV
        print("Saving to listings.csv...")
        
        # The columns from the API response
        columns = ['MLS_Number', 'Latitude', 'Longitude', 'Date', 'Unknown1', 'Address', 
                   'Neighborhood', 'Price', 'Description', 'Property_Type', 'Stories', 
                   'Unknown2', 'Bedrooms', 'Bathrooms', 'Unknown3', 'Unknown4', 'Unknown5']
        
        with open('listings.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(all_listings)
        
        print(f"Saved {len(all_listings)} listings to listings.csv")
        
        # Print a sample
        print("\nSample listing:")
        if len(all_listings) > 0:
            sample = all_listings[0]
            for i, col in enumerate(columns):
                if i < len(sample):
                    value = str(sample[i])[:100]
                    print(f"  {col}: {value}")
    else:
        print("No listings were captured. The token might be required or the API structure changed.")
        if captured_token:
            print(f"Captured token: {captured_token}")
            print("You can use this token to make manual API requests if needed.")

if __name__ == "__main__":
    run()
