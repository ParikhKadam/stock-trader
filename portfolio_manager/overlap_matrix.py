import pandas as pd
from pathlib import Path

def compute_overlap_matrix(ranked_funds):
    """
    Compute pairwise overlap matrix.
    Overlap_A,B = sum(min(weight_A_i, weight_B_i) for all stocks i)
    """
    holdings = {}
    base_path = Path("/home/kadam/data/me/swing-trader/mutualfunds/fund_info")
    
    for isin in ranked_funds:
        holdings_file = base_path / f"holdings_{isin}.tsv"
        if not holdings_file.exists():
            holdings[isin] = {}
            continue
        
        df = pd.read_csv(holdings_file, sep='\t')
        # Aggregate weights by stock_name (sum across periods)
        df_agg = df.groupby('stock_name')['weight'].sum().reset_index()
        holdings[isin] = df_agg.set_index('stock_name')['weight'].to_dict()
    
    n = len(ranked_funds)
    overlap = pd.DataFrame(0.0, index=ranked_funds, columns=ranked_funds)
    
    for i in range(n):
        for j in range(i + 1, n):
            fund_a = ranked_funds[i]
            fund_b = ranked_funds[j]
            overlap_ab = 0.0
            all_stocks = set(holdings[fund_a].keys()) | set(holdings[fund_b].keys())
            for stock in all_stocks:
                w_a = holdings[fund_a].get(stock, 0.0)
                w_b = holdings[fund_b].get(stock, 0.0)
                overlap_ab += min(w_a, w_b)
            overlap.loc[fund_a, fund_b] = overlap_ab
            overlap.loc[fund_b, fund_a] = overlap_ab
    
    return overlap
