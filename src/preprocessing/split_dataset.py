"""split_dataset.py

Stage: Train/test split.

Tries a SOURCE/DAY-BASED split: if every row's source_file can be mapped to a day of the week
(by finding a weekday name as a substring of the filename, case-insensitive), rows from
Monday-Thursday become the training set and rows from Friday become the test set. This tests
whether the detector generalizes to a different day's traffic, not just a random subset of the
same day.

If ANY source_file cannot be mapped to a weekday, this script does NOT guess. It prints the
exact set of source_file values it found and which ones failed to match a weekday, and exits
without writing train/test files - it is a genuine decision point: you may need to enable a
different split rule (e.g. if this dataset's files are organized by attack type rather than day).

Usage:
    python src/preprocessing/split_dataset.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
CLEANED_PATH = PROCESSED_DIR / "cleaned_data.csv"
REPORT_PATH = ROOT / "reports" / "split_report.json"

TRAIN_DAYS = {"monday", "tuesday", "wednesday", "thursday"}
TEST_DAYS = {"friday"}
ALL_DAYS = TRAIN_DAYS | TEST_DAYS


def detect_day(filename: str) -> str | None:
    name = filename.lower()
    for day in ALL_DAYS:
        if re.search(rf"\b{day}\b", name) or day in name:
            return day
    return None


def main() -> int:
    if not CLEANED_PATH.exists():
        print(f"{CLEANED_PATH} not found. Run clean.py first.")
        return 1

    print(f"Loading {CLEANED_PATH} ...")
    df = pd.read_csv(CLEANED_PATH, low_memory=False)

    source_files = sorted(df["source_file"].unique().tolist())
    day_by_file = {f: detect_day(f) for f in source_files}
    unmatched = [f for f, d in day_by_file.items() if d is None]

    report = {"source_files": source_files, "detected_day_by_file": day_by_file}

    if unmatched:
        report["status"] = "DECISION_NEEDED"
        report["unmatched_files"] = unmatched
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

        print(f"\n{'=' * 70}")
        print("DECISION NEEDED: could not detect a weekday for every source_file.")
        print(f"\nAll source_file values found in the cleaned dataset:")
        for f in source_files:
            print(f"    {f}  -> day: {day_by_file[f]}")
        print(f"\nFiles with NO detected weekday: {unmatched}")
        print(
            "\nThis dataset's filenames don't (at least not all) encode a day of the week the way "
            "the original CICIDS2017 'MachineLearningCVE' files do (e.g. "
            "'Monday-WorkingHours.pcap_ISCX.csv'). Before I write a train/test split I need you to "
            "tell me the actual naming/organization scheme (paste the source_file list above if "
            "it's not obvious from what's printed) so the split logic matches what's really in the "
            "files - guessing here would silently produce a meaningless train/test split."
        )
        print(f"\nPartial report written to: {REPORT_PATH}")
        return 2

    df["day"] = df["source_file"].map(day_by_file)
    train_df = df[df["day"].isin(TRAIN_DAYS)].drop(columns=["day"])
    test_df = df[df["day"].isin(TEST_DAYS)].drop(columns=["day"])

    if train_df.empty or test_df.empty:
        report["status"] = "DECISION_NEEDED"
        report["reason"] = "Day mapping succeeded but produced an empty train or test set."
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nDECISION NEEDED: train rows={len(train_df)}, test rows={len(test_df)} - "
              f"one side is empty. Detected days per file: {day_by_file}")
        return 2

    train_path = PROCESSED_DIR / "train.csv"
    test_path = PROCESSED_DIR / "test.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    report["status"] = "OK"
    report["train_rows"] = int(len(train_df))
    report["test_rows"] = int(len(test_df))
    report["train_attack_counts"] = {int(k): int(v) for k, v in train_df["Attack"].value_counts().items()}
    report["test_attack_counts"] = {int(k): int(v) for k, v in test_df["Attack"].value_counts().items()}
    report["test_label_counts"] = {str(k): int(v) for k, v in test_df["Label"].value_counts().items()}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    print(f"Day-based split written.")
    print(f"  Train (Mon-Thu): {len(train_df):,} rows -> {train_path}")
    print(f"  Test  (Fri):     {len(test_df):,} rows -> {test_path}")
    print(f"  Train Attack counts: {report['train_attack_counts']}")
    print(f"  Test Attack counts:  {report['test_attack_counts']}")
    print(f"  Test Label breakdown: {report['test_label_counts']}")
    print(f"\nFull report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
