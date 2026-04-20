from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
import csv
from datetime import datetime

# -----------------------------
# LOAD ENV
# -----------------------------
load_dotenv()
USERNAME = os.getenv("SITE_USERNAME")
PASSWORD = os.getenv("SITE_PASSWORD")

BASE_URL = "https://hsa.fldata.com"
TIMEOUT = 30000

PATHS = [
    "/mainpage.aspx",
    "/TMReports/TMSRC25_ReportSelection.aspx?ParentItem=People&MENUCLICK=TMMYEMPLOYEES",
    "/TMOther/SelectOrganization.aspx?GoToPage=../TMPeople/TMSRC57_ViewPeople.aspx&MENUCLICK=TMDIVISION",
    "/TMPeople/TMSRC57_ViewPeople.aspx?SELECTEDDIVISIONID=5&MENUCLICK=TMDIVISION",
    "/TMCurriculum/TMSRC71_ViewJobs.aspx?SELECTEDDIVISIONID=5&MENUCLICK=TMDIVISION",
    "/TMClasses/TMSRC104_ViewILTScheduler.aspx?ClassType=OPEN&SELECTEDDIVISIONID=5&MENUCLICK=TMDIVISION",
    "/TMAuthor/TMSRC302_ChangeNoToAsk.aspx?TestID=26",
    "/TMSettings/TMSRC67_ViewAccount.aspx?SELECTEDDIVISIONID=5&MENUCLICK=TMDIVISION",
    "/TMlibrary/TMSRC26_LibraryInfo.aspx",
    "/TMMOC/TMSRC140_ViewComplete.aspx?Mode=C&SELECTEDCOMPANYID=2&MENUCLICK=TMCOMPANY",
    "/TMACT/TMSRC238_ViewActionItemCompleted.aspx?Mode=C&SELECTEDCOMPANYID=2&MENUCLICK=TMCOMPANY",

    # --- TEST FAILURES ---
    "/this-page-does-not-exist-999",
    "/TMReportsInvalid/TMSRC25_ReportSelection.aspx",
    "/TMPeople/TMSRC57_ViewPeople.aspx?SELECTEDDIVISIONID=999999999",
    "/logout.aspx",
    "/abc/xyz/test/page.aspx",
    "/TMClasses///invalid///path.aspx",
    "/TMCurriculum/TMSRC71_ViewJobs.aspx?delay=999999999",
    "/!@#$%^&*()_invalid_url"
]


# -----------------------------
# GET REAL HTTP STATUS
# -----------------------------
def get_status(context, url):
    try:
        resp = context.request.get(url, timeout=TIMEOUT)
        return resp.status, None
    except Exception as e:
        return None, str(e)


# -----------------------------
# SAFE PAGE LOAD (OPTIONAL)
# -----------------------------
def load_page(page, url):
    try:
        start = time.time()
        page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        return round(time.time() - start, 2), None
    except Exception as e:
        return None, str(e)


# -----------------------------
# MAIN
# -----------------------------
def run():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = f"failed_report_{timestamp}.csv"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--no-zygote",
                "--single-process"
            ]
        )

        context = browser.new_context()
        page = context.new_page()

        print("🔐 Opening login page...")
        page.goto(BASE_URL, timeout=TIMEOUT)

        print("🔐 Logging in...")
        try:
            page.fill("input[type='text']", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            page.click("input[type='submit']")
        except Exception as e:
            print("❌ Login error:", e)
            browser.close()
            return

        page.wait_for_timeout(4000)

        if "login" in page.url.lower():
            print("❌ Login failed")
            browser.close()
            return

        print("✅ Login successful\n")

        # -----------------------------
        # SCAN
        # -----------------------------
        failed_results = []

        for path in PATHS:
            url = BASE_URL + path

            # 1. Get REAL HTTP status
            status_code, req_error = get_status(context, url)

            # 2. Load page (optional but useful)
            load_time, nav_error = load_page(page, url)

            # -----------------------------
            # DECIDE STATUS
            # -----------------------------
            if status_code is None:
                status = "Network Error"
                error = req_error

            elif "login" in page.url.lower():
                status = "Not Authenticated"
                error = ""

            elif status_code == 200:
                status = "OK"
                error = ""

            elif status_code == 404:
                status = "404 Not Found"
                error = ""

            elif status_code >= 500:
                status = "Server Error"
                error = ""

            else:
                status = f"HTTP {status_code}"
                error = ""

            print(f"{status} | {load_time}s | {url}")

            # ✅ ONLY STORE FAILURES
            if status != "OK":
                failed_results.append([
                    url,
                    status,
                    status_code if status_code else "",
                    load_time if load_time else "",
                    error or nav_error or ""
                ])

        browser.close()

        # -----------------------------
        # SAVE ONLY FAILED
        # -----------------------------
        if failed_results:
            with open(report_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["URL", "Status", "HTTP Code", "Load Time (s)", "Error"])
                writer.writerows(failed_results)

            print(f"\n📊 Failed report saved: {report_file}")
        else:
            print("\n✅ No failed URLs found")


if __name__ == "__main__":
    run()
