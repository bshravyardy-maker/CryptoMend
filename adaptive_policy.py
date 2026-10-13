"""Adaptive Redundancy Policy Engine.

Deterministically selects Reed-Solomon redundancy parameters (parity symbol count,
codeword block sizes) using documented risk assumptions. Operates strictly on
pre-transmission properties (payload size, environmental risk profile, entropy)
without any knowledge of future corruption patterns or benchmark conditions.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PolicyDecision:
    """Immutable record of the redundancy decision and supporting rationale."""
    strategy_name: str        # 'none', 'fixed', or 'adaptive'
    risk_tier: str           # 'none', 'low', 'medium', 'high'
    nsym: int                # Parity symbols per block (0, 16, 32, 64)
    data_capacity: int       # Data bytes per block (255 - nsym - 22 overhead)
    max_correctable_errors: int # Floor(nsym / 2)
    max_correctable_erasures: int # nsym
    expected_overhead_pct: float
    rationale: str


class AdaptivePolicy:
    """
    Deterministic rule-based policy engine for error correction redundancy.
    
    Documented Risk Model Assumptions:
    1. Small Payload Fragility: Files < 4 KB have fewer blocks; losing 1 block
       causes catastrophic loss of 25%-100% of content. They receive stronger protection.
    2. Environmental Risk Tiers:
       - 'low': High-reliability storage (local NVMe, RAID). Minimal parity (16 symbols).
       - 'medium': Standard networked storage / cloud transit. Balanced parity (32 symbols).
       - 'high': Hostile links (lossy wireless, satellite, archival tape). Robust parity (64 symbols).
    3. Shannon Entropy / Cascade Sensitivity: High-entropy data (>= 7.0 bits/byte,
       e.g., compressed or binary streams) cannot tolerate structural bit flips,
       justifying elevated redundancy.
    """

    # Reed-Solomon GF(2^8) parameters
    CODEWORD_MAX = 255
    BLOCK_HEADER_SIZE = 22  # 4B index + 2B len + 16B AES tag

    TIER_PARAMS = {
        "none": {"nsym": 0, "tier_id": 0},
        "low": {"nsym": 16, "tier_id": 1},
        "medium": {"nsym": 32, "tier_id": 2},
        "high": {"nsym": 64, "tier_id": 3},
    }

    @classmethod
    def calculate_entropy(cls, data: bytes) -> float:
        """Calculate Shannon entropy in bits per byte (0.0 to 8.0)."""
        if not data:
            return 0.0
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        total = len(data)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p)
        return round(entropy, 3)

    @classmethod
    def evaluate(
        cls,
        payload_length: int,
        strategy: str = "adaptive",
        risk_profile: str = "medium",
        entropy: Optional[float] = None
    ) -> PolicyDecision:
        """
        Deterministically evaluate redundancy parameters.
        
        Args:
            payload_length: Size in bytes of the plaintext payload.
            strategy: 'none', 'fixed', or 'adaptive'.
            risk_profile: 'low', 'medium', or 'high'.
            entropy: Optional precomputed Shannon entropy (0.0 to 8.0).
            
        Returns:
            PolicyDecision with deterministic parameters and reasoning.
        """
        strategy = strategy.lower().strip()
        risk_profile = risk_profile.lower().strip()

        if strategy not in ("none", "fixed", "adaptive"):
            raise ValueError(f"Unknown strategy: {strategy}. Must be 'none', 'fixed', or 'adaptive'.")

        if risk_profile not in ("low", "medium", "high"):
            risk_profile = "medium"

        # Baseline: No redundancy
        if strategy == "none":
            nsym = 0
            tier = "none"
            cap = cls.CODEWORD_MAX - cls.BLOCK_HEADER_SIZE
            return PolicyDecision(
                strategy_name="none",
                risk_tier=tier,
                nsym=nsym,
                data_capacity=cap,
                max_correctable_errors=0,
                max_correctable_erasures=0,
                expected_overhead_pct=0.0,
                rationale="Baseline mode: 0 parity bytes. No recovery capability."
            )

        # Baseline: Fixed redundancy (standard RS(255, 223) with 32 parity bytes)
        if strategy == "fixed":
            nsym = 32
            tier = "medium"
            cap = cls.CODEWORD_MAX - cls.BLOCK_HEADER_SIZE - nsym
            overhead = (nsym / cap) * 100
            return PolicyDecision(
                strategy_name="fixed",
                risk_tier=tier,
                nsym=nsym,
                data_capacity=cap,
                max_correctable_errors=nsym // 2,
                max_correctable_erasures=nsym,
                expected_overhead_pct=round(overhead, 2),
                rationale=f"Fixed RS(255, {255 - nsym}) with static 32 parity symbols across all files."
            )

        # Adaptive Redundancy: Deterministic rule set
        selected_tier = risk_profile
        reasons = [f"Base environmental risk profile set to '{risk_profile}'."]

        # Risk Factor 1: Small payload penalty
        # Very small files (< 2048 bytes) consist of 1-10 blocks. A single burst loss is fatal.
        if payload_length < 2048 and selected_tier == "low":
            selected_tier = "medium"
            reasons.append("Payload < 2KB: elevated from 'low' to 'medium' to guard against small-sample burst loss.")
        elif payload_length < 512 and selected_tier == "medium":
            selected_tier = "high"
            reasons.append("Payload < 512B: elevated to 'high' for micro-file preservation resilience.")

        # Risk Factor 2: High Shannon Entropy (> 7.2) indicates compressed/encrypted brittle streams
        if entropy is not None and entropy >= 7.2:
            if selected_tier == "low":
                selected_tier = "medium"
                reasons.append(f"Shannon entropy ({entropy:.2f} bits/B >= 7.20): elevated from 'low' to 'medium'.")
            elif selected_tier == "medium" and payload_length < 8192:
                selected_tier = "high"
                reasons.append(f"High entropy with moderate size (<8KB): elevated to 'high' tier.")

        nsym = cls.TIER_PARAMS[selected_tier]["nsym"]
        cap = cls.CODEWORD_MAX - cls.BLOCK_HEADER_SIZE - nsym
        overhead = (nsym / cap) * 100

        return PolicyDecision(
            strategy_name="adaptive",
            risk_tier=selected_tier,
            nsym=nsym,
            data_capacity=cap,
            max_correctable_errors=nsym // 2,
            max_correctable_erasures=nsym,
            expected_overhead_pct=round(overhead, 2),
            rationale=" ".join(reasons)
        )
