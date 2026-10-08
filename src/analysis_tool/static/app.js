let analysisResults = [];

const fileInput = document.getElementById("csv-file");
const dropZone = document.getElementById("drop-zone");
const uploadForm = document.getElementById("upload-form");
const analyzeCsvButton = document.getElementById("analyze-csv");
const analyzeDemoButton = document.getElementById("analyze-demo");

fileInput.addEventListener("change", () => {
    updateSelectedFile(fileInput.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
    dropZone.addEventListener(eventName, event => {
        event.preventDefault();
        dropZone.classList.add("dragging");
    });
}

for (const eventName of ["dragleave", "drop"]) {
    dropZone.addEventListener(eventName, event => {
        event.preventDefault();
        dropZone.classList.remove("dragging");
    });
}

dropZone.addEventListener("drop", event => {
    const file = event.dataTransfer.files[0];
    if (!file) return;

    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;
    updateSelectedFile(file);
});

uploadForm.addEventListener("submit", async event => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
        showMessage("Choose a CSV file first.", "error");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("row_limit", document.getElementById("row-limit").value);
    await runAnalysis("/analyze-csv", {method: "POST", body: formData}, "ANALYSING CSV");
});

analyzeDemoButton.addEventListener("click", async () => {
    await runAnalysis("/analyze-demo", {method: "POST"}, "ANALYSING DEMO");
});

function updateSelectedFile(file) {
    analyzeCsvButton.disabled = !file;
    document.getElementById("file-title").textContent = file ? file.name : "Drop a CSV here or choose a file";
    document.getElementById("file-detail").textContent = file
        ? `${formatBytes(file.size)} selected`
        : "Nothing is uploaded until you click Analyse CSV.";
}

async function runAnalysis(url, options, busyText) {
    setBusy(true, busyText);
    hideMessage();

    try {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Analysis failed.");

        renderAnalysis(data);
        showMessage(`Analysis complete: ${data.summary.analysed_rows} flow(s) processed.`, "info");
    } catch (error) {
        showMessage(error.message, "error");
    } finally {
        setBusy(false, "READY");
    }
}

function renderAnalysis(data) {
    analysisResults = data.results;
    const summary = data.summary;

    document.getElementById("metric-total").textContent = summary.analysed_rows;
    document.getElementById("metric-benign").textContent = summary.benign_predictions;
    document.getElementById("metric-attacks").textContent = summary.attack_predictions;
    document.getElementById("metric-probability").textContent = percent(summary.mean_attack_probability);
    document.getElementById("result-count").textContent = `${summary.analysed_rows} of ${summary.available_rows} available row(s)`;

    renderEvaluation(summary);
    renderResultsTable(data.results);

    document.getElementById("results-area").classList.remove("hidden");
    document.getElementById("detail-card").classList.add("hidden");
    document.getElementById("results-area").scrollIntoView({behavior: "smooth", block: "start"});
}

function renderEvaluation(summary) {
    const card = document.getElementById("evaluation-card");
    if (!summary.evaluated_rows) {
        card.classList.add("hidden");
        return;
    }

    const matrix = summary.confusion_matrix;
    const accuracy = summary.correct_binary_predictions / summary.evaluated_rows;
    document.getElementById("evaluation-accuracy").textContent = `${percent(accuracy)} correct`;
    document.getElementById("cm-tp").textContent = matrix.tp;
    document.getElementById("cm-fn").textContent = matrix.fn;
    document.getElementById("cm-fp").textContent = matrix.fp;
    document.getElementById("cm-tn").textContent = matrix.tn;
    card.classList.remove("hidden");
}

function renderResultsTable(results) {
    const body = document.getElementById("results-body");
    body.innerHTML = "";

    results.forEach((result, index) => {
        const row = document.createElement("tr");
        const matchClass = result.matches_actual === null
            ? ""
            : result.matches_actual ? "match-good" : "match-bad";
        const predictionClass = result.prediction === "ATTACK" ? "result-attack" : "result-benign";
        const severity = result.threat_analysis?.severity || "—";

        row.innerHTML = `
            <td>${result.row_number}</td>
            <td class="${matchClass}">${escapeHtml(result.actual_label || "Not supplied")}</td>
            <td class="${predictionClass}">${escapeHtml(result.prediction)}</td>
            <td>${percent(result.attack_probability)}</td>
            <td>${escapeHtml(formatAttackLabel(result.attack_type || "—"))}</td>
            <td>${escapeHtml(severity)}</td>
            <td><button class="inspect-button" type="button" data-result-index="${index}">Inspect</button></td>
        `;
        body.appendChild(row);
    });

    body.querySelectorAll("[data-result-index]").forEach(button => {
        button.addEventListener("click", () => showDetail(Number(button.dataset.resultIndex)));
    });
}

function showDetail(index) {
    const result = analysisResults[index];
    if (!result) return;

    document.getElementById("detail-title").textContent = `Flow ${result.row_number}`;
    const verdict = document.getElementById("detail-verdict");
    verdict.textContent = result.prediction;
    verdict.className = `verdict ${result.prediction === "ATTACK" ? "result-attack" : "result-benign"}`;

    document.getElementById("detail-attack-probability").textContent = percent(result.attack_probability);
    document.getElementById("detail-confidence").textContent = percent(result.binary_confidence);
    document.getElementById("detail-attack-type").textContent = formatAttackLabel(result.attack_type || "None");
    document.getElementById("detail-type-confidence").textContent = percent(result.attack_confidence);

    renderShap(result);
    renderThreat(result.threat_analysis);

    const card = document.getElementById("detail-card");
    card.classList.remove("hidden");
    card.scrollIntoView({behavior: "smooth", block: "start"});
}

function renderShap(result) {
    const items = result.shap || [];
    const summary = document.getElementById("shap-summary");
    summary.textContent = items.length
        ? `Top ${items.length} influences on the ATTACK score. Baseline ${percent(result.shap_base_value)}; final ${percent(result.attack_probability)}.`
        : result.shap_error || "No SHAP explanation available.";

    const list = document.getElementById("shap-list");
    list.innerHTML = "";
    const maximum = Math.max(...items.map(item => Math.abs(item.shap_value)), 1e-12);

    items.forEach(item => {
        const direction = item.shap_value >= 0 ? "attack" : "benign";
        const width = Math.abs(item.shap_value) / maximum * 50;
        const row = document.createElement("div");
        row.className = "shap-row";
        row.innerHTML = `
            <div class="shap-label">
                <strong>${escapeHtml(item.feature)}</strong>
                <small>value: ${escapeHtml(formatNumber(item.feature_value))}</small>
            </div>
            <div class="shap-track">
                <span class="shap-fill ${direction}" style="width:${width}%"></span>
            </div>
            <div class="shap-number">${item.shap_value >= 0 ? "+" : "−"}${Math.abs(item.shap_value).toFixed(4)}</div>
        `;
        list.appendChild(row);
    });
}

function renderThreat(threat) {
    const panel = document.getElementById("threat-detail");
    if (!threat) {
        panel.classList.add("hidden");
        return;
    }

    const severity = document.getElementById("detail-severity");
    severity.textContent = threat.severity;
    severity.className = `severity ${String(threat.severity).toLowerCase()}`;
    document.getElementById("detail-description").textContent = threat.description;
    renderList("detail-indicators", threat.indicators);
    renderList("detail-mitigation", threat.mitigation);
    panel.classList.remove("hidden");
}

function renderList(id, items) {
    const list = document.getElementById(id);
    list.innerHTML = "";
    (items || []).forEach(item => {
        const entry = document.createElement("li");
        entry.textContent = item;
        list.appendChild(entry);
    });
}

function setBusy(isBusy, text) {
    analyzeCsvButton.disabled = isBusy || !fileInput.files[0];
    analyzeDemoButton.disabled = isBusy;
    document.getElementById("system-status").lastChild.textContent = ` ${text}`;
}

function showMessage(text, type) {
    const message = document.getElementById("message");
    message.textContent = text;
    message.className = `message ${type}`;
}

function hideMessage() {
    document.getElementById("message").className = "message hidden";
}

function percent(value) {
    if (value === undefined || value === null) return "—";
    return `${(Number(value) * 100).toFixed(2)}%`;
}

function formatNumber(value) {
    return Number(value).toLocaleString(undefined, {maximumFractionDigits: 6});
}

function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatAttackLabel(value) {
    return String(value).replaceAll("�", "-").replace(/\s+/g, " ").trim();
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
