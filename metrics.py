"""Metrics and Evaluation Engine.

Computes recovery rates, rejection rates, silent incorrect acceptance rates,
storage overhead, and runtime benchmarks for experimental trials.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class TrialMetric:
    """Detailed record of an individual benchmark trial."""
    trial_id: str
    filename: str
    original_size: int
    strategy: str
    risk_tier: str
    nsym: int
    encoded_size: int
    overhead_pct: float
    corruption_type: str
    severity: float
    seed: int
    status: str
    is_exact_match: bool
    is_partial: bool
    is_rejected: bool
    silent_incorrect_accepted: bool
    recovered_blocks: int
    total_blocks: int
    recovery_rate: float
    encoding_time_ms: float
    recovery_time_ms: float
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCalculator:
    """Aggregates trial records into statistical summary metrics."""

    @staticmethod
    def evaluate_trial(
        trial_id: str,
        filename: str,
        original_bytes: bytes,
        encoded_meta: Dict[str, Any],
        corruption_log: Dict[str, Any],
        recovery_res: Any
    ) -> TrialMetric:
        """
        Evaluate a single trial outcome against ground truth.
        Enforces zero silent incorrect acceptance check.
        """
        orig_len = len(original_bytes)
        enc_len = encoded_meta.get("encoded_size", 0)
        overhead_pct = encoded_meta.get("overhead_pct", 0.0)

        # Ground truth byte-for-byte check
        is_exact = (recovery_res.status == "EXACT_RECOVERY") and (recovery_res.recovered_data == original_bytes)
        is_partial = (recovery_res.status == "PARTIAL_RECOVERY")
        is_rejected = (recovery_res.status in ("REJECTED", "AUTHENTICATION_FAILURE", "INVALID_FORMAT"))

        # Silent Incorrect Acceptance: Marked exact or accepted as valid, BUT bytes do NOT match!
        # In a secure authenticated system, this must ALWAYS be False.
        silent_acceptance = (recovery_res.status == "EXACT_RECOVERY") and (recovery_res.recovered_data != original_bytes)

        return TrialMetric(
            trial_id=trial_id,
            filename=filename,
            original_size=orig_len,
            strategy=encoded_meta.get("strategy", "unknown"),
            risk_tier=encoded_meta.get("risk_tier", "none"),
            nsym=encoded_meta.get("nsym", 0),
            encoded_size=enc_len,
            overhead_pct=overhead_pct,
            corruption_type=corruption_log.get("type", "none"),
            severity=corruption_log.get("severity", 0.0),
            seed=corruption_log.get("seed", 0),
            status=recovery_res.status,
            is_exact_match=is_exact,
            is_partial=is_partial,
            is_rejected=is_rejected,
            silent_incorrect_accepted=silent_acceptance,
            recovered_blocks=recovery_res.recovered_blocks,
            total_blocks=recovery_res.total_blocks,
            recovery_rate=recovery_res.recovery_rate,
            encoding_time_ms=encoded_meta.get("encoding_time_ms", 0.0),
            recovery_time_ms=recovery_res.execution_time_ms,
            details=recovery_res.details
        )

    @classmethod
    def aggregate_by_strategy(cls, trials: List[TrialMetric]) -> Dict[str, Any]:
        """Group and aggregate metrics across strategies."""
        groups: Dict[str, List[TrialMetric]] = {}
        for t in trials:
            groups.setdefault(t.strategy, []).append(t)

        summary = {}
        for strat, items in groups.items():
            total = len(items)
            exact_count = sum(1 for x in items if x.is_exact_match)
            partial_count = sum(1 for x in items if x.is_partial)
            rejected_count = sum(1 for x in items if x.is_rejected)
            silent_count = sum(1 for x in items if x.silent_incorrect_accepted)

            overheads = [x.overhead_pct for x in items]
            enc_times = [x.encoding_time_ms for x in items]
            rec_times = [x.recovery_time_ms for x in items]
            rec_rates = [x.recovery_rate for x in items]

            summary[strat] = {
                "total_trials": total,
                "exact_recovery_count": exact_count,
                "exact_recovery_rate": round(exact_count / total, 4) if total > 0 else 0.0,
                "partial_recovery_count": partial_count,
                "partial_recovery_rate": round(partial_count / total, 4) if total > 0 else 0.0,
                "rejection_count": rejected_count,
                "rejection_rate": round(rejected_count / total, 4) if total > 0 else 0.0,
                "silent_incorrect_acceptance_count": silent_count,
                "silent_incorrect_acceptance_rate": round(silent_count / total, 4) if total > 0 else 0.0,
                "avg_storage_overhead_pct": round(float(np.mean(overheads)), 2) if overheads else 0.0,
                "avg_encoding_time_ms": round(float(np.mean(enc_times)), 2) if enc_times else 0.0,
                "avg_recovery_time_ms": round(float(np.mean(rec_times)), 2) if rec_times else 0.0,
                "avg_block_recovery_rate": round(float(np.mean(rec_rates)), 4) if rec_rates else 0.0,
            }

        return summary
