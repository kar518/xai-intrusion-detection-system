from pathlib import Path

import joblib
import pandas as pd
import shap


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models"


class SHAPExplainer:
    """SHAP explanations for the project's Random Forest IDS models."""

    def __init__(self, model_path: Path):
        artifact = joblib.load(model_path)

        # The binary model was saved directly as a RandomForestClassifier,
        # while the attack-type model was saved inside an artifact dictionary.
        if isinstance(artifact, dict):
            self.model = artifact["model"]
            self.features = artifact["features"]
        else:
            self.model = artifact

            # Binary training script stores its feature list separately.
            feature_file = model_path.with_suffix(".features.json")

            if not feature_file.exists():
                raise FileNotFoundError(
                    f"Feature list not found: {feature_file}"
                )

            import json

            feature_data = json.loads(
                feature_file.read_text(encoding="utf-8")
            )

            self.features = feature_data["feature_columns"]

        self.explainer = shap.TreeExplainer(self.model)

    def prepare_input(self, flow: pd.DataFrame) -> pd.DataFrame:
        """Return input with exactly the features used during training."""

        missing = [
            feature
            for feature in self.features
            if feature not in flow.columns
        ]

        if missing:
            raise ValueError(
                "Input flow is missing required features:\n"
                + "\n".join(f"  - {feature}" for feature in missing)
            )

        return flow[self.features].copy()

    def explain(self, flow: pd.DataFrame, top_n: int = 10):
        """
        Generate SHAP explanations for one or more flows.

        For classification models, select the SHAP values corresponding
        to the model's predicted class.
        """

        X = self.prepare_input(flow)

        shap_values = self.explainer.shap_values(X)
        predictions = self.model.predict(X)

        # SHAP output format differs between versions.
        #
        # Possible formats include:
        #   list[class] -> (samples, features)
        #   ndarray -> (samples, features, classes)
        #   ndarray -> (samples, features)
        #
        # Normalize this into:
        #   (samples, features)
        if isinstance(shap_values, list):
            values = []

            for i, prediction in enumerate(predictions):
                class_index = list(self.model.classes_).index(prediction)
                values.append(shap_values[class_index][i])

            values = pd.DataFrame(values).to_numpy()

        else:
            values = shap_values

            if values.ndim == 3:
                # Current SHAP format:
                # samples x features x classes
                selected = []

                class_indices = {
                    label: index
                    for index, label in enumerate(self.model.classes_)
                }

                for i, prediction in enumerate(predictions):
                    class_index = class_indices[prediction]
                    selected.append(values[i, :, class_index])

                values = pd.DataFrame(selected).to_numpy()

            elif values.ndim != 2:
                raise ValueError(
                    f"Unexpected SHAP value shape: {values.shape}"
                )

        results = []

        for i in range(len(X)):
            row_values = values[i]

            ranking = sorted(
                zip(self.features, row_values),
                key=lambda item: abs(float(item[1])),
                reverse=True,
            )[:top_n]

            results.append(
                {
                    "prediction": predictions[i],
                    "features": [
                        {
                            "feature": feature,
                            "shap_value": float(value),
                            "feature_value": float(X.iloc[i][feature]),
                        }
                        for feature, value in ranking
                    ],
                }
            )

        return results

    def global_importance(self, flow: pd.DataFrame) -> pd.DataFrame:
        """Calculate mean absolute SHAP importance."""

        X = self.prepare_input(flow)

        shap_values = self.explainer.shap_values(X)
        predictions = self.model.predict(X)

        # Normalize SHAP output to:
        # samples x features
        if isinstance(shap_values, list):
            selected = []

            class_indices = {
                label: index
                for index, label in enumerate(self.model.classes_)
            }

            for i, prediction in enumerate(predictions):
                class_index = class_indices[prediction]
                selected.append(shap_values[class_index][i])

            values = pd.DataFrame(selected).to_numpy()

        else:
            values = shap_values

            if values.ndim == 3:
                selected = []

                class_indices = {
                    label: index
                    for index, label in enumerate(self.model.classes_)
                }

                for i, prediction in enumerate(predictions):
                    class_index = class_indices[prediction]
                    selected.append(values[i, :, class_index])

                values = pd.DataFrame(selected).to_numpy()

            elif values.ndim != 2:
                raise ValueError(
                    f"Unexpected SHAP value shape: {values.shape}"
                )

        importance = abs(values).mean(axis=0)

        result = pd.DataFrame(
            {
                "feature": self.features,
                "mean_abs_shap": importance,
            }
        )

        return result.sort_values(
            "mean_abs_shap",
            ascending=False,
        ).reset_index(drop=True)


def main():
    binary_model = MODEL_DIR / "random_forest_binary.joblib"
    attack_model = MODEL_DIR / "attack_random_forest.joblib"

    print("Loading models...")

    binary_explainer = SHAPExplainer(binary_model)
    attack_explainer = SHAPExplainer(attack_model)

    print("SHAP explainers created successfully.")

    test_file = ROOT / "data" / "processed" / "test.csv"

    print("Loading a real attack sample...")

    df = pd.read_csv(
        test_file,
        low_memory=False,
    )

    attack = df[df["Attack"] == 1].head(1)

    flow = attack.drop(
        columns=[
            column
            for column in ["Label", "Attack", "source_file"]
            if column in attack.columns
        ]
    )

    print("\nActual label:")
    print(attack["Label"].iloc[0])

    print("\nBinary SHAP explanation:")

    explanation = binary_explainer.explain(
        flow,
        top_n=10,
    )[0]

    for item in explanation["features"]:
        direction = "toward ATTACK" if item["shap_value"] > 0 else "toward BENIGN"

        print(
            f"  {item['feature']:<35} "
            f"SHAP={item['shap_value']:>12.6f} "
            f"value={item['feature_value']:<15g} "
            f"({direction})"
        )

    print("\nGlobal binary feature importance:")

    global_importance = binary_explainer.global_importance(
        df.drop(
            columns=[
                column
                for column in ["Label", "Attack", "source_file"]
                if column in df.columns
            ]
        ).sample(
            n=min(5000, len(df)),
            random_state=42,
        )
    )

    print(global_importance.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
