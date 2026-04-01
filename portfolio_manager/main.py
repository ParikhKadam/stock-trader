import pandas as pd
from pathlib import Path

# Placeholder for actual filter, ranking, and optimizer modules
from .quality_filter import quality_filter
from .fund_ranker import rank_funds
from .overlap_matrix import compute_overlap_matrix
from .portfolio_optimizer import optimize_portfolio

def get_fund_isin(fund_name, raw_data_path):
    df = pd.read_csv(raw_data_path, sep='\t')
    match = df[df['schemeName'].str.lower() == fund_name.lower()]
    if not match.empty:
        return match.iloc[0]['isin']
    return None

def main():
    print("=== Portfolio Manager ===")
    num_funds = int(input("Enter number of funds to include: "))
    risk_profile = input("Enter investor risk profile (conservative/moderate/aggressive): ").strip().lower()
    raw_data_path = input("Enter path to raw fund data CSV/TSV: ").strip()

    fund_names = []
    fund_isins = []
    for i in range(num_funds):
        name = input(f"Enter name of fund #{i+1}: ").strip()
        fund_names.append(name)
        isin = get_fund_isin(name, raw_data_path)
        if isin:
            print(f"  ISIN for {name}: {isin}")
            fund_isins.append(isin)
        else:
            print(f"  ISIN for {name} not found! Skipping.")

    if not fund_isins:
        print("No valid funds found. Exiting.")
        return

    # Step 1: Quality filter
    filtered_funds = quality_filter(fund_isins)
    print(f"Funds after quality filter: {len(filtered_funds)} out of {len(fund_isins)}")

    if not filtered_funds:
        print("No funds passed quality filter. Exiting.")
        return

    # Step 2: Ranking
    ranked_funds = rank_funds(filtered_funds)
    print(f"Ranked funds: {ranked_funds}")

    # Step 3: Overlap matrix
    overlap = compute_overlap_matrix(ranked_funds)
    print("Overlap matrix (%):")
    print(overlap)

    # Step 4: Portfolio optimization
    portfolio = optimize_portfolio(ranked_funds, overlap, risk_profile)
    print("\n=== Final Portfolio ===")
    for fund, weight in portfolio.items():
        print(f"{fund}: {weight:.2%}")

if __name__ == "__main__":
    main()
