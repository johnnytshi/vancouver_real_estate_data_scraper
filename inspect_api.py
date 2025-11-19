import os
import json
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("ZEALTY_USERNAME")
PASSWORD = os.getenv("ZEALTY_PASSWORD")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to login page...")
        page.goto("https://www.zealty.ca/sign-in")

        print("Filling credentials...")
        page.fill("#email", USERNAME)
        page.fill("#password", PASSWORD)
        
        # Capture specific API requests
        def handle_response(response):
            if "svcFetchDB.php" in response.url or "svcGetInfoDB.php" in response.url:
                print(f"\n[API MATCH] URL: {response.url}")
                print(f"   Method: {response.request.method}")
                print(f"   Post Data: {response.request.post_data}")
                try:
                    body = response.json()
                    print(f"   Response Keys: {list(body.keys())[:5]}")
                    # Print a sample of the data
                    print(f"   Sample Data: {str(body)[:500]}")
                except:
                    print("   Response is not JSON or failed to parse.")

        page.on("response", handle_response)

        # Capture WebSockets
        def handle_ws(ws):
            print(f"[WS] Opened: {ws.url}")
            ws.on("framesent", lambda f: print(f"[WS] Sent: {f.payload[:100]}"))
            ws.on("framereceived", lambda f: print(f"[WS] Recv: {f.payload[:100]}"))
        
        page.on("websocket", handle_ws)

        print("Clicking sign in...")
        page.click("button:has-text('Sign In')")
        
        print("Waiting for login to complete...")
        time.sleep(5)

        print("Checking current URL...")
        if "map.html" not in page.url:
            print(f"Current URL is {page.url}. Forcing navigation to map...")
            page.goto("https://www.zealty.ca/map.html")
        
        print("Waiting for map data...")
        try:
            page.wait_for_load_state("networkidle")
            time.sleep(10)
            
            # Interact with map to trigger loading
            print("Interacting with map...")
            page.mouse.move(500, 500)
            page.mouse.down()
            page.mouse.move(600, 600)
            page.mouse.up()
            time.sleep(5)
            
            print("Taking map screenshot...")
            page.screenshot(path="map_page.png")
            
        except Exception as e:
            print(f"Error waiting for map: {e}")

        browser.close()

if __name__ == "__main__":
    run()
