import pandas as pd
from pathlib import Path

# Input and output files
input_file = Path("mutualfunds/raw_funds.tsv")
output_file = Path("mutualfunds/top_funds_moneycontrol_updated.tsv")

# Read raw data
df = pd.read_csv(input_file, sep="\t")

# Mapping
df_mapped = pd.DataFrame()
df_mapped["Scheme Name"] = df["Scheme Name"]
df_mapped["Plan"] = "Direct Plan"
df_mapped["Category Name"] = df["Category"]
df_mapped["Crisil Rating"] = df["Rating"]
df_mapped["AuM (Cr)"] = ""  # Not available in API

# Returns columns
return_cols = ["1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "3Y", "5Y", "10Y"]
for col in return_cols:
    df_mapped[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "")

# Save to TSV
df_mapped.to_csv(output_file, sep="\t", index=False)
print(f"Mapped data saved to {output_file}")