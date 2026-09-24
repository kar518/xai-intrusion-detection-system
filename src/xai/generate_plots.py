from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import shap


ROOT = Path(__file__).resolve().parents[2]

DATA_FILE = ROOT / "data" / "processed" / "test.csv"
MODEL_FILE = ROOT / "models" / "random_forest_binary.joblib"
FEATURE_FILE = ROOT / "models" / "random_forest_binary.features.json"
OUTPUT_DIR = ROOT / "reports" / "figures"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model...")
    model = joblib.load(MODEL_FILE)

    print("Loading feature list...")
    feature_data = pd.read_json(FEATURE_FILE)
    features = feature_data["feature_columns"].tolist()

    print("Loading attack sample...")
    df = pd.read_csv(DATA_FILE, low_memory=False)

    attack = df[df["Attack"] == 1].iloc[[0]]
    X = attack[features]

    print("Creating SHAP explainer...")
    explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X)

    # SHAP 0.52 can return different shapes depending on model/output.
    if isinstance(shap_values, list):
        values = shap_values[1][0]
    else:
        values = shap_values

        if values.ndim == 3:
            values = values[0, :, 1]
        elif values.ndim == 2:
            values = values[0]

    explanation = shap.Explanation(
        values=values,
        base_values=explainer.expected_value[1]
        if hasattr(explainer.expected_value, "__len__")
        else explainer.expected_value,
        data=X.iloc[0].values,
        feature_names=features,
    )

    print("Generating waterfall plot...")
    plt.figure()
    shap.plots.waterfall(
        explanation,
        max_display=15,
        show=False,
    )
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "shap_waterfall_attack.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    print("Generating local bar plot...")
    plt.figure()
    shap.plots.bar(
        explanation,
        max_display=15,
        show=False,
    )
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "shap_local_bar.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    print("Generating global importance...")
    background = df[features].sample(
        n=min(1000, len(df)),
        random_state=42,
    )

    global_values = explainer.shap_values(background)

    if isinstance(global_values, list):
        global_values = global_values[1]
    elif global_values.ndim == 3:
        global_values = global_values[:, :, 1]

    importance = pd.DataFrame({
        "feature": features,
        "importance": abs(global_values).mean(axis=0),
    }).sort_values(
        "importance",
        ascending=False,
    )

    top = importance.head(15).sort_values("importance")

    plt.figure(figsize=(10, 7))
    plt.barh(
        top["feature"],
        top["importance"],
    )
    plt.xlabel("Mean |SHAP value|")
    plt.title("Global SHAP Feature Importance")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "shap_global_importance.png",
        dpi=200,
        bbox_inches="tight",
    )
    plt.close()

    importance.to_csv(
        ROOT / "reports" / "shap_global_importance.csv",
        index=False,
    )

    print()
    print("=" * 70)
    print("SHAP VISUALIZATIONS COMPLETE")
    print("=" * 70)
    print(f"Waterfall:       {OUTPUT_DIR / 'shap_waterfall_attack.png'}")
    print(f"Local bar:       {OUTPUT_DIR / 'shap_local_bar.png'}")
    print(f"Global importance: {OUTPUT_DIR / 'shap_global_importance.png'}")
    print(f"Importance CSV:  {ROOT / 'reports' / 'shap_global_importance.csv'}")


if __name__ == "__main__":
    main()
