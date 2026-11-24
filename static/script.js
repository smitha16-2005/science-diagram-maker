
const API = "";

const resultsBody = document.getElementById("resultsBody");
const message = document.getElementById("message");

const totalCount = document.getElementById("totalCount");
const passedCount = document.getElementById("passedCount");
const totalCostElement = document.getElementById("totalCost");

let currentResults = [];

// Escape text before displaying it in HTML.
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

// Format estimated API cost.
function formatCost(value) {
    return "$" + Number(value || 0).toFixed(6);
}

// Display messages.
function showMessage(text, type = "info") {
    if (!message) return;

    message.hidden = false;
    message.className = `message ${type}`;
    message.textContent = text;
}

// Render validation results.
function renderChecks(validation) {

    const checks = validation?.checks || {};

    const labels = {
        valid_xml: "Valid SVG / XML",
        inside_viewbox: "Inside SVG viewBox",
        has_title: "Title present",
        has_labels: "At least 3 text labels",
        has_animation: "Animation present",
        has_graphics: "Graphics present"
    };

    return Object.entries(labels).map(([key, label]) => {

        const passed = checks[key] === true;

        return `
            <div class="check-item">

                <span>${passed ? "✓" : "✗"}</span>

                <span>${label}</span>

                <b class="${passed ? "pass" : "fail"}">
                    ${passed ? "PASS" : "FAIL"}
                </b>

            </div>
        `;

    }).join("");
}

// Render one diagram row.
function renderRow(item, index) {

    const id = escapeHTML(item.id);

    const review = item.review || {};

    const decision = review.decision || "pending";

    // Handle failed generations.
    if (item.status === "error") {

        return `
            <tr>

                <td>${index + 1}</td>

                <td>
                    <strong>${escapeHTML(item.concept)}</strong>
                </td>

                <td colspan="3">

                    <div class="error-box">
                        ${escapeHTML(item.error || "Generation failed")}
                    </div>

                </td>

                <td>
                    <button
                        class="generate-btn"
                        data-generate="${id}">
                        Try again
                    </button>
                </td>

            </tr>
        `;
    }

    return `
        <tr>

            <td>${index + 1}</td>

            <!-- Concept -->
            <td>

                <strong>${escapeHTML(item.concept)}</strong>

                <p>
                    <span class="validation-status ${
                        item.status === "passed" ? "pass" : "fail"
                    }">
                        ${escapeHTML(item.status || "unknown").toUpperCase()}
                    </span>
                </p>

            </td>

            <!-- Animated SVG -->
            <td>

                <div class="svg-preview">

                    ${
                        item.svg ||
                        "<p>No SVG available</p>"
                    }

                </div>

            </td>

            <!-- Validation checks -->
            <td>
                ${renderChecks(item.validation)}
            </td>

            <!-- Model and token usage -->
            <td>

                <div class="usage-details">

                    <p>
                        <span>Model</span>
                        <strong>${escapeHTML(item.model || "Unknown")}</strong>
                    </p>

                    <p>
                        <span>Input tokens</span>
                        <strong>${Number(item.input_tokens || 0)}</strong>
                    </p>

                    <p>
                        <span>Output tokens</span>
                        <strong>${Number(item.output_tokens || 0)}</strong>
                    </p>

                    <p>
                        <span>Estimated cost</span>
                        <strong>${formatCost(item.estimated_cost_usd)}</strong>
                    </p>

                    <p>
                        <span>API retries</span>
                        <strong>${Number(item.api_retries || 0)}</strong>
                    </p>

                    <p>
                        <span>Validation retries</span>
                        <strong>${Number(item.validation_retries || 0)}</strong>
                    </p>

                </div>

            </td>

            <!-- Reviewer actions -->
            <td>

                <span class="review-status">
                    ${escapeHTML(decision.toUpperCase())}
                </span>

                <textarea
                    class="review-note"
                    id="note-${id}"
                    placeholder="Write your feedback..."
                >${escapeHTML(review.note || "")}</textarea>

                <div class="button-row">

                    <button
                        class="approve-btn"
                        data-review="${id}"
                        data-decision="approved">
                        Approve
                    </button>

                    <button
                        class="reject-btn"
                        data-review="${id}"
                        data-decision="rejected">
                        Reject
                    </button>

                    <button
                        class="generate-btn"
                        data-generate="${id}">
                        Regenerate
                    </button>

                </div>

            </td>

        </tr>
    `;
}

