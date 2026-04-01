import pandas as pd
from pathlib import Path

def quality_filter(fund_isins):
    """
    Filter funds based on quality criteria:
    - Sharpe_3Y >= category average
    - StdDev_3Y <= 1.2 * category average
    - Returns_3Y > 0
    """
    filtered = []
    base_path = Path("/home/kadam/data/me/swing-trader/mutualfunds/fund_info")
    
    for isin in fund_isins:
        risk_file = base_path / f"risk_metrics_{isin}.tsv"
        if not risk_file.exists():
            print(f"Risk metrics file not found for {isin}")
            continue
        
        risk_df = pd.read_csv(risk_file, sep='\t')
        if risk_df.empty:
            continue
        
        row = risk_df.iloc[0]
        sharpe_3y = row.get('sharpe_3y', 0)
        std_3y = row.get('std_3y', 0)
        returns_3y = row.get('returns_3y', 0)
        sharpe_cat_avg_3y = row.get('sharpe_cat_avg_3y', 0)
        std_cat_avg_3y = row.get('std_cat_avg_3y', 0)
        
        if sharpe_3y >= sharpe_cat_avg_3y and std_3y <= std_cat_avg_3y * 1.2 and returns_3y > 0:
            filtered.append(isin)
    
    return filtered
