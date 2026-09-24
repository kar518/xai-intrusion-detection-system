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


    document.getElementById(
        "xai-panel"
    ).classList.remove("hidden");
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
