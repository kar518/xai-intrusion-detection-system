"""count_invalid_rows.py

Stage: Invalid-ROW counting (distinct from analyze_invalid.py, which counts invalid VALUES
per column). This script reports, per file: how many entire rows contain at least one NaN or
infinite value, and how many rows are exact duplicates of another row in the same file - these
are the numbers that actually determine how much data cleaning will remove.

Writes reports/invalid_row_counts.json.

Usage:
    python src/preprocessing/count_invalid_rows.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "reports" / "invalid_row_counts.json"


def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1")


def count_file(path: Path) -> dict:
    print(f"Counting invalid rows in {path.name} ...")
    df = read_csv_robust(path)
    df.columns = [str(c).strip() for c in df.columns]

    numeric_df = df.select_dtypes(include=[np.number])
    has_nan_row = df.isna().any(axis=1)
    has_inf_row = pd.Series(False, index=df.index)
    if not numeric_df.empty:
        inf_mask = np.isinf(numeric_df.to_numpy())
        has_inf_row = pd.Series(inf_mask.any(axis=1), index=df.index)

    invalid_row_mask = has_nan_row | has_inf_row
    duplicate_row_mask = df.duplicated(keep="first")

    return {
        "filename": path.name,
        "row_count": int(len(df)),
        "rows_with_nan": int(has_nan_row.sum()),
        "rows_with_infinity": int(has_inf_row.sum()),
        "rows_with_any_invalid_value": int(invalid_row_mask.sum()),
        "duplicate_rows": int(duplicate_row_mask.sum()),
        "rows_invalid_or_duplicate": int((invalid_row_mask | duplicate_row_mask).sum()),
        "pct_rows_affected": round(100 * float((invalid_row_mask | duplicate_row_mask).mean()), 3),
    }


def main() -> int:
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSV files found in {RAW_DIR}.")
        return 1

    files = sorted(RAW_DIR.glob("*.csv"))
    results = [count_file(f) for f in files]

    total_rows = sum(r["row_count"] for r in results)
    total_invalid_or_dup = sum(r["rows_invalid_or_duplicate"] for r in results)
    report = {
        "n_files": len(results),
        "files": results,
        "total_rows": total_rows,
        "total_rows_invalid_or_duplicate": total_invalid_or_dup,
        "pct_of_dataset_affected": round(100 * total_invalid_or_dup / total_rows, 3) if total_rows else 0.0,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    for r in results:
        print(f"\n  {r['filename']}  (rows={r['row_count']:,})")
        print(f"    rows with NaN: {r['rows_with_nan']:,}   rows with infinity: {r['rows_with_infinity']:,}")
        print(f"    duplicate rows: {r['duplicate_rows']:,}")
        print(f"    total affected: {r['rows_invalid_or_duplicate']:,} ({r['pct_rows_affected']}%)")
    print(f"\n  DATASET TOTAL: {total_rows:,} rows, {total_invalid_or_dup:,} affected "
          f"({report['pct_of_dataset_affected']}%)")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
