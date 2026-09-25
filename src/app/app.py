import sys
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request, render_template
from src.threat_analysis.analyzer import analyze_threat

ROOT = Path(__file__).resolve().parents[2]

# Make `xai.*` importable no matter how the app is launched
# (python src/app/app.py, python -m src.app.app, flask run, ...).
SRC_DIR = ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from xai.shap_explainer import SHAPExplainer  # noqa: E402

MODEL_DIR = ROOT / "models"
TEST_FILE = ROOT / "data" / "processed" / "test.csv"

BINARY_MODEL_FILE = MODEL_DIR / "random_forest_binary.joblib"
BINARY_FEATURE_FILE = MODEL_DIR / "random_forest_binary.features.json"
ATTACK_MODEL_FILE = MODEL_DIR / "attack_random_forest.joblib"


app = Flask(__name__)


# ---------------------------------------------------------------------
# LOAD MODELS
# ---------------------------------------------------------------------

print("Loading IDS models...")

binary_model = joblib.load(BINARY_MODEL_FILE)

feature_data = pd.read_json(BINARY_FEATURE_FILE)
binary_features = feature_data["feature_columns"].tolist()

attack_artifact = joblib.load(ATTACK_MODEL_FILE)

attack_model = attack_artifact["model"]
attack_features = attack_artifact["features"]


# ---------------------------------------------------------------------
# LOAD SHAP
# ---------------------------------------------------------------------

print("Loading SHAP explainer...")

binary_shap_explainer = SHAPExplainer(
    BINARY_MODEL_FILE
)

print("SHAP explainer loaded.")


print("Models loaded.")
print(f"Binary features: {len(binary_features)}")
print(f"Attack features: {len(attack_features)}")


# ---------------------------------------------------------------------
# FEATURE PREPARATION
# ---------------------------------------------------------------------

def prepare_features(flow, features):

    missing = [
        feature
        for feature in features
        if feature not in flow
    ]

    if missing:
        raise ValueError(
            f"Missing required features: {missing}"
        )

    values = {
        feature: flow[feature]
        for feature in features
    }

    return pd.DataFrame(
        [values],
        columns=features,
    )


# ---------------------------------------------------------------------
# IDS PREDICTION
# ---------------------------------------------------------------------

def predict_flow(flow):

    # -------------------------------------------------------------
    # STAGE 1: BENIGN / ATTACK
    # -------------------------------------------------------------

    X_binary = prepare_features(
        flow,
        binary_features,
    )

    binary_prediction = binary_model.predict(
        X_binary
    )[0]

    binary_probabilities = (
        binary_model.predict_proba(X_binary)[0]
    )

    classes = list(binary_model.classes_)

    probability_map = dict(
        zip(
            classes,
            binary_probabilities,
        )
    )

    attack_probability = probability_map.get(
        1,
        0.0,
    )

    result = {
        "prediction": (
            "ATTACK"
            if binary_prediction == 1
            else "BENIGN"
        ),

        "binary_confidence": float(
            max(binary_probabilities)
        ),

        "attack_probability": float(
            attack_probability
        ),
    }

    # -------------------------------------------------------------
    # SHAP EXPLANATION (contributions toward the ATTACK class)
    # -------------------------------------------------------------
    #
    # Positive shap_value  -> pushes the flow toward ATTACK
    # Negative shap_value  -> pushes the flow toward BENIGN
    #
    # Explained for BENIGN flows too, so the dashboard can show why a
    # flow was NOT flagged.

    try:

        shap_explanation = (
            binary_shap_explainer.explain(
                X_binary,
                top_n=10,
                target_class=1,
            )[0]
        )

        result["shap"] = [
            {
                "feature": item["feature"],
                "shap_value": float(
                    item["shap_value"]
                ),
                "feature_value": float(
                    item["feature_value"]
                ),
            }
            for item in shap_explanation["features"]
        ]

        result["shap_base_value"] = float(
            shap_explanation["base_value"]
        )

    except Exception as error:

        # Never let an explanation failure break the prediction.
        print(f"SHAP explanation failed: {error!r}")

        result["shap"] = []
        result["shap_error"] = str(error)

    # -------------------------------------------------------------
    # STAGE 2: ATTACK TYPE
    # -------------------------------------------------------------

    if binary_prediction == 1:

        X_attack = prepare_features(
            flow,
            attack_features,
        )

        attack_prediction = attack_model.predict(
            X_attack
        )[0]

        attack_probabilities = (
            attack_model.predict_proba(
                X_attack
            )[0]
        )

        attack_classes = list(
            attack_model.classes_
        )

        attack_probability_map = dict(
            zip(
                attack_classes,
                attack_probabilities,
            )
        )

        result["attack_type"] = str(
            attack_prediction
        )

        result["attack_confidence"] = float(
            max(attack_probabilities)
        )

        result["attack_probabilities"] = {
            str(label): float(probability)
            for label, probability
            in attack_probability_map.items()
        }

        result["threat_analysis"] = analyze_threat(
            str(attack_prediction)
        )

    return result


# ---------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------

@app.get("/")
def home():

    return render_template(
        "index.html"
    )


@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "binary_model": True,
        "attack_classifier": True,
        "shap": True,
        "binary_features": len(
            binary_features
        ),
        "attack_features": len(
            attack_features
        ),
    })


@app.post("/predict")
def predict():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": (
                "Request body must contain JSON."
            )
        }), 400

    try:

        result = predict_flow(data)

        return jsonify(result)

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ---------------------------------------------------------------------
# REAL CICIDS2017 DEMO FLOW
# ---------------------------------------------------------------------

@app.get("/demo")
def demo():

    label = request.args.get(
        "label",
        "DDoS",
    )

    valid_labels = {
        "DDoS",
        "PortScan",
        "Bot",
    }

    if label not in valid_labels:

        return jsonify({
            "error": (
                "Invalid label. Choose from: "
                f"{sorted(valid_labels)}"
            )
        }), 400

    if not TEST_FILE.exists():

        return jsonify({
            "error": (
                f"Test dataset not found: "
                f"{TEST_FILE}"
            )
        }), 500

    try:

        for chunk in pd.read_csv(
            TEST_FILE,
            chunksize=50000,
            low_memory=False,
        ):

            matches = chunk[
                chunk["Label"] == label
            ]

            if matches.empty:
                continue

            row = matches.iloc[0]

            actual_label = str(
                row["Label"]
            )

            metadata_columns = {
                "Label",
                "Attack",
                "source_file",
            }

            flow = row.drop(
                labels=[
                    column
                    for column in metadata_columns
                    if column in row.index
                ]
            )

            flow = {
                str(key): float(value)
                for key, value in flow.items()
            }

            return jsonify({
                "actual_label": actual_label,
                "flow": flow,
            })

        return jsonify({
            "error": (
                f"No {label} samples found."
            )
        }), 404

    except Exception as error:

        return jsonify({
            "error": str(error)
        }), 500


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )