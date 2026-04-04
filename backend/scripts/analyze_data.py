"""
Deep analysis of STE and Contracts datasets.
Outputs statistics, data quality report, and patterns for ML feature engineering.
"""
import sys
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent
STE_FILE = DATA_DIR / "СТЕ_20260403.csv"
CONTRACTS_FILE = DATA_DIR / "Контракты_20260403.csv"

STE_COLS = ["ste_id", "name", "category", "attributes"]
CONTRACT_COLS = [
    "purchase_name", "contract_id", "ste_id", "contract_date",
    "contract_cost", "customer_inn", "customer_name", "customer_region",
    "supplier_inn", "supplier_name", "supplier_region",
]


def analyze_ste():
    print("=" * 80)
    print("STE (Standard Trade Entity) ANALYSIS")
    print("=" * 80)

    df = pd.read_csv(STE_FILE, sep=";", header=None, names=STE_COLS, dtype={"ste_id": str})
    print(f"\nTotal rows: {len(df):,}")
    print(f"Unique STE IDs: {df['ste_id'].nunique():,}")
    print(f"Duplicate STE IDs: {len(df) - df['ste_id'].nunique():,}")

    print(f"\nMissing values:")
    for col in STE_COLS:
        null_count = df[col].isna().sum()
        pct = null_count / len(df) * 100
        print(f"  {col}: {null_count:,} ({pct:.2f}%)")

    print(f"\nName statistics:")
    name_lens = df["name"].dropna().str.len()
    print(f"  Min length: {name_lens.min()}")
    print(f"  Max length: {name_lens.max()}")
    print(f"  Mean length: {name_lens.mean():.1f}")
    print(f"  Median length: {name_lens.median():.1f}")

    print(f"\nCategory statistics:")
    print(f"  Unique categories: {df['category'].nunique():,}")
    top_cats = df["category"].value_counts().head(30)
    print(f"  Top 30 categories:")
    for cat, count in top_cats.items():
        print(f"    {cat}: {count:,} ({count/len(df)*100:.2f}%)")

    print(f"\nAttribute analysis:")
    has_attrs = df["attributes"].notna().sum()
    print(f"  Rows with attributes: {has_attrs:,} ({has_attrs/len(df)*100:.1f}%)")

    sample_attrs = df["attributes"].dropna().head(100)
    all_keys = Counter()
    for attr_str in sample_attrs:
        pairs = str(attr_str).split(";")
        for pair in pairs:
            if ":" in pair:
                key = pair.split(":")[0].strip()
                if key:
                    all_keys[key] += 1

    print(f"  Top 20 attribute keys (from sample of 100 rows):")
    for key, count in all_keys.most_common(20):
        print(f"    {key}: {count}")

    attr_lens = df["attributes"].dropna().str.len()
    print(f"\n  Attribute string length stats:")
    print(f"    Min: {attr_lens.min()}")
    print(f"    Max: {attr_lens.max()}")
    print(f"    Mean: {attr_lens.mean():.0f}")
    print(f"    Median: {attr_lens.median():.0f}")

    print(f"\n  Checking for duplicate attribute patterns...")
    dup_count = 0
    sample_100 = df["attributes"].dropna().head(1000)
    for attr_str in sample_100:
        pairs = str(attr_str).split(";")
        if len(pairs) != len(set(pairs)):
            dup_count += 1
    print(f"    Rows with duplicated attribute pairs (sample 1000): {dup_count}")

    return df


