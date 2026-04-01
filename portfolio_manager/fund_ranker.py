import pandas as pd
from pathlib import Path

def rank_funds(filtered_funds):
    """
    Rank funds based on composite score:
    Score = 0.4 * Sharpe_3Y + 0.2 * Sortino_3Y + 0.2 * Returns_3Y - 0.2 * StdDev_3Y
    """
    scores = []
    base_path = Path("/home/kadam/data/me/swing-trader/mutualfunds/fund_info")
    
    for isin in filtered_funds:
        risk_file = base_path / f"risk_metrics_{isin}.tsv"
        if not risk_file.exists():
            continue
        
        risk_df = pd.read_csv(risk_file, sep='\t')
        if risk_df.empty:
            continue
        
        row = risk_df.iloc[0]
        sharpe_3y = row.get('sharpe_3y', 0)
        sortino_3y = row.get('sortino_3y', 0)
        returns_3y = row.get('returns_3y', 0)
        std_3y = row.get('std_3y', 0)
        
        score = 0.4 * sharpe_3y + 0.2 * sortino_3y + 0.2 * returns_3y - 0.2 * std_3y
        scores.append((isin, score))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    return [isin for isin, _ in scores]
