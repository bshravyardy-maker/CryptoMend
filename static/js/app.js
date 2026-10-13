/**
 * Frontend JavaScript for Adaptive Redundancy Encrypted File Recovery Dashboard.
 * Handles tab transitions, metrics fetching, interactive simulation form, and ledger filtering.
 */

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initSeveritySlider();
    fetchSummaryMetrics();
    fetchLedger();
    initSimulateForm();
    initLedgerFilters();
});

// 1. Tab Navigation
function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");

            tabButtons.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                targetEl.classList.add("active");
            }
        });
    });
}

// 2. Severity Slider Display
function initSeveritySlider() {
    const slider = document.getElementById("severity");
    const display = document.getElementById("severity-val");
    if (slider && display) {
        slider.addEventListener("input", () => {
            const pct = Math.round(parseFloat(slider.value) * 100);
            display.textContent = `${pct}%`;
        });
    }
}

// 3. KPI Metrics Fetcher
async function fetchSummaryMetrics() {
    try {
        const res = await fetch("/api/summary");
        if (!res.ok) return;
        const data = await res.json();

        const totalTrials = data.total_trials || 0;
        document.getElementById("kpi-total-trials").textContent = totalTrials;

        const sumObj = data.strategies_summary || {};
        const stratKeys = Object.keys(sumObj);

        if (stratKeys.length > 0) {
            // Aggregate weighted or average across strategies
            let totalExact = 0;
            let totalPartial = 0;
            let totalRejections = 0;
            let totalSilent = 0;
            let totalOverheads = 0;

            stratKeys.forEach(k => {
                const s = sumObj[k];
                totalExact += s.exact_recovery_count || 0;
                totalPartial += s.partial_recovery_count || 0;
                totalRejections += s.rejection_count || 0;
                totalSilent += s.silent_incorrect_acceptance_count || 0;
                totalOverheads += s.avg_storage_overhead_pct || 0;
            });

            const exactPct = totalTrials > 0 ? (totalExact / totalTrials * 100).toFixed(1) : "0.0";
            const partialPct = totalTrials > 0 ? (totalPartial / totalTrials * 100).toFixed(1) : "0.0";
            const rejectPct = totalTrials > 0 ? (totalRejections / totalTrials * 100).toFixed(1) : "0.0";
            const silentPct = totalTrials > 0 ? (totalSilent / totalTrials * 100).toFixed(1) : "0.0";
            const avgOverhead = (totalOverheads / stratKeys.length).toFixed(1);

            document.getElementById("kpi-exact-rate").textContent = `${exactPct}%`;
            document.getElementById("kpi-partial-rate").textContent = `${partialPct}%`;
            document.getElementById("kpi-rejection-rate").textContent = `${rejectPct}%`;
            document.getElementById("kpi-silent-rate").textContent = `${silentPct}%`;
            document.getElementById("kpi-overhead").textContent = `${avgOverhead}%`;
        }
    } catch (err) {
        console.error("Failed to load summary metrics:", err);
    }
}

