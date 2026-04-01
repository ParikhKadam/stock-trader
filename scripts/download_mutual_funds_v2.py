import requests
import csv
from pathlib import Path
import time
import json

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
    "user-agent": "Mozilla/5.0"
}

output_dir = Path("mutualfunds")
output_dir.mkdir(exist_ok=True)
output_file = output_dir / "raw_funds.tsv"

session = requests.Session()
session.headers.update(HEADERS)

# Warm-up
session.get("https://www.moneycontrol.com/")

all_funds = []


def debug_response(response, note=""):
    print("\n🚨 DEBUG INFO", f"({note})" if note else "")
    print("URL:", response.url)
    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Response (first 500 chars):")
    print(response.text[:500])
    print("-" * 80)


print("\n📊 Fetching ALL funds (RAW mode)...")

page = 1

while True:
    params = {
        **COMMON_PARAMS,
        "page": page
    }

    try:
        response = session.get(BASE_URL, params=params, timeout=10)

        print(f"➡️ Page {page}: {response.status_code}")

        if "application/json" not in response.headers.get("content-type", ""):
            debug_response(response, "Non-JSON response")
            break

        try:
            data = response.json()
        except Exception:
            debug_response(response, "JSON decode failed")
            break

        schemes = data.get("data", {}).get("schemeList", [])

        if not schemes:
            print(f"⛔ No more data (page {page})")
            break

        for scheme in schemes:
            # ✅ Keep everything raw
            row = {}

            for key, value in scheme.items():
                # Convert nested JSON to string
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value)
                else:
                    row[key] = value

            all_funds.append(row)

        print(f"✅ Got {len(schemes)} schemes")
        page += 1

        time.sleep(0.5)

    except Exception as e:
        print(f"❌ Error: {e}")
        if 'response' in locals():
            debug_response(response, "Exception occurred")
        break


# 💾 Save
if all_funds:
    # collect all keys dynamically
    fieldnames = sorted({k for d in all_funds for k in d.keys()})

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_funds)

    print(f"\n💾 Saved {len(all_funds)} raw records → {output_file}")
else:
    print("⚠️ No data collected")