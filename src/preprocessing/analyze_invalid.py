"""analyze_invalid.py

Stage: Invalid-value analysis (NaN / +inf / -inf), per column, per file.

Writes reports/invalid_analysis.json.

Usage:
    python src/preprocessing/analyze_invalid.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "reports" / "invalid_analysis.json"


def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1")


def analyze_file(path: Path) -> dict:
    print(f"Checking invalid values in {path.name} ...")
    df = read_csv_robust(path)
    df.columns = [str(c).strip() for c in df.columns]

    nan_by_col = {c: int(n) for c, n in df.isna().sum().items() if n > 0}

    numeric_df = df.select_dtypes(include=[np.number])
    pos_inf_by_col, neg_inf_by_col = {}, {}
    if not numeric_df.empty:
        arr = numeric_df.to_numpy()
        pos_inf = np.isposinf(arr)
        neg_inf = np.isneginf(arr)
        for i, c in enumerate(numeric_df.columns):
            p, n = int(pos_inf[:, i].sum()), int(neg_inf[:, i].sum())
            if p:
                pos_inf_by_col[c] = p
            if n:
                neg_inf_by_col[c] = n

    return {
        "filename": path.name,
        "row_count": int(len(df)),
        "nan_values_by_column": nan_by_col,
        "nan_values_total": int(sum(nan_by_col.values())),
        "positive_infinity_by_column": pos_inf_by_col,
        "negative_infinity_by_column": neg_inf_by_col,
        "infinity_values_total": int(sum(pos_inf_by_col.values()) + sum(neg_inf_by_col.values())),
    }


def main() -> int:
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSV files found in {RAW_DIR}.")
        return 1

    files = sorted(RAW_DIR.glob("*.csv"))
    results = [analyze_file(f) for f in files]

    report = {
        "n_files": len(results),
        "files": results,
        "total_nan_values": sum(r["nan_values_total"] for r in results),
        "total_infinity_values": sum(r["infinity_values_total"] for r in results),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    for r in results:
        print(f"\n  {r['filename']}  (rows={r['row_count']:,})")
        print(f"    NaN total: {r['nan_values_total']:,}"
              + (f"  by column: {r['nan_values_by_column']}" if r["nan_values_by_column"] else ""))
        print(f"    +inf total: {sum(r['positive_infinity_by_column'].values()):,}"
              + (f"  by column: {r['positive_infinity_by_column']}" if r["positive_infinity_by_column"] else ""))
        print(f"    -inf total: {sum(r['negative_infinity_by_column'].values()):,}"
              + (f"  by column: {r['negative_infinity_by_column']}" if r["negative_infinity_by_column"] else ""))
    print(f"\n  TOTAL across all files: {report['total_nan_values']:,} NaN, "
          f"{report['total_infinity_values']:,} infinite values")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
