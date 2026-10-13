"""Production-ready Flask Web Application for Adaptive File Recovery.

Provides RESTful endpoints for benchmark metrics, interactive corruption/recovery
simulation, and real-time dashboard analytics.
"""

import os
import csv
import json
import io
import tempfile
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename

from redundancy import RedundancyEngine
from corruption import CorruptionSimulator, CorruptionType
from recovery import RecoveryEngine, RecoveryStatus
from metrics import MetricsCalculator, TrialMetric

# Application Configuration
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.config["RESULTS_DIR"] = os.path.join(os.path.dirname(__file__), "results")
app.config["EXPERIMENTS_DIR"] = os.path.join(os.path.dirname(__file__), "experiments")

# Secret key for sessions if needed
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())


def load_benchmark_summary() -> Dict[str, Any]:
    """Load latest benchmark results from JSON file."""
    json_path = os.path.join(app.config["RESULTS_DIR"], "benchmark_results.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_trials": 0, "strategies_summary": {}}


def load_recovery_ledger(
    strategy_filter: str = "",
    status_filter: str = "",
    corruption_filter: str = ""
) -> List[Dict[str, Any]]:
    """Load and filter trial records from recovery ledger CSV."""
    ledger_path = os.path.join(app.config["RESULTS_DIR"], "recovery_ledger.csv")
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(ledger_path):
        return rows

    with open(ledger_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if strategy_filter and r.get("strategy") != strategy_filter:
                continue
            if status_filter and r.get("status") != status_filter:
                continue
            if corruption_filter and r.get("corruption_type") != corruption_filter:
                continue
            rows.append(r)
    return rows


@app.route("/")
def index():
    """Render dashboard page."""
    return render_template("index.html")


@app.route("/health")
def health():
    """System health check endpoint for monitoring and container readiness."""
    return jsonify({
        "status": "healthy",
        "service": "cryptomend",
        "version": "1.0.0"
    }), 200


@app.route("/api/summary")
def api_summary():
    """Return aggregated benchmark metrics."""
    data = load_benchmark_summary()
    return jsonify(data)


@app.route("/api/ledger")
def api_ledger():
    """Return recovery ledger trials with optional query filtering."""
    strategy = request.args.get("strategy", "").strip()
    status = request.args.get("status", "").strip()
    corruption = request.args.get("corruption", "").strip()
    limit = int(request.args.get("limit", 100))

    trials = load_recovery_ledger(
        strategy_filter=strategy,
        status_filter=status,
        corruption_filter=corruption
    )
    return jsonify({
        "total": len(trials),
        "trials": trials[:limit]
    })


@app.route("/api/export-ledger")
def export_ledger():
    """Export the complete recovery ledger as a downloadable CSV."""
    ledger_path = os.path.join(app.config["RESULTS_DIR"], "recovery_ledger.csv")
    if not os.path.exists(ledger_path):
        return Response("No ledger data available.", status=404, mimetype="text/plain")

    with open(ledger_path, "r", encoding="utf-8") as f:
        content = f.read()

    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=recovery_ledger.csv"}
    )


@app.route("/api/chart/<name>")
def get_chart(name: str):
    """Serve benchmark chart PNG images."""
    allowed_charts = {
        "strategy": "recovery_rate_by_strategy.png",
        "severity": "recovery_vs_severity.png",
        "overhead": "storage_overhead_comparison.png",
        "timing": "encoding_recovery_time.png",
    }
    filename = allowed_charts.get(name)
    if not filename:
        return jsonify({"error": "Unknown chart requested"}), 404

    chart_path = os.path.join(app.config["RESULTS_DIR"], filename)
    if not os.path.exists(chart_path):
        return jsonify({"error": "Chart not yet generated"}), 404

    return send_file(chart_path, mimetype="image/png")


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """
    Live Interactive Experiment Endpoint:
    Receives file or text input, strategy, risk profile, corruption type,
    severity, seed, and passphrase. Runs encryption -> corruption -> recovery pipeline
    and returns exact execution statistics and status badges.
    """
    try:
        # 1. Extract payload safely
        passphrase = request.form.get("passphrase", "DefaultDemoKey2026!")
        strategy = request.form.get("strategy", "adaptive")
        risk_profile = request.form.get("risk_profile", "medium")
        corruption_type = request.form.get("corruption_type", CorruptionType.RANDOM_BYTES)
        severity = float(request.form.get("severity", 0.05))
        seed = int(request.form.get("seed", 42))

        payload_bytes: bytes = b""

        if "file" in request.files and request.files["file"].filename:
            file_obj = request.files["file"]
            # Secure filename and read limited bytes
            _ = secure_filename(file_obj.filename)
            payload_bytes = file_obj.read()
        else:
            sample_text = request.form.get("text", "")
            if sample_text:
                payload_bytes = sample_text.encode("utf-8")
            else:
                payload_bytes = b"Standard Test Payload for Cryptographic Reed-Solomon Recovery. " * 8

        if len(payload_bytes) > 2 * 1024 * 1024:
            return jsonify({"error": "Interactive simulation payload limited to 2MB for responsiveness."}), 400

        # Step 1: Encode with authenticated encryption and redundancy
        container, enc_meta = RedundancyEngine.encode(
            plaintext=payload_bytes,
            passphrase=passphrase,
            strategy=strategy,
            risk_profile=risk_profile
        )

        # Step 2: Inject simulated corruption
        corrupted_bytes, corr_log = CorruptionSimulator.corrupt(
            data=container,
            corruption_type=corruption_type,
            severity=severity,
            seed=seed
        )

        # Step 3: Attempt recovery
        rec_res = RecoveryEngine.recover(
            container_bytes=corrupted_bytes,
            passphrase=passphrase,
            expected_original=payload_bytes
        )

        # Step 4: Metric evaluation
        metric = MetricsCalculator.evaluate_trial(
            trial_id="SIM-LIVE",
            filename="user_input",
            original_bytes=payload_bytes,
            encoded_meta=enc_meta,
            corruption_log=corr_log,
            recovery_res=rec_res
        )

        # Produce preview safe snippet (first 100 bytes hex or text if printable)
        preview_text = ""
        try:
            preview_text = rec_res.recovered_data[:200].decode("utf-8", errors="replace")
        except Exception:
            preview_text = rec_res.recovered_data[:100].hex()

        return jsonify({
            "success": True,
            "status": rec_res.status,
            "is_exact_match": metric.is_exact_match,
            "silent_incorrect_accepted": metric.silent_incorrect_accepted,
            "original_size": len(payload_bytes),
            "encoded_size": len(container),
            "overhead_pct": enc_meta["overhead_pct"],
            "strategy": enc_meta["strategy"],
            "risk_tier": enc_meta["risk_tier"],
            "nsym": enc_meta["nsym"],
            "total_blocks": rec_res.total_blocks,
            "recovered_blocks": rec_res.recovered_blocks,
            "lost_blocks": rec_res.lost_blocks,
            "recovery_rate": rec_res.recovery_rate,
            "encoding_time_ms": enc_meta["encoding_time_ms"],
            "recovery_time_ms": rec_res.execution_time_ms,
            "corruption_type": corr_log["type"],
            "corrupted_bytes": corr_log["corrupted_bytes"],
            "details": rec_res.details,
            "recovered_preview": preview_text
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
