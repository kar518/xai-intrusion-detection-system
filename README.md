# Explainable AI Intrusion Detection System

This project demonstrates an explainable, two-stage intrusion-detection
pipeline using the CICIDS2017 network-flow dataset.

The dashboard does not capture live packets. It loads one already-extracted
CICIDS2017 flow containing 65 numerical features and analyses that flow with
two trained Random Forest models.

## What happens to a flow

1. **Stage 1 - binary detection:** predict `BENIGN` or `ATTACK` and return the
   attack probability.
2. **SHAP explanation:** show the ten features that most influenced the Stage
   1 attack score. Positive values push toward `ATTACK`; negative values push
   toward `BENIGN`.
3. **Stage 2 - attack classification:** only when Stage 1 predicts `ATTACK`,
   predict the specific CICIDS2017 attack type and per-class probabilities.
4. **Threat analysis:** look up the predicted type's severity, description,
   typical indicators, and recommended mitigation.

Stage 2 is deliberately conditional. A flow that Stage 1 considers benign is
not assigned an attack type, even if its ground-truth dataset label is an
attack. This is how false negatives such as the Bot demo become visible.

## Run the dashboard

From the repository root:

```bash
source .venv/bin/activate
flask --app src.app.app run
```

Open <http://127.0.0.1:5000>.

If the virtual environment has not been created yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The processed dataset and trained model files must exist under
`data/processed/` and `models/` respectively.

## Recommended review demonstration

1. Click **Load DDoS**.
2. Point out that the dashboard displays the actual dataset label and all 65
   model inputs.
3. Click **Analyze Flow**.
4. Explain the Stage 1 prediction, attack probability, and binary confidence.
5. Explain the Stage 2 attack type and its conditional confidence.
6. Show the threat-analysis panel and its response guidance.
7. Show the SHAP panel. Red/positive contributions increase the attack score;
   blue/negative contributions decrease it.
8. Optionally load **Benign** to show that Stage 2 is skipped, then load
   **PortScan** or **Bot** to demonstrate the known false-negative limitation.

## Dashboard outputs

- **Actual dataset label:** ground truth from CICIDS2017; it is not given to
  the models as an input feature.
- **Prediction:** Stage 1's `BENIGN` or `ATTACK` decision.
- **Attack probability:** probability assigned specifically to the attack
  class.
- **Binary confidence:** the larger of the benign and attack probabilities.
- **Attack type/confidence:** Stage 2 result, shown only after an attack
  prediction.
- **SHAP contribution:** how much a feature moved the Stage 1 attack score
  away from its baseline.
- **Threat analysis:** static security guidance associated with the predicted
  attack type; this is a knowledge-base lookup, not a third ML model.

## Evaluation summary

Stage 1 was trained on Monday-Thursday traffic and tested on Friday traffic.
DDoS, PortScan, and Bot appear only in the Friday test attacks and were absent
from Stage 1 training.

| Metric | Result |
| --- | ---: |
| Test flows | 621,371 |
| Accuracy | 77.50% |
| Precision | 99.78% |
| Recall | 36.77% |
| F1-score | 53.74% |
| DDoS detection rate | 63.24% |
| PortScan detection rate | 0.25% |
| Bot detection rate | 0.00% |

The system produces few false alarms, but it misses many attacks from families
not represented in Stage 1 training. It should therefore be presented as an
experimental explainable IDS, not as a production-ready or standalone
security control.

Stage 2 uses a separate stratified split of all attack flows. Its training
protocol is different from the day-based Stage 1 evaluation, and the research
paper does not report a complete Stage 2 evaluation.

## Main files

- `src/app/app.py` - Flask routes and the two-stage inference pipeline
- `src/app/templates/index.html` - dashboard structure
- `src/app/static/app.js` - dashboard interaction and result rendering
- `src/xai/shap_explainer.py` - local SHAP explanations
- `src/threat_analysis/analyzer.py` - threat profiles and response guidance
- `src/preprocessing/` - inspection, cleaning, and splitting scripts
- `src/models/` - training and evaluation scripts
- `reports/` - saved data-preparation and Stage 1 evaluation results

## Known limitations

- No live traffic capture or PCAP upload; the demo uses stored flows.
- Low Stage 1 recall on unseen attack families, especially PortScan and Bot.
- Stage 2 runs only after Stage 1 detects an attack.
- SHAP currently explains Stage 1, not the attack-type decision.
- Threat profiles are static and do not adapt to the individual flow.
- Stage 2 needs a complete documented evaluation.
