# FlowScope Offline Analysis Tool

FlowScope is a separate application that turns the project into a practical
offline analysis tool. It does not change or replace the original demonstration
dashboard.

## Start the application

From the repository root:

```bash
source .venv/bin/activate
flask --app src.analysis_tool.app run --port 5001
```

Open <http://127.0.0.1:5001>.

The original dashboard remains available separately on port 5000 when started
with `flask --app src.app.app run`.

## Analyse a CSV

The CSV must contain all 65 numerical feature columns used by the binary model.
Column names must match the names in `models/random_forest_binary.features.json`.

Optional columns:

- `Label` - the CICIDS attack label or `BENIGN`
- `Attack` - binary ground truth (`0` for benign, `1` for attack)
- `source_file` - retained as metadata and not given to the models
- `actual_label` - an alternative ground-truth label column

When ground truth is supplied, the page calculates binary correctness and a
small confusion matrix for the analysed rows. Without ground truth, it still
returns predictions, probabilities, SHAP explanations and threat guidance.

For responsiveness, one request analyses at most 100 rows. This is intentional:
the application creates a local SHAP explanation for every selected flow.

Use **Download column template** to obtain the required header. Use **Run mixed
demo batch** to analyse two real test flows from each of the BENIGN, DDoS,
PortScan and Bot labels without uploading a file.

## What the tool displays

- Batch totals and mean attack probability
- Ground-truth comparison when labels are supplied
- One result row per flow
- Stage 1 prediction and confidence
- Stage 2 attack type for detected attacks
- Threat severity and mitigation
- Top ten local SHAP contributions for any selected row

## Scope

This remains an offline flow-analysis tool. It accepts already-extracted
CICIDS-compatible features; it does not capture packets or convert PCAP files
into flow features.
