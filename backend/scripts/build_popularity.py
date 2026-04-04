"""
Popularity scoring for STE items from contract history.
Computes normalized popularity (0..1) per STE based on contract counts + volume.
Stores in Redis HSET for O(1) lookup during ranking.
Can also dump to CSV for analysis.
"""
import sys
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

CONTRACT_COLS = [
    "purchase_name", "contract_id", "ste_id", "contract_date",
    "contract_cost", "customer_inn", "customer_name", "customer_region",
    "supplier_inn", "supplier_name", "supplier_region",
]


def compute_popularity(contracts_file: str) -> pd.DataFrame:
    """Aggregate contract_count and total_volume per STE, normalize to 0..1."""
    logger.info(f"Loading contracts from {contracts_file}")
    df = pd.read_csv(
        contracts_file, sep=";", header=None, names=CONTRACT_COLS,
        dtype={"ste_id": str, "contract_cost": float},
        low_memory=False,
    )
    logger.info(f"Loaded {len(df)} contracts")

    agg = df.groupby("ste_id").agg(
        contract_count=("contract_id", "count"),
        total_volume=("contract_cost", "sum"),
        unique_customers=("customer_inn", "nunique"),
    ).reset_index()

    max_count = agg["contract_count"].max() or 1
    max_volume = agg["total_volume"].max() or 1
    max_customers = agg["unique_customers"].max() or 1

    agg["count_norm"] = agg["contract_count"] / max_count
    agg["volume_norm"] = agg["total_volume"] / max_volume
    agg["customer_norm"] = agg["unique_customers"] / max_customers
    agg["popularity_score"] = (
        0.4 * agg["count_norm"] + 0.3 * agg["volume_norm"] + 0.3 * agg["customer_norm"]
    ).clip(0, 1)

    logger.info(
        f"Popularity stats: {len(agg)} STEs | "
        f"mean={agg['popularity_score'].mean():.4f}, "
        f"median={agg['popularity_score'].median():.4f}, "
        f"p90={agg['popularity_score'].quantile(0.9):.4f}"
    )
    return agg


def store_in_redis(agg: pd.DataFrame, redis_url: str = "redis://localhost:6379/0"):
    """Persist popularity scores in Redis HSET for fast ranking lookups."""
    try:
        import redis
        r = redis.from_url(redis_url)
        pipe = r.pipeline()
        for _, row in agg.iterrows():
            pipe.hset("ste_popularity", str(row["ste_id"]), f"{row['popularity_score']:.6f}")
        pipe.execute()
        logger.info(f"Stored {len(agg)} popularity scores in Redis")
    except Exception as e:
        logger.warning(f"Redis not available, skipping: {e}")


def main():
    parser = argparse.ArgumentParser(description="Build popularity scores from contracts")
    parser.add_argument("--contracts-file", required=True)
    parser.add_argument("--output", default=None, help="Optional CSV output path")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--skip-redis", action="store_true")
    args = parser.parse_args()

    agg = compute_popularity(args.contracts_file)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        agg.to_csv(out, index=False)
        logger.info(f"Saved to {out}")
    else:
        default_path = Path(__file__).parent.parent / "app" / "data" / "ste_popularity.csv"
        default_path.parent.mkdir(parents=True, exist_ok=True)
        agg[["ste_id", "popularity_score"]].to_csv(default_path, index=False)
        logger.info(f"Saved to {default_path}")

    if not args.skip_redis:
        store_in_redis(agg, args.redis_url)


if __name__ == "__main__":
    main()
