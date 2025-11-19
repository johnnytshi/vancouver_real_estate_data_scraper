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
            page.wait_for_url("**/map.html", timeout=15000)
        except:
            print("Manually navigating to map.html...")
            page.goto("https://www.zealty.ca/map.html")
            page.wait_for_load_state("networkidle")
        
        time.sleep(5) # Wait for map to load
        
        # Click on "For Sale" button
        print("\n=== Clicking 'For Sale' ===")
        for_sale_btn = page.get_by_text("For Sale", exact=False).first
        for_sale_btn.click()
        time.sleep(2)
        page.screenshot(path="for_sale_clicked.png")
        
        # Look for date selector - might be a dropdown or date input
        # Let's check the page content
        print("Looking for date selector after clicking For Sale...")
        # Try to find select elements or date inputs near the button
        selects = page.locator("select").all()
        print(f"Found {len(selects)} select elements")
        for i, select in enumerate(selects):
            if select.is_visible():
                print(f"  Select {i}: {select.get_attribute('name')} / {select.get_attribute('id')}")
                options = select.locator("option").all()
                print(f"    Options: {[opt.text_content() for opt in options[:5]]}")  # First 5 options
        
        # Click on "Solds" button
        print("\n=== Clicking 'Solds' ===")
        solds_btn = page.get_by_text("Solds", exact=False).first
        solds_btn.click()
        time.sleep(2)
        page.screenshot(path="solds_clicked.png")
        
        print("Looking for date selector after clicking Solds...")
        selects = page.locator("select").all()
        print(f"Found {len(selects)} select elements")
        for i, select in enumerate(selects):
            if select.is_visible():
                print(f"  Select {i}: {select.get_attribute('name')} / {select.get_attribute('id')}")
                options = select.locator("option").all()
                print(f"    Options: {[opt.text_content() for opt in options[:5]]}")
        
        # Click on "Expired" button
        print("\n=== Clicking 'Expired' ===")
        expired_btn = page.get_by_text("Expired", exact=False).first
        expired_btn.click()
        time.sleep(2)
        page.screenshot(path="expired_clicked.png")
        
        print("Looking for date selector after clicking Expired...")
        selects = page.locator("select").all()
        print(f"Found {len(selects)} select elements")
        for i, select in enumerate(selects):
            if select.is_visible():
                print(f"  Select {i}: {select.get_attribute('name')} / {select.get_attribute('id')}")
                options = select.locator("option").all()
                print(f"    Options: {[opt.text_content() for opt in options[:5]]}")

        browser.close()

if __name__ == "__main__":
    run()