def analyze_contracts():
    print("\n" + "=" * 80)
    print("CONTRACTS ANALYSIS")
    print("=" * 80)

    df = pd.read_csv(
        CONTRACTS_FILE, sep=";", header=None, names=CONTRACT_COLS,
        dtype={"contract_id": str, "ste_id": str, "customer_inn": str, "supplier_inn": str},
        low_memory=False,
    )
    print(f"\nTotal rows: {len(df):,}")
    print(f"Unique contract IDs: {df['contract_id'].nunique():,}")
    print(f"Unique STE IDs referenced: {df['ste_id'].nunique():,}")

    print(f"\nMissing values:")
    for col in CONTRACT_COLS:
        null_count = df[col].isna().sum()
        pct = null_count / len(df) * 100
        print(f"  {col}: {null_count:,} ({pct:.2f}%)")

    print(f"\nCustomer statistics:")
    print(f"  Unique customer INNs: {df['customer_inn'].nunique():,}")
    print(f"  Unique customer names: {df['customer_name'].nunique():,}")
    print(f"  Unique customer regions: {df['customer_region'].nunique():,}")

    top_customers = df["customer_inn"].value_counts().head(10)
    print(f"  Top 10 customers by contract count:")
    for inn, count in top_customers.items():
        name = df[df["customer_inn"] == inn]["customer_name"].iloc[0]
        print(f"    INN {inn}: {count:,} contracts - {name[:60]}")

    print(f"\nSupplier statistics:")
    print(f"  Unique supplier INNs: {df['supplier_inn'].nunique():,}")
    top_suppliers = df["supplier_inn"].value_counts().head(10)
    print(f"  Top 10 suppliers:")
    for inn, count in top_suppliers.items():
        name = df[df["supplier_inn"] == inn]["supplier_name"].iloc[0]
        print(f"    INN {inn}: {count:,} contracts - {name[:60]}")

    print(f"\nRegion statistics:")
    top_regions = df["customer_region"].value_counts().head(15)
    print(f"  Top 15 customer regions:")
    for region, count in top_regions.items():
        print(f"    {region}: {count:,} ({count/len(df)*100:.1f}%)")

    print(f"\nContract cost statistics:")
    costs = pd.to_numeric(df["contract_cost"], errors="coerce")
    print(f"  Min: {costs.min():,.2f}")
    print(f"  Max: {costs.max():,.2f}")
    print(f"  Mean: {costs.mean():,.2f}")
    print(f"  Median: {costs.median():,.2f}")
    print(f"  Std: {costs.std():,.2f}")

    print(f"\nDate range:")
    dates = pd.to_datetime(df["contract_date"], errors="coerce")
    print(f"  Earliest: {dates.min()}")
    print(f"  Latest: {dates.max()}")

    print(f"\nContracts per STE statistics:")
    ste_counts = df["ste_id"].value_counts()
    print(f"  Mean contracts per STE: {ste_counts.mean():.1f}")
    print(f"  Median contracts per STE: {ste_counts.median():.1f}")
    print(f"  Max contracts per STE: {ste_counts.max():,}")
    print(f"  STEs with only 1 contract: {(ste_counts == 1).sum():,}")

    print(f"\nContracts per customer statistics:")
    cust_counts = df["customer_inn"].value_counts()
    print(f"  Mean contracts per customer: {cust_counts.mean():.1f}")
    print(f"  Median contracts per customer: {cust_counts.median():.1f}")
    print(f"  Max contracts per customer: {cust_counts.max():,}")
    print(f"  Customers with only 1 contract: {(cust_counts == 1).sum():,}")
    print(f"  Customers with >10 contracts: {(cust_counts > 10).sum():,}")
    print(f"  Customers with >100 contracts: {(cust_counts > 100).sum():,}")

    return df


def cross_analysis(ste_df, contracts_df):
    print("\n" + "=" * 80)
    print("CROSS-DATASET ANALYSIS")
    print("=" * 80)

    ste_ids = set(ste_df["ste_id"].astype(str).unique())
    contract_ste_ids = set(contracts_df["ste_id"].astype(str).unique())

    shared = ste_ids & contract_ste_ids
    ste_only = ste_ids - contract_ste_ids
    contract_only = contract_ste_ids - ste_ids

    print(f"\nSTE ID overlap:")
    print(f"  STEs in catalog: {len(ste_ids):,}")
    print(f"  STEs referenced in contracts: {len(contract_ste_ids):,}")
    print(f"  STEs in both: {len(shared):,}")
    print(f"  STEs only in catalog (no contracts): {len(ste_only):,}")
    print(f"  STEs only in contracts (not in catalog): {len(contract_only):,}")

    print(f"\nUser-Category co-occurrence (for personalization):")
    merged = contracts_df.merge(
        ste_df[["ste_id", "category"]].astype({"ste_id": str}),
        on="ste_id", how="left"
    )
    user_cats = merged.groupby("customer_inn")["category"].nunique()
    print(f"  Avg unique categories per customer: {user_cats.mean():.1f}")
    print(f"  Median unique categories per customer: {user_cats.median():.1f}")
    print(f"  Max unique categories per customer: {user_cats.max()}")

    print(f"\nCategory popularity (by contract volume):")
    cat_contracts = merged["category"].value_counts().head(20)
    for cat, count in cat_contracts.items():
        print(f"    {cat}: {count:,} contracts")


def main():
    ste_df = analyze_ste()
    contracts_df = analyze_contracts()
    cross_analysis(ste_df, contracts_df)

    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    print("""
KEY FINDINGS:
1. STE catalog has ~543K items with names, categories, and structured attributes
2. Contracts have ~2M records linking customers to STEs
3. Attributes contain duplicated key-value pairs that need deduplication
4. Data is semicolon-separated WITHOUT headers

ML RECOMMENDATIONS:
1. Use rubert-tiny2 for embeddings (312-dim, fast, Russian-optimized)
2. Build BM25 index on deduplicated STE names + categories
3. Build SymSpell dictionary from all unique words in STE names
4. Extract user preference vectors from contract history per customer INN
5. Train lightweight CatBoost ranker using contract co-occurrence as relevance signal
6. Use JAX for fast batch embedding inference and custom ranking model
""")


if __name__ == "__main__":
    main()
