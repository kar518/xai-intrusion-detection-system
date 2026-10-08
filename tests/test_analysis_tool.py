import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analysis_tool.app import app, binary_features


def _one_valid_row():
    source = pd.read_csv(
        "data/processed/test.csv",
        nrows=1,
        low_memory=False,
    )
    return source[["Label", "Attack", *binary_features]]


def test_home_and_schema():
    client = app.test_client()

    home = client.get("/")
    assert home.status_code == 200
    assert b"FlowScope" in home.data

    schema = client.get("/schema")
    assert schema.status_code == 200
    assert len(schema.get_json()["required_features"]) == 65


def test_csv_analysis_returns_prediction_and_explanation():
    client = app.test_client()
    csv_bytes = _one_valid_row().to_csv(index=False).encode("utf-8")

    response = client.post(
        "/analyze-csv",
        data={
            "file": (io.BytesIO(csv_bytes), "flow.csv"),
            "row_limit": "1",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["analysed_rows"] == 1
    assert payload["summary"]["evaluated_rows"] == 1
    assert payload["results"][0]["prediction"] in {"BENIGN", "ATTACK"}
    assert len(payload["results"][0]["shap"]) == 10


def test_csv_analysis_rejects_missing_features():
    client = app.test_client()
    csv_bytes = b"Destination Port,Flow Duration\n80,1000\n"

    response = client.post(
        "/analyze-csv",
        data={"file": (io.BytesIO(csv_bytes), "incomplete.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "missing" in response.get_json()["error"].lower()
