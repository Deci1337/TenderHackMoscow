import csv, os, sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "backend" / "app" / "data"

# Force UTF-8 output
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for fname in os.listdir(DATA_DIR):
    if not fname.endswith(".csv"):
        continue
    fpath = DATA_DIR / fname

    # Try different encodings
    for enc in ("cp1251", "utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(fpath, "r", encoding=enc, errors="replace") as f:
                reader = csv.reader(f, delimiter=";")
                rows = [next(reader, None) for _ in range(3)]
            print(f"\nFILE: {fpath.name}  ({fpath.stat().st_size/1e6:.1f} MB)  encoding={enc}")
            for i, row in enumerate(rows):
                if row:
                    print(f"  row{i} ({len(row)} cols): {[str(x)[:50] for x in row[:5]]}")
            break
        except Exception as e:
            print(f"  {enc} failed: {e}")
