import requests
import csv
import pandas as pd

RISK_URL = "https://api.moneycontrol.com/swiftapi/v1/mutualfunds/risk-metrics"
HOLDINGS_URL = "https://api.moneycontrol.com/swiftapi/v1/mutualfunds/holdings"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.moneycontrol.com",
    "referer": "https://www.moneycontrol.com/",
    "user-agent": "Mozilla/5.0"
}

FILE_PATH = "mutualfunds/raw_funds.tsv"


# 🔍 Lookup
def get_isin(fund_name):
    with open(FILE_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if fund_name.lower() in row["schemeName"].lower():
                return row.get("isin"), row["schemeName"]
    return None, None


# 📡 API fetch
def fetch_api(url, isin, session):
    params = {
        "isin": isin,
        "deviceType": "W",
        "responseType": "json"
    }
    r = session.get(url, params=params, timeout=10)

    if "application/json" not in r.headers.get("content-type", ""):
        print("❌ Bad response:", r.url)
        return None

    return r.json()


# =========================
# 📊 RISK → DataFrame
# =========================
def parse_risk_df(risk_json, fund_name, isin):
    data = risk_json.get("data", {})

    row = {
        "schemeName": fund_name,
        "isin": isin
    }

    # Returns
    returns = data.get("returns", {})
    for k, v in returns.items():
        if isinstance(v, dict):
            continue
        row[f"returns_{k}"] = v

    # Std Dev
    std = data.get("risk_std_dev", {})
    for k, v in std.items():
        if isinstance(v, dict):
            continue
        row[f"std_{k}"] = v

    # Sharpe
    sharpe = data.get("sharpe_ratio", {})
    for k, v in sharpe.items():
        if isinstance(v, dict):
            continue
        row[f"sharpe_{k}"] = v

    # Sortino
    sortino = data.get("sortino_ratio", {})
    for k, v in sortino.items():
        if isinstance(v, dict):
            continue
        row[f"sortino_{k}"] = v

    # Beta
    beta = data.get("beta", {})
    for k, v in beta.items():
        if isinstance(v, dict):
            continue
        row[f"beta_{k}"] = v

    return pd.DataFrame([row])


# =========================
# 📦 HOLDINGS → DataFrame
# =========================
def parse_holdings_df(holdings_json, fund_name, isin):
    stocks = holdings_json.get("data", {}).get("stock", [])

    rows = []

    for s in stocks:
        base = {
            "schemeName": fund_name,
            "isin": isin,
            "stock_name": s.get("name"),
            "sector": s.get("sector"),
            "market_value": s.get("marketvalue"),
            "weight": s.get("weighting"),
            "change_1m": s.get("change1M")
        }

        # Expand historical holdings
        history = s.get("holdings", [])

        if history:
            for h in history:
                row = base.copy()
                row["period"] = h.get("per")
                row["weightage"] = h.get("weightage")
                rows.append(row)
        else:
            rows.append(base)

    return pd.DataFrame(rows)


# =========================
# 🚀 MAIN
# =========================
def main():
    fund_input = input("Enter fund name: ").strip()

    isin, name = get_isin(fund_input)

    if not isin:
        print("❌ Fund not found")
        return

    print(f"✅ Found: {name} ({isin})")

    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://www.moneycontrol.com/")

    # Fetch
    risk_json = fetch_api(RISK_URL, isin, session)
    holdings_json = fetch_api(HOLDINGS_URL, isin, session)

    # Parse
    risk_df = parse_risk_df(risk_json, name, isin) if risk_json else pd.DataFrame()
    holdings_df = parse_holdings_df(holdings_json, name, isin) if holdings_json else pd.DataFrame()

    # Show
    print("\n📊 Risk DF:")
    print(risk_df.head())

    print("\n📦 Holdings DF:")
    print(holdings_df.head())

    # Optional save
    risk_df.to_csv(f"mutualfunds/fund_info/risk_metrics_{isin}.tsv", sep="\t", index=False)
    holdings_df.to_csv(f"mutualfunds/fund_info/holdings_{isin}.tsv", sep="\t", index=False)

    print("\n💾 Saved to files")


if __name__ == "__main__":
    main()