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
    "/TMACT/TMSRC238_ViewActionItemCompleted.aspx?Mode=C&SELECTEDCOMPANYID=2&MENUCLICK=TMCOMPANY"
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
# LOAD PAGE (for content check)
# -----------------------------
def load_page(page, url):
    try:
        start = time.time()
        page.goto(url, timeout=TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        load_time = round(time.time() - start, 2)
        return load_time, None
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

        print(" Opening login page...")
        page.goto(BASE_URL, timeout=TIMEOUT)

        print(" Logging in...")
        try:
            page.fill("input[type='text']", USERNAME)
            page.fill("input[type='password']", PASSWORD)
            page.click("input[type='submit']")
        except Exception as e:
            print(" Login error:", e)
            browser.close()
            return

        page.wait_for_timeout(4000)

        if "login" in page.url.lower():
            print(" Login failed")
            browser.close()
            return

        print(" Login successful\n")

        failed_results = []

        for path in PATHS:
            url = BASE_URL + path

            status_code, req_error = get_status(context, url)
            load_time, nav_error = load_page(page, url)

            page_content = page.content().lower()
            current_url = page.url.lower()

            # -----------------------------
            # DETERMINE STATUS
            # -----------------------------
            if status_code is None:
                final_status = "Network Error"

            elif "login" in current_url:
                final_status = f"{status_code} (Auth Issue)"

            elif "genericerror" in current_url or "something went wrong" in page_content:
                final_status = f"{status_code} (Application Error)"

            else:
                final_status = str(status_code)

            print(f"{final_status} | {load_time}s | {url}")

            #  SAVE ONLY FAILURES
            if final_status != "200":
                failed_results.append([
                    url,
                    final_status,
                    load_time if load_time else "",
                    req_error or nav_error or ""
                ])

        browser.close()

        # -----------------------------
        # SAVE REPORT
        # -----------------------------
        if failed_results:
            with open(report_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["URL", "Status", "Load Time (s)", "Error"])
                writer.writerows(failed_results)

            print(f"\n Failed report saved: {report_file}")
        else:
            print("\n No failed URLs found")


if __name__ == "__main__":
    run()
