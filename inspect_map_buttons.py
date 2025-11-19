import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("ZEALTY_USERNAME")
PASSWORD = os.getenv("ZEALTY_PASSWORD")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        print("Navigating to login page...")
        page.goto("https://www.zealty.ca/sign-in")

        print("Filling credentials...")
        page.fill("#email", USERNAME)
        page.fill("#password", PASSWORD)
        page.click("button:has-text('Sign In')")
        
        print("Waiting for login...")
        try:
            # Wait for either map.html or just a successful login redirect
            page.wait_for_url("**/map.html", timeout=15000)
            print("Redirected to map page automatically.")
        except:
            print(f"Timed out waiting for redirect. Current URL: {page.url}")
            print("Manually navigating to map.html...")
            page.goto("https://www.zealty.ca/map.html")
            page.wait_for_load_state("networkidle")
        
        print(f"Current URL: {page.url}")
        print("On map page. Taking screenshot...")
        time.sleep(5) # Wait for map to load
        page.screenshot(path="map_page_top.png")
        
        # Try to find buttons with text "For Sale", "Solds", "Expired"
        # Also look for specific classes if we can guess them, but text is safer for now
        for text in ["For Sale", "Solds", "Expired"]:
            try:
                # Try different selectors
                locators = [
                    page.get_by_text(text, exact=False),
                    page.locator(f"button:has-text('{text}')"),
                    page.locator(f"div:has-text('{text}')")
                ]
                
                found = False
                for loc in locators:
                    if loc.count() > 0 and loc.first.is_visible():
                        print(f"Found '{text}' element")
                        box = loc.first.bounding_box()
                        print(f"  at {box}")
                        found = True
                        break
                if not found:
                    print(f"Could not find '{text}'")
            except Exception as e:
                print(f"Error looking for '{text}': {e}")

        browser.close()

if __name__ == "__main__":
    run()