// 4. Recovery Ledger Fetcher & Filter Handler
async function fetchLedger() {
    const stratFilter = document.getElementById("filter-strategy").value;
    const statusFilter = document.getElementById("filter-status").value;
    const corrFilter = document.getElementById("filter-corruption").value;

    const tbody = document.getElementById("ledger-body");
    tbody.innerHTML = `<tr><td colspan="9" class="text-center">Loading filtered ledger records...</td></tr>`;

    try {
        const queryParams = new URLSearchParams({
            strategy: stratFilter,
            status: statusFilter,
            corruption: corrFilter,
            limit: 100
        });

        const res = await fetch(`/api/ledger?${queryParams.toString()}`);
        if (!res.ok) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center">Failed to fetch ledger.</td></tr>`;
            return;
        }

        const data = await res.json();
        const trials = data.trials || [];

        if (trials.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center">No trials match the selected filter criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = "";
        trials.forEach(t => {
            const tr = document.createElement("tr");

            // Format status badge
            let badgeClass = "badge-idle";
            if (t.status === "EXACT_RECOVERY") badgeClass = "badge-exact";
            else if (t.status === "PARTIAL_RECOVERY") badgeClass = "badge-partial";
            else if (t.status === "REJECTED") badgeClass = "badge-rejected";
            else if (t.status === "AUTHENTICATION_FAILURE") badgeClass = "badge-auth-fail";

            const silentTag = t.silent_incorrect_accepted === "True" || t.silent_incorrect_accepted === true
                ? `<span class="badge badge-rejected">ALERT: YES</span>`
                : `<span class="badge badge-exact">NONE (0%)</span>`;

            const sevPct = (parseFloat(t.severity) * 100).toFixed(0) + "%";
            const totalMs = (parseFloat(t.encoding_time_ms || 0) + parseFloat(t.recovery_time_ms || 0)).toFixed(1) + " ms";

            tr.innerHTML = `
                <td><code>${t.trial_id}</code></td>
                <td>${t.filename}</td>
                <td><strong style="text-transform: uppercase;">${t.strategy}</strong></td>
                <td><code>${t.corruption_type}</code></td>
                <td>${sevPct}</td>
                <td>${t.recovered_blocks} / ${t.total_blocks}</td>
                <td><span class="badge ${badgeClass}">${t.status}</span></td>
                <td>${silentTag}</td>
                <td>${totalMs}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to load ledger:", err);
        tbody.innerHTML = `<tr><td colspan="9" class="text-center">Error reading ledger data.</td></tr>`;
    }
}

function initLedgerFilters() {
    ["filter-strategy", "filter-status", "filter-corruption"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("change", fetchLedger);
        }
    });
}

// 5. Interactive Simulation Execution
function initSimulateForm() {
    const form = document.getElementById("simulate-form");
    const btn = document.getElementById("btn-run-sim");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector(".btn-text");

    const emptyState = document.getElementById("sim-empty-state");
    const resultsBody = document.getElementById("sim-results-body");
    const badge = document.getElementById("sim-status-badge");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // UI loading state
        btn.disabled = true;
        btnText.textContent = "Processing Cryptography & ECC...";

        try {
            const formData = new FormData(form);
            const res = await fetch("/api/simulate", {
                method: "POST",
                body: formData
            });

            const data = await res.json();

            if (!data.success) {
                alert(`Simulation error: ${data.error || "Unknown failure"}`);
                return;
            }

            // Update status badge
            badge.className = "badge";
            if (data.status === "EXACT_RECOVERY") {
                badge.classList.add("badge-exact");
                badge.textContent = "100% EXACT RECOVERY";
            } else if (data.status === "PARTIAL_RECOVERY") {
                badge.classList.add("badge-partial");
                badge.textContent = "PARTIAL RECOVERY";
            } else if (data.status === "AUTHENTICATION_FAILURE") {
                badge.classList.add("badge-auth-fail");
                badge.textContent = "AUTH TAG TAMPER DETECTED";
            } else {
                badge.classList.add("badge-rejected");
                badge.textContent = "CORRUPTION REJECTED";
            }

            // Populate stats
            document.getElementById("res-blocks").textContent = `${data.recovered_blocks} / ${data.total_blocks}`;
            document.getElementById("res-ratio").textContent = `${(data.recovery_rate * 100).toFixed(1)}%`;
            document.getElementById("res-corrupt-bytes").textContent = `${data.corrupted_bytes} Bytes`;
            document.getElementById("res-nsym").textContent = `${data.nsym} (${data.strategy})`;
            document.getElementById("res-overhead").textContent = `+${data.overhead_pct}%`;
            document.getElementById("res-time").textContent = `${data.recovery_time_ms} ms`;

            document.getElementById("res-details").textContent = data.details;
            document.getElementById("res-preview").textContent = data.recovered_preview || "[No authenticated data available]";

            emptyState.classList.add("hidden");
            resultsBody.classList.remove("hidden");

        } catch (err) {
            console.error("Simulation request failed:", err);
            alert("Network or server failure during cryptographic simulation.");
        } finally {
            btn.disabled = false;
            btnText.textContent = "Execute Cryptographic Experiment";
        }
    });
}
