import requests
import csv
from pathlib import Path
import time

BASE_URL = "https://api.moneycontrol.com/swiftapi/v1/mutualfunds/getSchemeCollection"

COMMON_PARAMS = {
    "responseType": "json",
    "deviceType": "W",
    "pageSize": 25,
    "collection": "ALL",
    "tab": "RETURNS",
    "invType": "Equity",
    "schemePlan": "Direct Plan",
    "sortBy": "RETURN_DESC"
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://www.moneycontrol.com",
    "referer": "https://www.moneycontrol.com/",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

CATEGORY_MAPPING = {
    "Large Cap Fund": "Large-Cap",
    "Mid Cap Fund": "Mid-Cap",
    "Small Cap Fund": "Small-Cap",
    "Multi Cap Fund": "Multi-Cap",
    "Flexi Cap Fund": "Flexi-Cap",
    "Large & Mid Cap Fund": "Large-Mid-Cap",
    "Focused Fund": "Focused",
    "Value Fund": "Value",
    "Contra Fund": "Contra",
    "ELSS": "ELSS",
    "Sectoral/Thematic": "Sectoral-Thematic"
}

# 📁 Output
output_dir = Path("mutualfunds")
output_dir.mkdir(exist_ok=True)
output_file = output_dir / "all_funds.tsv"

# 🔥 Session (important)
session = requests.Session()
session.headers.update(HEADERS)

# Warm-up request (sets cookies)
session.get("https://www.moneycontrol.com/")

all_funds = []


# 🔧 Helper: flatten trailing returns
def extract_returns(trailing_returns):
    result = {}
    for item in trailing_returns:
        freq = item.get("frequency")
        result[freq] = item.get("annualisedReturn")
    return result


# 🔁 Main loop
for category_name, api_category in CATEGORY_MAPPING.items():
    print(f"\n📊 Fetching: {category_name}")
    
    page = 1
    category_data = []

    while True:
        params = {
            **COMMON_PARAMS,
            "page": page,
            "invCategory": api_category
        }

        try:
            response = session.get(BASE_URL, params=params, timeout=10)

            print(f"➡️ Page {page}: {response.status_code}")

            # 🚨 Detect blocked / invalid response
            if "application/json" not in response.headers.get("content-type", ""):
                print("⚠️ Non-JSON response")
                print(response.text[:200])
                break

            data = response.json()

            schemes = data.get("data", {}).get("schemeList", [])

            if not schemes:
                print(f"⛔ No more data (page {page})")
                break

            for scheme in schemes:
                returns = extract_returns(scheme.get("trailingReturns", []))

                row = {
                    "Scheme Name": scheme.get("schemeName"),
                    "Category": category_name,
                    "Rating": scheme.get("rating"),
                    "Risk": scheme.get("risk"),
                    "1W": returns.get("1W"),
                    "1M": returns.get("1M"),
                    "3M": returns.get("3M"),
                    "6M": returns.get("6M"),
                    "YTD": returns.get("YTD"),
                    "1Y": returns.get("1Y"),
                    "2Y": returns.get("2Y"),
                    "3Y": returns.get("3Y"),
                    "5Y": returns.get("5Y"),
                    "10Y": returns.get("10Y"),
                }

                category_data.append(row)

            print(f"✅ Got {len(schemes)} schemes")
            page += 1

            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error: {e}")
            break

    print(f"📦 Total: {len(category_data)}")
    all_funds.extend(category_data)


# 💾 Save
if all_funds:
    fieldnames = list(all_funds[0].keys())

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_funds)

    print(f"\n💾 Saved {len(all_funds)} funds → {output_file}")

else:
    print("⚠️ No data collected")