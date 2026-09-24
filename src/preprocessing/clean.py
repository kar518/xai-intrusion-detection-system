"""clean.py

Stage: Cleaning + binary target creation.

Concrete, non-abstracted steps (no fitted-object/class hierarchy - just functions that run once
over the whole dataset):

  1. Load every CSV in data/raw/, tag each row with source_file = the CSV's filename.
  2. Normalize column names (strip whitespace only - names are not renamed/guessed).
  3. Locate the label column (case-insensitive 'label'); fail loudly if a file doesn't have one.
  4. Coerce every other column to numeric; replace +/-infinity with NaN.
  5. Drop columns that are constant (nunique <= 1) ACROSS THE WHOLE COMBINED DATASET, or that are
     an exact duplicate of an earlier column across the whole combined dataset - i.e. only when
     verified globally, never assumed from a single file. Both are logged by name.
  6. Drop rows where the label itself is missing (can't be used for training or evaluation either way).
  7. Fill remaining NaN with that column's median (computed on the full cleaned dataset at this
     stage - stage-level cleaning, not a train-only fitted preprocessor; re-fitting anything on
     train only happens later at the modelling stage once the split exists).
  8. Remove exact duplicate rows (all columns identical, including source_file - so the same flow
     appearing twice in the SAME file is removed; the same flow legitimately appearing in two
     different capture files is NOT considered a duplicate).
  9. Create Attack: 0 where Label == 'BENIGN' (case-insensitive), else 1. Label itself is preserved
     unmodified alongside it.
 10. Write data/processed/cleaned_data.csv and reports/cleaning_report.json.

Usage:
    python src/preprocessing/clean.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_PATH = ROOT / "reports" / "cleaning_report.json"


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


def find_duplicate_columns(df: pd.DataFrame, exclude: set[str]) -> list[str]:
    """Exact-duplicate-column detection, verified on the full combined dataset."""
    first_by_hash: dict[int, list[str]] = {}
    dupes: list[str] = []
    for c in df.columns:
        if c in exclude:
            continue
        h = int(pd.util.hash_pandas_object(df[c], index=False).sum() % (2**63))
        bucket = first_by_hash.setdefault(h, [])
        if any(df[c].equals(df[other]) for other in bucket):
            dupes.append(c)
        else:
            bucket.append(c)
    return dupes


def load_and_tag(files: list[Path]) -> pd.DataFrame:
    frames = []
    for f in files:
        print(f"Loading {f.name} ...")
        df = read_csv_robust(f)
        df.columns = [str(c).strip() for c in df.columns]
        label_col = find_label_column(list(df.columns))
        if label_col is None:
            raise ValueError(f"{f.name}: no 'Label' column found - columns were {list(df.columns)}")
        if label_col != "Label":
            df = df.rename(columns={label_col: "Label"})
        df["source_file"] = f.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True, sort=False)


def main() -> int:
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSV files found in {RAW_DIR}. Run dataset acquisition first.")
        return 1

    files = sorted(RAW_DIR.glob("*.csv"))
    report: dict = {"source_files": [f.name for f in files]}

    df = load_and_tag(files)
    report["rows_loaded"] = int(len(df))

    protected = {"Label", "source_file"}
    feature_cols = [c for c in df.columns if c not in protected]

    for c in feature_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    numeric_vals = df[feature_cols].to_numpy(dtype="float64")
    report["infinite_values_replaced_with_nan"] = int(np.isinf(numeric_vals).sum())
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    report["nan_values_before_imputation"] = int(df[feature_cols].isna().sum().sum())

    nunique = df[feature_cols].nunique(dropna=True)
    constant_cols = [c for c in feature_cols if nunique[c] <= 1]
    report["dropped_constant_columns"] = constant_cols

    duplicate_cols = find_duplicate_columns(df[feature_cols], exclude=set(constant_cols))
    report["dropped_duplicate_columns"] = duplicate_cols

    drop_cols = set(constant_cols) | set(duplicate_cols)
    kept_feature_cols = [c for c in feature_cols if c not in drop_cols]
    df = df[kept_feature_cols + ["Label", "source_file"]]
    report["kept_feature_columns"] = kept_feature_cols
    report["n_features_before"] = len(feature_cols)
    report["n_features_after"] = len(kept_feature_cols)

    before_label_drop = len(df)
    df = df[df["Label"].notna()].reset_index(drop=True)
    report["rows_dropped_missing_label"] = int(before_label_drop - len(df))

    medians = df[kept_feature_cols].median(numeric_only=True)
    df[kept_feature_cols] = df[kept_feature_cols].fillna(medians)
    report["median_imputation_values"] = {k: float(v) for k, v in medians.items()}

    before_dedup = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    report["duplicate_rows_removed"] = int(before_dedup - len(df))

    df["Attack"] = (df["Label"].astype(str).str.strip().str.lower() != "benign").astype(int)

    report["rows_final"] = int(len(df))
    report["attack_value_counts"] = {int(k): int(v) for k, v in df["Attack"].value_counts().items()}
    report["label_value_counts"] = {str(k): int(v) for k, v in df["Label"].value_counts().items()}
    report["rows_by_source_file"] = {str(k): int(v) for k, v in df["source_file"].value_counts().items()}

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "cleaned_data.csv"
    df.to_csv(out_path, index=False)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"Cleaned dataset written to {out_path}")
    print(f"  Rows: {report['rows_loaded']:,} loaded -> {report['rows_final']:,} final")
    print(f"  Features: {report['n_features_before']} -> {report['n_features_after']} "
          f"(dropped {len(constant_cols)} constant, {len(duplicate_cols)} duplicate)")
    if constant_cols:
        print(f"  Dropped constant columns: {constant_cols}")
    if duplicate_cols:
        print(f"  Dropped duplicate columns: {duplicate_cols}")
    print(f"  Rows dropped (missing label): {report['rows_dropped_missing_label']:,}")
    print(f"  Duplicate rows removed: {report['duplicate_rows_removed']:,}")
    print(f"  Attack value counts: {report['attack_value_counts']}")
    print(f"  Rows by source_file: {report['rows_by_source_file']}")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
