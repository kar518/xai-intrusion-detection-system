# Flow Investigation Lab

This separate Flask application reuses the existing IDS model and explanation
functions. It does not edit the original app or train new models.

From the project root, run:

```sh
source .venv/bin/activate
flask --app src.investigation.app run --port 5002
```

Open http://127.0.0.1:5002. Keep the terminal running.

1. Observe a real test record and make a benign/suspicious/unsure guess.
2. Reveal the model decision and read plain-language SHAP descriptions.
3. Choose a timeline factor and reanalyse to compare original and simulated
   attack probabilities, verdicts, measurements and explanations.
4. Reveal the original dataset label and see whether your guess and the model
   were correct. Start another case to repeat the exercise.

Cases are the first three finite records available from each of BENIGN, DDoS,
PortScan and Bot in test.csv, interleaved and randomly presented. They are not
selected based on model correctness. Dataset labels are withheld from the
initial case response, and never sent to the prediction model.

The training script uses these 65 numeric features directly, without a scaler;
the lab passes recorded values in the saved feature order. The lab performs no
packet capture or traffic generation. Timing experiments multiply duration,
inter-arrival statistics, active and idle summaries together and divide the
four rate measurements by the same factor. Counts and byte/size features stay
fixed. This is an educational feature-level approximation: actual extraction
can change flow segmentation and active/idle definitions. Modified records
have no ground-truth label. Model failures remain visible.
