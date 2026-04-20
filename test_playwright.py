from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # visible browser
    page = browser.new_page()

    page.goto("https://hsa.fldata.com")

    print("Title:", page.title())

    input("Press Enter to close...")  # keep browser open

    browser.close()
