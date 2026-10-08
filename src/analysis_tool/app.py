from __future__ import annotations

import io
import math
from pathlib import Path

import pandas as pd
from flask import Flask, Response, jsonify, render_template, request

from src.app.app import binary_features, predict_flow


ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = ROOT / "data" / "processed" / "test.csv"

MAX_ANALYSIS_ROWS = 100
DEMO_ROWS_PER_LABEL = 2
METADATA_COLUMNS = {"Label", "Attack", "source_file", "actual_label"}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


def _safe_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Values must be finite numbers.")
    return number


def _normalise_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]

    duplicate_columns = frame.columns[frame.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ValueError(
            "CSV contains duplicate columns: "
            + ", ".join(sorted(set(duplicate_columns)))
        )

    missing = [feature for feature in binary_features if feature not in frame.columns]
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "" if len(missing) <= 8 else f" and {len(missing) - 8} more"
        raise ValueError(
            f"CSV is missing {len(missing)} required feature columns: "
            f"{preview}{suffix}."
        )

    for feature in binary_features:
        converted = pd.to_numeric(frame[feature], errors="coerce")
        invalid_count = int(converted.isna().sum())
        if invalid_count:
            raise ValueError(
                f"Column '{feature}' contains {invalid_count} missing or "
                "non-numeric value(s)."
            )
        frame[feature] = converted

    return frame


def _actual_label(row: pd.Series):
    for column in ("Label", "actual_label"):
        if column in row.index and pd.notna(row[column]):
            return str(row[column])

    if "Attack" in row.index and pd.notna(row["Attack"]):
        return "ATTACK" if int(row["Attack"]) == 1 else "BENIGN"

    return None


def _actual_is_attack(row: pd.Series, label):
    if "Attack" in row.index and pd.notna(row["Attack"]):
        return int(row["Attack"]) == 1

    if label is None:
        return None

    return str(label).strip().upper() not in {"BENIGN", "0"}


def analyse_frame(frame: pd.DataFrame, requested_limit: int):
    if frame.empty:
        raise ValueError("CSV does not contain any data rows.")

    frame = _normalise_frame(frame)
    limit = max(1, min(int(requested_limit), MAX_ANALYSIS_ROWS))
    selected = frame.head(limit)

    results = []
    confusion = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    evaluated_rows = 0
    probability_total = 0.0
    attack_type_counts: dict[str, int] = {}

    for position, (_, row) in enumerate(selected.iterrows(), start=1):
        flow = {
            feature: _safe_float(row[feature])
            for feature in binary_features
        }

        prediction = predict_flow(flow)
        label = _actual_label(row)
        actual_attack = _actual_is_attack(row, label)
        predicted_attack = prediction["prediction"] == "ATTACK"

        if actual_attack is not None:
            evaluated_rows += 1
            if actual_attack and predicted_attack:
                confusion["tp"] += 1
            elif actual_attack and not predicted_attack:
                confusion["fn"] += 1
            elif not actual_attack and predicted_attack:
                confusion["fp"] += 1
            else:
                confusion["tn"] += 1

        attack_type = prediction.get("attack_type")
        if attack_type:
            attack_type_counts[attack_type] = attack_type_counts.get(attack_type, 0) + 1

        probability_total += prediction["attack_probability"]

        results.append(
            {
                "row_number": position,
                "actual_label": label,
                "matches_actual": (
                    None
                    if actual_attack is None
                    else actual_attack == predicted_attack
                ),
                **prediction,
            }
        )

    attack_count = sum(
        result["prediction"] == "ATTACK"
        for result in results
    )

    return {
        "summary": {
            "available_rows": int(len(frame)),
            "analysed_rows": len(results),
            "benign_predictions": len(results) - attack_count,
            "attack_predictions": attack_count,
            "mean_attack_probability": probability_total / len(results),
            "evaluated_rows": evaluated_rows,
            "correct_binary_predictions": confusion["tp"] + confusion["tn"],
            "confusion_matrix": confusion,
            "attack_type_counts": attack_type_counts,
        },
        "results": results,
    }


def _demo_frame() -> pd.DataFrame:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test dataset not found: {TEST_FILE}")

    labels = ("BENIGN", "DDoS", "PortScan", "Bot")
    collected = {label: [] for label in labels}

    def collected_count(label):
        return sum(len(part) for part in collected[label])

    for chunk in pd.read_csv(TEST_FILE, chunksize=50000, low_memory=False):
        for label in labels:
            needed = DEMO_ROWS_PER_LABEL - collected_count(label)
            if needed <= 0:
                continue
            matches = chunk[chunk["Label"] == label].head(needed)
            if not matches.empty:
                collected[label].append(matches)

        if all(
            collected_count(label) >= DEMO_ROWS_PER_LABEL
            for label in labels
        ):
            break

    frames = []
    for label in labels:
        if collected[label]:
            frames.append(pd.concat(collected[label]).head(DEMO_ROWS_PER_LABEL))

    if not frames:
        raise ValueError("No demonstration rows were found in the test dataset.")

    return pd.concat(frames, ignore_index=True)


@app.get("/")
def home():
    return render_template(
        "index.html",
        feature_count=len(binary_features),
        max_rows=MAX_ANALYSIS_ROWS,
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "required_features": len(binary_features),
            "maximum_rows": MAX_ANALYSIS_ROWS,
        }
    )


@app.get("/schema")
def schema():
    return jsonify(
        {
            "required_features": binary_features,
            "optional_metadata": sorted(METADATA_COLUMNS),
        }
    )


@app.get("/template.csv")
def template_csv():
    columns = ["Label", *binary_features]
    content = ",".join(columns) + "\n"
    return Response(
        content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=flow-analysis-template.csv"
        },
    )


@app.post("/analyze-csv")
def analyze_csv():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "Choose a CSV file to analyse."}), 400

    try:
        row_limit = int(request.form.get("row_limit", "25"))
        raw = upload.stream.read()
        if not raw:
            raise ValueError("Uploaded CSV is empty.")

        frame = pd.read_csv(io.BytesIO(raw), low_memory=False)
        return jsonify(analyse_frame(frame, row_limit))
    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as error:
        return jsonify({"error": f"Unable to read CSV: {error}"}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.post("/analyze-demo")
def analyze_demo():
    try:
        frame = _demo_frame()
        return jsonify(analyse_frame(frame, len(frame)))
    except Exception as error:
        return jsonify({"error": str(error)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
