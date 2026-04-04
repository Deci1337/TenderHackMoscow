"""Load real STE and Contracts data into PostgreSQL."""
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "backend" / "app" / "data"


def find_csvs() -> tuple[str, str]:
    """Return (ste_path, contracts_path) by detecting column count."""
    import csv
    results = []
    for fname in os.listdir(DATA_DIR):
        if not fname.lower().endswith(".csv"):
            continue
        fpath = str(DATA_DIR / fname)
        with open(fpath, "r", encoding="utf-8-sig", errors="replace") as f:
            row = next(csv.reader(f, delimiter=";"), [])
        ncols = len(row)
        log.info("  %s  %.1f MB  %d cols", fname, os.path.getsize(fpath) / 1e6, ncols)
        results.append((ncols, fpath))

    ste_file = next((p for n, p in results if n == 4), None)
    contracts_file = next((p for n, p in results if n >= 10), None)

    if not ste_file:
        raise RuntimeError("STE file (4 columns) not found")
    if not contracts_file:
        raise RuntimeError("Contracts file (10+ columns) not found")

    return ste_file, contracts_file


async def main():
    from scripts.load_data import load_ste, load_contracts, build_ml_indexes
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.config import settings

    log.info("Detecting data files...")
    ste_file, contracts_file = find_csvs()
    log.info("STE:       %s", ste_file)
    log.info("Contracts: %s", contracts_file)

    # Patch pandas to use UTF-8-SIG for these large Russian files
    import pandas as pd
    _orig = pd.read_csv
    def _patched(fp, **kw):
        if isinstance(fp, str) and fp.endswith(".csv"):
            kw.setdefault("encoding", "utf-8-sig")
            kw.setdefault("encoding_errors", "replace")
        return _orig(fp, **kw)
    pd.read_csv = _patched

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        log.info("Loading STE (may take several minutes)...")
        await load_ste(session, ste_file)

    async with Session() as session:
        log.info("Loading Contracts (may take several minutes)...")
        await load_contracts(session, contracts_file)

    log.info("Building search indexes (tsvector + popularity)...")
    async with Session() as session:
        await build_ml_indexes(session)

    await engine.dispose()
    log.info("All done!")


if __name__ == "__main__":
    asyncio.run(main())
