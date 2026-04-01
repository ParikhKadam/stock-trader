import pandas as pd
from pathlib import Path

def optimize_portfolio(ranked_funds, overlap_matrix, risk_profile):
    """
    Optimize portfolio:
    - Select number of funds based on risk profile
    - Remove funds with >40% overlap
    - Allocate weights based on Sharpe/StdDev ratio
    """
    if risk_profile == 'conservative':
        num_select = min(3, len(ranked_funds))
    elif risk_profile == 'moderate':
        num_select = min(4, len(ranked_funds))
    else:  # aggressive
        num_select = min(5, len(ranked_funds))
    
    # Select top num_select
    selected = ranked_funds[:num_select]
    
    # Remove funds with >40% overlap with any other selected fund
    to_remove = set()
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            if overlap_matrix.loc[selected[i], selected[j]] > 40:
                to_remove.add(selected[j])  # Remove lower ranked
    
    selected = [f for f in selected if f not in to_remove]
    
    # Allocate weights based on Sharpe/StdDev
    weights = {}
    total_ratio = 0.0
    base_path = Path("/home/kadam/data/me/swing-trader/mutualfunds/fund_info")
    
    for isin in selected:
        risk_file = base_path / f"risk_metrics_{isin}.tsv"
        if not risk_file.exists():
            continue
        
        risk_df = pd.read_csv(risk_file, sep='\t')
        if risk_df.empty:
            continue
        
        row = risk_df.iloc[0]
        sharpe_3y = row.get('sharpe_3y', 0)
        std_3y = row.get('std_3y', 0)
        ratio = sharpe_3y / std_3y if std_3y > 0 else 0
        weights[isin] = ratio
        total_ratio += ratio
    
    if total_ratio > 0:
        weights = {k: v / total_ratio for k, v in weights.items()}
    else:
        # Fallback to equal weights
        n = len(selected)
        if n > 0:
            equal_weight = 1.0 / n
            weights = {isin: equal_weight for isin in selected}
    
    return weights
