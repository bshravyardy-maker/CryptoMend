"""Benchmark Engine for Empirical Resilience and Overhead Evaluation.

Executes matched-pair trials comparing No Redundancy, Fixed Reed-Solomon,
and Adaptive Reed-Solomon across configurable corruption scenarios.
Generates genuine CSV, JSON, and Matplotlib visual analytics.
"""

import os
import csv
import json
import time
from typing import List, Dict, Any

# Ensure headless Matplotlib rendering
import matplotlib
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_aref")
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from redundancy import RedundancyEngine
from corruption import CorruptionSimulator, CorruptionType
from recovery import RecoveryEngine
from metrics import MetricsCalculator, TrialMetric


class BenchmarkRunner:
    """Executes systematic resilience and overhead experiments."""

    def __init__(self, output_dir: str = "results", experiments_dir: str = "experiments"):
        self.output_dir = output_dir
        self.experiments_dir = experiments_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.experiments_dir, exist_ok=True)

    def prepare_test_files(self) -> Dict[str, bytes]:
        """Create sample test payloads of diverse sizes and entropy profiles."""
        test_files = {}

        # 1. Structured Text file (1 KB)
        text_content = (
            "Adaptive Redundancy for Encrypted File Recovery System.\n"
            "Confidential Mission Briefing: Resilience under channel packet degradation.\n"
            "Timestamp: 2026-10-13T15:38:26Z. Authenticated AES-GCM + Reed-Solomon Parity.\n"
        ) * 15
        text_bytes = text_content.encode("utf-8")[:1024]
        test_files["mission_log.txt"] = text_bytes
        with open(os.path.join(self.experiments_dir, "mission_log.txt"), "wb") as f:
            f.write(text_bytes)

        # 2. Binary / Compressed-like High-Entropy file (2 KB)
        rng = np.random.default_rng(seed=1337)
        binary_bytes = bytes(rng.integers(0, 256, size=2048, dtype=np.uint8))
        test_files["sensor_telemetry.bin"] = binary_bytes
        with open(os.path.join(self.experiments_dir, "sensor_telemetry.bin"), "wb") as f:
            f.write(binary_bytes)

        # 3. JSON Configuration file (512 Bytes)
        cfg_content = json.dumps({
            "service": "secure-adaptive-storage",
            "version": "1.0.0",
            "cipher": "AES-256-GCM",
            "kdf": "scrypt",
            "reed_solomon_gf": "2^8",
            "thresholds": {"low": 16, "medium": 32, "high": 64},
            "environment": "edge-sensor-gateway",
            "status": "active"
        }, indent=2).encode("utf-8")
        test_files["system_manifest.json"] = cfg_content
        with open(os.path.join(self.experiments_dir, "system_manifest.json"), "wb") as f:
            f.write(cfg_content)

        return test_files

    def run_benchmark(self, iterations_per_condition: int = 1) -> List[TrialMetric]:
        """
        Run systematic matched trials across strategies and corruption modes.
        """
        test_files = self.prepare_test_files()
        passphrase = "CorrectHorseBatteryStaple-2026!"

        strategies = ["none", "fixed", "adaptive"]
        corruption_scenarios = [
            (CorruptionType.RANDOM_BYTES, 0.02),
            (CorruptionType.RANDOM_BYTES, 0.05),
            (CorruptionType.BURST_DAMAGE, 0.05),
            (CorruptionType.BURST_DAMAGE, 0.15),
            (CorruptionType.MISSING_BLOCKS, 0.10),
            (CorruptionType.MODIFY_HEADER, 0.04),
            (CorruptionType.MODIFY_AUTH_TAGS, 0.05),
        ]

        trials: List[TrialMetric] = []
        trial_counter = 1

        print(f"Starting benchmark with {len(test_files)} files, {len(strategies)} strategies, {len(corruption_scenarios)} corruption scenarios...")

        for fname, raw_bytes in test_files.items():
            for strat in strategies:
                # Encode once per file + strategy pair
                try:
                    container, enc_meta = RedundancyEngine.encode(
                        plaintext=raw_bytes,
                        passphrase=passphrase,
                        strategy=strat,
                        risk_profile="medium"
                    )
                except Exception as e:
                    print(f"Encoding failed for {fname} [{strat}]: {e}")
                    continue

                for corr_type, severity in corruption_scenarios:
                    for it in range(iterations_per_condition):
                        seed = 1000 + trial_counter
                        trial_id = f"TR-{trial_counter:04d}"

                        # Corrupt container
                        corrupted_bytes, corr_log = CorruptionSimulator.corrupt(
                            data=container,
                            corruption_type=corr_type,
                            severity=severity,
                            seed=seed
                        )

                        # Attempt recovery
                        recovery_res = RecoveryEngine.recover(
                            container_bytes=corrupted_bytes,
                            passphrase=passphrase,
                            expected_original=raw_bytes
                        )

                        # Evaluate metrics
                        metric = MetricsCalculator.evaluate_trial(
                            trial_id=trial_id,
                            filename=fname,
                            original_bytes=raw_bytes,
                            encoded_meta=enc_meta,
                            corruption_log=corr_log,
                            recovery_res=recovery_res
                        )
                        trials.append(metric)
                        trial_counter += 1

        print(f"Completed {len(trials)} benchmark trials.")
        self.save_results(trials)
        self.generate_charts(trials)
        return trials

    def save_results(self, trials: List[TrialMetric]) -> None:
        """Persist benchmark outcomes to CSV, JSON, and recovery ledger."""
        ledger_path = os.path.join(self.output_dir, "recovery_ledger.csv")
        results_csv_path = os.path.join(self.output_dir, "benchmark_results.csv")
        results_json_path = os.path.join(self.output_dir, "benchmark_results.json")

        # 1. Recovery ledger (all individual trials)
        fieldnames = list(trials[0].to_dict().keys()) if trials else []
        with open(ledger_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for t in trials:
                writer.writerow(t.to_dict())

        # 2. Aggregated summary
        aggregated = MetricsCalculator.aggregate_by_strategy(trials)

        # Save aggregated JSON
        summary_payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_trials": len(trials),
            "strategies_summary": aggregated,
        }
        with open(results_json_path, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)

        # Save aggregated CSV
        with open(results_csv_path, "w", newline="", encoding="utf-8") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([
                "Strategy", "Total Trials", "Exact Recovery Rate", "Partial Recovery Rate",
                "Rejection Rate", "Silent Acceptance Rate", "Avg Storage Overhead %",
                "Avg Encoding Time (ms)", "Avg Recovery Time (ms)"
            ])
            for strat, data in aggregated.items():
                csv_writer.writerow([
                    strat,
                    data["total_trials"],
                    f"{data['exact_recovery_rate'] * 100:.1f}%",
                    f"{data['partial_recovery_rate'] * 100:.1f}%",
                    f"{data['rejection_rate'] * 100:.1f}%",
                    f"{data['silent_incorrect_acceptance_rate'] * 100:.1f}%",
                    f"{data['avg_storage_overhead_pct']:.2f}%",
                    f"{data['avg_encoding_time_ms']:.2f}",
                    f"{data['avg_recovery_time_ms']:.2f}",
                ])

        print(f"Saved results to {results_csv_path}, {results_json_path}, and {ledger_path}")

    def generate_charts(self, trials: List[TrialMetric]) -> None:
        """Render high-resolution Matplotlib visualizations."""
        aggregated = MetricsCalculator.aggregate_by_strategy(trials)
        strategies = list(aggregated.keys())

        # Chart 1: Recovery Rates by Strategy (Exact vs Partial vs Rejected)
        plt.figure(figsize=(9, 5))
        bar_width = 0.25
        x = np.arange(len(strategies))

        exact_rates = [aggregated[s]["exact_recovery_rate"] * 100 for s in strategies]
        partial_rates = [aggregated[s]["partial_recovery_rate"] * 100 for s in strategies]
        reject_rates = [aggregated[s]["rejection_rate"] * 100 for s in strategies]

        plt.bar(x - bar_width, exact_rates, width=bar_width, label="Exact Recovery (100%)", color="#10b981")
        plt.bar(x, partial_rates, width=bar_width, label="Partial Recovery", color="#3b82f6")
        plt.bar(x + bar_width, reject_rates, width=bar_width, label="Safely Rejected / Tag Fail", color="#ef4444")

        plt.title("Recovery Outcome Distribution by Strategy", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Redundancy Strategy", fontsize=11)
        plt.ylabel("Outcome Percentage (%)", fontsize=11)
        plt.xticks(x, [s.upper() for s in strategies])
        plt.ylim(0, 105)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.legend(frameon=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "recovery_rate_by_strategy.png"), dpi=200)
        plt.close()

        # Chart 2: Recovery Rate vs Corruption Severity
        plt.figure(figsize=(9, 5))
        # Filter random bytes and burst trials
        subset = [t for t in trials if t.corruption_type in (CorruptionType.RANDOM_BYTES, CorruptionType.BURST_DAMAGE)]
        severities = sorted(list(set(t.severity for t in subset)))

        for s in strategies:
            rates_by_sev = []
            for sev in severities:
                matching = [t for t in subset if t.strategy == s and t.severity == sev]
                if matching:
                    rates_by_sev.append(sum(1 for m in matching if m.is_exact_match) / len(matching) * 100)
                else:
                    rates_by_sev.append(0.0)
            plt.plot(np.array(severities) * 100, rates_by_sev, marker="o", linewidth=2.2, label=s.upper())

        plt.title("Exact Recovery Rate vs. Corruption Severity", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Corruption Severity (% of payload)", fontsize=11)
        plt.ylabel("Exact Recovery Rate (%)", fontsize=11)
        plt.ylim(-5, 105)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend(frameon=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "recovery_vs_severity.png"), dpi=200)
        plt.close()

        # Chart 3: Storage Overhead Comparison
        plt.figure(figsize=(8, 5))
        overheads = [aggregated[s]["avg_storage_overhead_pct"] for s in strategies]
        colors = ["#64748b", "#3b82f6", "#8b5cf6"]
        bars = plt.bar([s.upper() for s in strategies], overheads, color=colors, width=0.5)
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2.0, height + 0.5, f"{height:.1f}%", ha="center", va="bottom", fontweight="bold")

        plt.title("Total Storage Overhead by Strategy (Format + Parity)", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Redundancy Strategy", fontsize=11)
        plt.ylabel("Average Overhead (%)", fontsize=11)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "storage_overhead_comparison.png"), dpi=200)
        plt.close()

        # Chart 4: Encoding and Recovery Times
        plt.figure(figsize=(9, 5))
        enc_times = [aggregated[s]["avg_encoding_time_ms"] for s in strategies]
        rec_times = [aggregated[s]["avg_recovery_time_ms"] for s in strategies]

        x = np.arange(len(strategies))
        width = 0.35
        plt.bar(x - width / 2, enc_times, width, label="Encoding Time (ms)", color="#0ea5e9")
        plt.bar(x + width / 2, rec_times, width, label="Recovery Time (ms)", color="#f59e0b")

        plt.title("Computational Runtime: Encoding vs Recovery", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Redundancy Strategy", fontsize=11)
        plt.ylabel("Mean Duration (ms)", fontsize=11)
        plt.xticks(x, [s.upper() for s in strategies])
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.legend(frameon=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "encoding_recovery_time.png"), dpi=200)
        plt.close()

        print("Generated benchmark charts in results/")


if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run_benchmark(iterations_per_condition=1)