// Render all five saved diagrams.
function renderResults(results) {

    if (!resultsBody) {
        console.error("resultsBody element is missing.");
        return;
    }

    totalCount.textContent = `${results.length} / 5`;

    passedCount.textContent = results.filter(
        item => item.status === "passed"
    ).length;

    const totalCost = results.reduce(
        (sum, item) =>
            sum + Number(item.estimated_cost_usd || 0),
        0
    );

    totalCostElement.textContent = formatCost(totalCost);

    if (results.length === 0) {

        resultsBody.innerHTML = `
            <tr>
                <td colspan="6">
                    No saved diagrams found.
                </td>
            </tr>
        `;

        return;
    }

    resultsBody.innerHTML = results
        .map((item, index) => renderRow(item, index))
        .join("");
}

// INITIAL PAGE LOAD:
// Read embedded results directly from HTML.
// No API call is made here.
function loadInitialResults() {

    const initialResultsElement =
        document.getElementById("initial-results");

    if (!initialResultsElement) {

        showMessage(
            "Initial saved results were not embedded by the server.",
            "error"
        );

        return;
    }

    try {

        const savedResults = JSON.parse(
            initialResultsElement.textContent || "[]"
        );

        currentResults = savedResults;

        renderResults(currentResults);

    } catch (error) {

        console.error("Initial results parsing failed:", error);

        showMessage(
            "Could not load saved results: " + error.message,
            "error"
        );

    }
}

// Refresh results only after a user action.
async function refreshResults() {

    try {

        const response = await fetch(`${API}/api/results`);

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        currentResults = data.results || [];

        renderResults(currentResults);

        showMessage(
            "Results refreshed successfully.",
            "success"
        );

    } catch (error) {

        showMessage(
            "Could not refresh results: " + error.message,
            "error"
        );

    }
}

// Save reviewer decision and feedback.
async function saveReview(id, decision) {

    const noteElement =
        document.getElementById(`note-${id}`);

    const note = noteElement ? noteElement.value : "";

    try {

        const response = await fetch(
            `${API}/api/review/${encodeURIComponent(id)}`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    decision: decision,
                    note: note
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Could not save review"
            );
        }

        showMessage(
            `Review ${decision} successfully saved.`,
            "success"
        );

        await refreshResults();

    } catch (error) {

        showMessage(error.message, "error");

    }
}

// Generate or regenerate one diagram.
async function generateOne(id) {

    const buttons = document.querySelectorAll(
        `[data-generate="${id}"]`
    );

    buttons.forEach(button => {

        button.disabled = true;
        button.textContent = "Generating...";

    });

    showMessage(
        "Generating diagram. Please wait...",
        "info"
    );

    try {

        const response = await fetch(
            `${API}/api/generate/${encodeURIComponent(id)}`,
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Generation failed"
            );
        }

        showMessage(
            "Diagram generated successfully.",
            "success"
        );

        await refreshResults();

    } catch (error) {

        showMessage(
            "Generation error: " + error.message,
            "error"
        );

        buttons.forEach(button => {

            button.disabled = false;
            button.textContent = "Regenerate";

        });

    }
}

// Attach click events safely.
if (resultsBody) {

    resultsBody.addEventListener("click", async event => {

        const reviewButton =
            event.target.closest("[data-review]");

        if (reviewButton) {

            await saveReview(
                reviewButton.dataset.review,
                reviewButton.dataset.decision
            );

            return;
        }

        const generateButton =
            event.target.closest("[data-generate]");

        if (generateButton) {

            await generateOne(
                generateButton.dataset.generate
            );

        }

    });

}

// Attach refresh button.
const refreshButton =
    document.getElementById("refreshBtn");

if (refreshButton) {

    refreshButton.addEventListener(
        "click",
        refreshResults
    );

}

// Start the application.
loadInitialResults();
