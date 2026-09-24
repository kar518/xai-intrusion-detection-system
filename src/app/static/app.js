let currentFlow = null;
let currentActualLabel = null;


// ================================================================
// LOAD REAL CICIDS2017 DEMO FLOW
// ================================================================

async function loadDemo(label) {

    setStatus("LOADING FLOW...");

    try {

        const response = await fetch(
            `/demo?label=${encodeURIComponent(label)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Failed to load demo flow."
            );
        }

        currentFlow = data.flow;
        currentActualLabel = data.actual_label;

        displayFlow(currentFlow);

        document.getElementById(
            "actual-label"
        ).textContent =
            `Actual dataset label: ${currentActualLabel}`;

        document.getElementById(
            "analyze-btn"
        ).disabled = false;

        document.getElementById(
            "result-panel"
        ).classList.add("hidden");

        document.getElementById(
            "xai-panel"
        ).classList.add("hidden");

        setStatus("FLOW LOADED");

    } catch (error) {

        console.error(error);

        setStatus("ERROR");

        alert(error.message);
    }
}


// ================================================================
// DISPLAY FEATURES
// ================================================================

function displayFlow(flow) {

    const container =
        document.getElementById("flow-container");

    container.innerHTML = "";

    const entries =
        Object.entries(flow);

    for (const [feature, value] of entries) {

        const card =
            document.createElement("div");

        card.className = "feature";

        card.innerHTML = `
            <span class="feature-name">
                ${escapeHtml(feature)}
            </span>

            <span class="feature-value">
                ${formatNumber(value)}
            </span>
        `;

        container.appendChild(card);
    }
}


// ================================================================
// ANALYZE FLOW
// ================================================================

async function analyzeFlow() {

    if (!currentFlow) {
        return;
    }

    const button =
        document.getElementById("analyze-btn");

    button.disabled = true;
    button.textContent = "Analyzing...";

    setStatus("RUNNING IDS...");

    try {

        const response = await fetch(
            "/predict",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(
                    currentFlow
                )
            }
        );

        const result =
            await response.json();

        if (!response.ok) {
            throw new Error(
                result.error ||
                "Prediction failed."
            );
        }

        displayResult(result);

        setStatus("ANALYSIS COMPLETE");

    } catch (error) {

        console.error(error);

        setStatus("ERROR");

        alert(error.message);

    } finally {

        button.disabled = false;
        button.textContent = "Analyze Flow";
    }
}


// ================================================================
// DISPLAY RESULT
// ================================================================

function displayResult(result) {

    const panel =
        document.getElementById(
            "result-panel"
        );

    panel.classList.remove("hidden");

    const prediction =
        document.getElementById(
            "prediction"
        );

    prediction.textContent =
        result.prediction;

    prediction.className =
        result.prediction === "ATTACK"
            ? "attack"
            : "benign";


    document.getElementById(
        "attack-probability"
    ).textContent =
        percent(result.attack_probability);


    document.getElementById(
        "binary-confidence"
    ).textContent =
        percent(result.binary_confidence);


    const attackType =
        document.getElementById(
            "attack-type"
        );

    const attackConfidence =
        document.getElementById(
            "attack-confidence"
        );


    if (
        result.prediction === "ATTACK"
    ) {

        attackType.textContent =
            result.attack_type;

        attackConfidence.textContent =
            percent(
                result.attack_confidence
            );

        displayProbabilities(
            result.attack_probabilities
        );

    } else {

        attackType.textContent =
            "None";

        attackConfidence.textContent =
            "—";

        document.getElementById(
            "probabilities"
        ).innerHTML =
            "<p>No attack classification performed.</p>";
    }


    // ============================================================
    // SHAP EXPLANATION
    // ============================================================

    displaySHAP(
        result.shap
    );




    displaySHAP(result);
    document.getElementById(
        "xai-panel"
    ).classList.remove("hidden");
}


// ================================================================
// SHAP FEATURE CONTRIBUTIONS
// ================================================================

function displaySHAP(shapData) {

    const container =
        document.getElementById(
            "shap-features"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (
        !shapData ||
        !shapData.features ||
        shapData.features.length === 0
    ) {
        container.innerHTML =
            "<p>No SHAP explanation available.</p>";

        return;
    }

    for (
        const item of shapData.features
    ) {

        const row =
            document.createElement("div");

        row.className =
            "shap-row";

        const direction =
            item.shap_value > 0
                ? "toward ATTACK"
                : "toward BENIGN";

        const sign =
            item.shap_value > 0
                ? "+"
                : "";

        row.innerHTML = `
            <div class="shap-feature">
                ${escapeHtml(item.feature)}
            </div>

            <div class="shap-value">
                ${sign}${item.shap_value.toFixed(6)}
            </div>

            <div class="shap-direction ${
                item.shap_value > 0
                    ? "toward-attack"
                    : "toward-benign"
            }">
                ${direction}
            </div>

            <div class="shap-input">
                Input: ${formatNumber(item.feature_value)}
            </div>
        `;

        container.appendChild(row);
    }
}




// ================================================================
// SHAP EXPLANATION
// ================================================================

function displaySHAP(result) {

    const container =
        document.getElementById("shap-container");

    const summary =
        document.getElementById("shap-summary");

    container.innerHTML = "";
    summary.innerHTML = "";

    const items = Array.isArray(result.shap)
        ? result.shap
        : [];

    if (items.length === 0) {

        const reason = result.shap_error
            ? `SHAP explanation failed: ${result.shap_error}`
            : "No SHAP explanation available.";

        container.innerHTML =
            `<div class="empty">${escapeHtml(reason)}</div>`;

        return;
    }

    const verdict =
        result.prediction === "ATTACK"
            ? "flagged as an attack"
            : "classified as benign";

    let text =
        `This flow was ${verdict}. ` +
        `Top ${items.length} features by influence ` +
        `on the attack score:`;

    if (typeof result.shap_base_value === "number") {
        text +=
            ` (baseline attack probability ` +
            `${percent(result.shap_base_value)}, ` +
            `this flow ${percent(result.attack_probability)})`;
    }

    summary.textContent = text;

    const maxAbs = Math.max(
        ...items.map(item => Math.abs(item.shap_value)),
        1e-12
    );

    for (const item of items) {

        const value = item.shap_value;
        const toward = value >= 0 ? "attack" : "benign";
        const width = (Math.abs(value) / maxAbs) * 50;

        const row = document.createElement("div");
        row.className = "shap-row";

        row.innerHTML = `
            <div class="shap-feature">
                <span class="shap-name">
                    ${escapeHtml(item.feature)}
                </span>
                <span class="shap-fvalue">
                    value: ${formatNumber(item.feature_value)}
                </span>
            </div>

            <div class="shap-bar">
                <div class="shap-axis"></div>
                <div
                    class="shap-fill shap-${toward}"
                    style="width: ${width}%;
                           ${value >= 0
                               ? "left: 50%;"
                               : "right: 50%;"}"
                ></div>
            </div>

            <div class="shap-number shap-text-${toward}">
                ${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(4)}
            </div>
        `;

        container.appendChild(row);
    }
}


// ================================================================
// ATTACK PROBABILITIES
// ================================================================

function displayProbabilities(probabilities) {

    const container =
        document.getElementById(
            "probabilities"
        );

    container.innerHTML = "";

    const sorted =
        Object.entries(probabilities)
            .sort(
                (a, b) =>
                    b[1] - a[1]
            );

    for (
        const [label, probability]
        of sorted
    ) {

        const row =
            document.createElement("div");

        row.className =
            "probability-row";

        row.innerHTML = `
            <div class="probability-label">
                ${escapeHtml(label)}
            </div>

            <div class="probability-bar">
                <div
                    class="probability-fill"
                    style="width: ${probability * 100}%"
                ></div>
            </div>

            <div class="probability-value">
                ${percent(probability)}
            </div>
        `;

        container.appendChild(row);
    }
}


// ================================================================
// HELPERS
// ================================================================

function percent(value) {

    if (
        value === undefined ||
        value === null
    ) {
        return "—";
    }

    return (
        (value * 100).toFixed(2) +
        "%"
    );
}


function formatNumber(value) {

    if (
        typeof value !== "number"
    ) {
        return value;
    }

    if (
        Number.isInteger(value)
    ) {
        return value.toLocaleString();
    }

    return value.toLocaleString(
        undefined,
        {
            maximumFractionDigits: 6
        }
    );
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function setStatus(message) {

    document.getElementById(
        "status"
    ).textContent =
        `● ${message}`;
}
