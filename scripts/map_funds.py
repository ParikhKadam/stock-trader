import pandas as pd
import json
from pathlib import Path

input_file = Path("mutualfunds/raw_funds.tsv")
output_file = Path("mutualfunds/all_funds_moneycontrol.tsv")

df = pd.read_csv(input_file, sep="\t")


def extract_returns(trailing_json, freq):
    try:
        data = json.loads(trailing_json)
        for item in data:
            if item.get("frequency") == freq:
                return item.get("annualisedReturn")
    except:
        return None


df_mapped = pd.DataFrame()
df_mapped["Scheme Name"] = df["schemeName"]
df_mapped["Plan"] = "Direct Plan"
df_mapped["Category Name"] = df["invCategory"]
df_mapped["Crisil Rating"] = df["rating"]
df_mapped["AuM (Cr)"] = ""

return_cols = ["1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "3Y", "5Y", "10Y"]

for col in return_cols:
    df_mapped[col] = df["trailingReturns"].apply(
        lambda x: extract_returns(x, col)
    ).apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")

df_mapped.to_csv(output_file, sep="\t", index=False)

print(f"Mapped data saved to {output_file}")