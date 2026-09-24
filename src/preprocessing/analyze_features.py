"""analyze_features.py

Stage: Feature analysis.

For every CSV in data/raw/, computes real descriptive statistics (min, max, mean, std, number of
distinct values) for every numeric column, and flags columns that are constant (nunique <= 1) or
whose values look suspicious (all-zero, single dominant value >99% of rows). Also flags any
non-numeric column other than the label column, since that usually signals an identifier or a
parsing problem, not a real feature.

Writes reports/feature_analysis.json.

Usage:
    python src/preprocessing/analyze_features.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "reports" / "feature_analysis.json"


def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, low_memory=False, encoding="latin-1")


def find_label_column(columns: list[str]) -> str | None:
    for c in columns:
        if c.strip().lower() == "label":
            return c
    return None


def analyze_file(path: Path) -> dict:
    print(f"Analyzing features in {path.name} ...")
    df = read_csv_robust(path)
    df.columns = [str(c).strip() for c in df.columns]
    label_col = find_label_column(list(df.columns))
    feature_cols = [c for c in df.columns if c != label_col]

    numeric_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric_cols = [c for c in feature_cols if c not in numeric_cols]

    stats = {}
    constant_columns = []
    dominant_value_columns = {}
    for c in numeric_cols:
        col = df[c].replace([np.inf, -np.inf], np.nan)
        nunique = int(df[c].nunique(dropna=True))
        desc = {
            "min": None if col.dropna().empty else float(col.min()),
            "max": None if col.dropna().empty else float(col.max()),
            "mean": None if col.dropna().empty else float(col.mean()),
            "std": None if col.dropna().empty else float(col.std()),
            "n_unique": nunique,
        }
        stats[c] = desc
        if nunique <= 1:
            constant_columns.append(c)
        else:
            top_share = df[c].value_counts(normalize=True, dropna=True).iloc[0]
            if top_share > 0.99:
                dominant_value_columns[c] = float(top_share)

    return {
        "filename": path.name,
        "label_column": label_col,
        "n_numeric_features": len(numeric_cols),
        "n_non_numeric_columns_excluding_label": len(non_numeric_cols),
        "non_numeric_columns_excluding_label": non_numeric_cols,
        "constant_columns": constant_columns,
        "columns_with_dominant_single_value_over_99pct": dominant_value_columns,
        "numeric_feature_stats": stats,
    }


def main() -> int:
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSV files found in {RAW_DIR}.")
        return 1

    files = sorted(RAW_DIR.glob("*.csv"))
    results = [analyze_file(f) for f in files]

    constant_everywhere = set(results[0]["constant_columns"]) if results else set()
    for r in results[1:]:
        constant_everywhere &= set(r["constant_columns"])

    report = {
        "n_files": len(results),
        "files": results,
        "columns_constant_in_every_file": sorted(constant_everywhere),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    for r in results:
        print(f"\n  {r['filename']}")
        print(f"    numeric features: {r['n_numeric_features']}")
        if r["non_numeric_columns_excluding_label"]:
            print(f"    non-numeric columns (excl. label): {r['non_numeric_columns_excluding_label']}")
        if r["constant_columns"]:
            print(f"    constant columns: {r['constant_columns']}")
        if r["columns_with_dominant_single_value_over_99pct"]:
            print(f"    >99% single-value columns: "
                  f"{list(r['columns_with_dominant_single_value_over_99pct'].keys())}")
    if constant_everywhere:
        print(f"\n  Columns constant in EVERY file (candidates to drop in clean.py): "
              f"{sorted(constant_everywhere)}")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
