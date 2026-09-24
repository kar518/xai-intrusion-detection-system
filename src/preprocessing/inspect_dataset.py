"""inspect_dataset.py

Stage: Dataset inspection.

Reads every CSV in data/raw/, and for each file reports: filename, row count, column count,
exact column names (whitespace-stripped only, nothing renamed), dtypes as pandas inferred them,
and an attempt to locate the label column (case-insensitive match on 'label'). Makes no
assumptions about which other columns exist.

Writes reports/inspection_report.json and prints a human-readable summary.

Usage:
    python src/preprocessing/inspect_dataset.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "reports" / "inspection_report.json"


def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        print(f"  {path.name}: not UTF-8, retrying as latin-1")
        return pd.read_csv(path, low_memory=False, encoding="latin-1")


def find_label_column(columns: list[str]) -> str | None:
    for c in columns:
        if c.strip().lower() == "label":
            return c
    return None


def inspect_file(path: Path) -> dict:
    print(f"Inspecting {path.name} ...")
    df = read_csv_robust(path)
    df.columns = [str(c).strip() for c in df.columns]
    label_col = find_label_column(list(df.columns))
    info = {
        "filename": path.name,
        "size_bytes": path.stat().st_size,
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "column_names": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "label_column_found": label_col,
    }
    if label_col is not None:
        counts = df[label_col].astype(str).value_counts()
        info["unique_label_values"] = sorted(counts.index.tolist())
        info["label_value_counts"] = {str(k): int(v) for k, v in counts.items()}
    else:
        info["warning"] = "No column named 'Label' (case-insensitive) found in this file."
    return info


def main() -> int:
    if not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")):
        print(f"No CSV files found in {RAW_DIR}. Copy the dataset there first.")
        return 1

    files = sorted(RAW_DIR.glob("*.csv"))
    results = [inspect_file(f) for f in files]

    all_columns = sorted({c for r in results for c in r["column_names"]})
    columns_not_in_every_file = sorted(
        c for c in all_columns if not all(c in r["column_names"] for r in results)
    )
    label_columns_found = {r["filename"]: r["label_column_found"] for r in results}
    total_rows = sum(r["row_count"] for r in results)

    report = {
        "n_files": len(results),
        "total_rows": total_rows,
        "files": results,
        "columns_not_present_in_every_file": columns_not_in_every_file,
        "label_column_by_file": label_columns_found,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"Inspected {len(results)} file(s), {total_rows:,} total rows.")
    for r in results:
        print(f"\n  {r['filename']}")
        print(f"    rows={r['row_count']:,}  columns={r['column_count']}")
        print(f"    label column: {r['label_column_found']!r}")
        if "unique_label_values" in r:
            print(f"    unique labels: {r['unique_label_values']}")
    if columns_not_in_every_file:
        print(f"\n  WARNING: columns not present in every file: {columns_not_in_every_file}")
    else:
        print("\n  All files share an identical column set.")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
