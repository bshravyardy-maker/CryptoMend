"""Comprehensive Test Suite for Adaptive Redundancy Encrypted File Recovery.

Validates cryptographic round-trips, authenticated tamper detection,
Reed-Solomon error and erasure recovery, adaptive policy determinism,
benchmark metrics, and container validation.
"""

import os
import struct
import pytest
from crypto_engine import CryptoEngine, AuthenticationError
from adaptive_policy import AdaptivePolicy, PolicyDecision
from file_format import FileFormat, FileHeader, FormatValidationError, STORED_HEADER_LEN, RAW_HEADER_LEN
from redundancy import RedundancyEngine
from corruption import CorruptionSimulator, CorruptionType
from recovery import RecoveryEngine, RecoveryStatus
from metrics import MetricsCalculator
from app import app


# -----------------------------------------------------------------------------
# 1. Cryptographic Engine Tests
# -----------------------------------------------------------------------------

def test_crypto_key_derivation_deterministic():
    """Verify that scrypt key derivation is deterministic for same salt & passphrase."""
    salt = CryptoEngine.generate_salt()
    key1 = CryptoEngine.derive_key("SecretPassword123", salt)
    key2 = CryptoEngine.derive_key("SecretPassword123", salt)
    assert key1 == key2
    assert len(key1) == 32

    # Different salt produces different key
    salt2 = CryptoEngine.generate_salt()
    key3 = CryptoEngine.derive_key("SecretPassword123", salt2)
    assert key1 != key3


def test_crypto_unique_block_nonces():
    """Verify block nonce derivation guarantees unique nonces across block indices."""
    master = CryptoEngine.generate_nonce()
    nonce0 = CryptoEngine.derive_block_nonce(master, 0)
    nonce1 = CryptoEngine.derive_block_nonce(master, 1)
    nonce2 = CryptoEngine.derive_block_nonce(master, 2)
    assert nonce0 != nonce1
    assert nonce1 != nonce2
    assert len(nonce0) == 12


def test_crypto_encryption_decryption_roundtrip():
    """Verify authenticated AES-256-GCM encryption and decryption roundtrip."""
    salt = CryptoEngine.generate_salt()
    key = CryptoEngine.derive_key("TestPassphrase2026", salt)
    nonce = CryptoEngine.generate_nonce()
    plaintext = b"Highly sensitive intelligence payload data."
    aad = b"authenticated_header_context"

    ciphertext, tag = CryptoEngine.encrypt_block(key, nonce, plaintext, aad=aad)
    recovered = CryptoEngine.decrypt_block(key, nonce, ciphertext, tag, aad=aad)
    assert recovered == plaintext


def test_crypto_wrong_passphrase_fails():
    """Verify that decryption with an incorrect passphrase raises AuthenticationError."""
    salt = CryptoEngine.generate_salt()
    key_correct = CryptoEngine.derive_key("CorrectPassphrase", salt)
    key_wrong = CryptoEngine.derive_key("WrongPassphrase", salt)
    nonce = CryptoEngine.generate_nonce()
    plaintext = b"Payload to protect"

    ciphertext, tag = CryptoEngine.encrypt_block(key_correct, nonce, plaintext)
    with pytest.raises(AuthenticationError):
        CryptoEngine.decrypt_block(key_wrong, nonce, ciphertext, tag)


def test_crypto_tampered_ciphertext_fails():
    """Verify that tampering with ciphertext fails authentication tag verification."""
    salt = CryptoEngine.generate_salt()
    key = CryptoEngine.derive_key("Password123", salt)
    nonce = CryptoEngine.generate_nonce()
    ciphertext, tag = CryptoEngine.encrypt_block(key, nonce, b"Test data")

    tampered_ct = bytearray(ciphertext)
    tampered_ct[0] ^= 0x01
    with pytest.raises(AuthenticationError):
        CryptoEngine.decrypt_block(key, nonce, bytes(tampered_ct), tag)


# -----------------------------------------------------------------------------
# 2. Adaptive Policy Tests
# -----------------------------------------------------------------------------

def test_adaptive_policy_determinism():
    """Verify adaptive policy produces deterministic decisions given the same inputs."""
    d1 = AdaptivePolicy.evaluate(payload_length=1500, strategy="adaptive", risk_profile="medium")
    d2 = AdaptivePolicy.evaluate(payload_length=1500, strategy="adaptive", risk_profile="medium")
    assert d1 == d2
    assert d1.strategy_name == "adaptive"
    assert d1.nsym in (16, 32, 64)


def test_adaptive_policy_small_payload_elevation():
    """Verify small files receive elevated protection to guard against high relative loss."""
    dec_large = AdaptivePolicy.evaluate(payload_length=50000, strategy="adaptive", risk_profile="low")
    dec_small = AdaptivePolicy.evaluate(payload_length=1000, strategy="adaptive", risk_profile="low")
    assert dec_large.risk_tier == "low"
    assert dec_small.risk_tier == "medium"  # Elevated


def test_adaptive_policy_baselines():
    """Verify None and Fixed baseline strategy modes."""
    d_none = AdaptivePolicy.evaluate(payload_length=2000, strategy="none")
    assert d_none.nsym == 0
    assert d_none.expected_overhead_pct == 0.0

    d_fixed = AdaptivePolicy.evaluate(payload_length=2000, strategy="fixed")
    assert d_fixed.nsym == 32
    assert d_fixed.max_correctable_errors == 16


# -----------------------------------------------------------------------------
# 3. File Format & Container Validation Tests
# -----------------------------------------------------------------------------

def test_format_header_serialization():
    """Verify container header packing, serialization, and parsing."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = os.urandom(32)

    header = FileHeader(
        version=1,
        strategy_name="fixed",
        risk_tier="medium",
        nsym=32,
        plaintext_size=1024,
        total_blocks=6,
        salt=salt,
        master_nonce=nonce
    )

    container = FileFormat.serialize_container(header, [b"block1", b"block2"], key)
    assert len(container) > STORED_HEADER_LEN

    parsed_header, _, offset = FileFormat.parse_header(container, key=key)
    assert parsed_header.version == 1
    assert parsed_header.strategy_name == "fixed"
    assert parsed_header.plaintext_size == 1024
    assert parsed_header.total_blocks == 6
    assert parsed_header.salt == salt
    assert offset == STORED_HEADER_LEN


def test_format_header_tampering_fails():
    """Verify that tampering with header fields fails header authentication."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = os.urandom(32)

    header = FileHeader(
        version=1,
        strategy_name="fixed",
        risk_tier="medium",
        nsym=32,
        plaintext_size=1024,
        total_blocks=6,
        salt=salt,
        master_nonce=nonce
    )

    container = bytearray(FileFormat.serialize_container(header, [], key))
    # Modify header payload byte beyond RS capacity or tag byte
    container[STORED_HEADER_LEN - 1] ^= 0xFF

    with pytest.raises(FormatValidationError):
        FileFormat.parse_header(bytes(container), key=key)


def test_format_truncated_header():
    """Verify that truncated files smaller than header raise FormatValidationError."""
    with pytest.raises(FormatValidationError):
        FileFormat.parse_header(b"AREF123")


# -----------------------------------------------------------------------------
# 4. Redundancy & Recovery Roundtrip & Resilience Tests
# -----------------------------------------------------------------------------

def test_full_pipeline_clean_recovery():
    """Verify 100% exact recovery under uncorrupted condition."""
    plaintext = b"Lorem ipsum dolor sit amet, consectetur adipiscing elit." * 10
    passphrase = "TopSecretPassphrase2026"

    container, meta = RedundancyEngine.encode(plaintext, passphrase, strategy="adaptive")
    res = RecoveryEngine.recover(container, passphrase, expected_original=plaintext)

    assert res.status == RecoveryStatus.EXACT_RECOVERY
    assert res.is_exact_match is True
    assert res.recovered_data == plaintext
    assert res.recovered_blocks == res.total_blocks


def test_recovery_from_correctable_random_bytes():
    """Verify Reed-Solomon corrects random byte flips within capacity."""
    plaintext = b"Resilient communications payload with forward error correction." * 8
    passphrase = "ResilienceKey2026"

    # Use adaptive / fixed with 32 parity symbols
    container, meta = RedundancyEngine.encode(plaintext, passphrase, strategy="fixed")
    
    # Inject 1% random byte corruption
    corrupted, log = CorruptionSimulator.corrupt(
        container,
        corruption_type=CorruptionType.RANDOM_BYTES,
        severity=0.01,
        seed=101
    )

    res = RecoveryEngine.recover(corrupted, passphrase, expected_original=plaintext)
    assert res.status == RecoveryStatus.EXACT_RECOVERY
    assert res.recovered_data == plaintext


def test_recovery_from_correctable_burst():
    """Verify recovery from localized burst scratch."""
    plaintext = b"Critical telemetry buffer with Reed Solomon burst resilience." * 12
    passphrase = "BurstKey2026"

    container, meta = RedundancyEngine.encode(plaintext, passphrase, strategy="adaptive", risk_profile="high")
    
    # Inject modest burst damage (e.g. 5 bytes burst)
    corrupted, log = CorruptionSimulator.corrupt(
        container,
        corruption_type=CorruptionType.BURST_DAMAGE,
        severity=0.01,
        seed=202
    )

    res = RecoveryEngine.recover(corrupted, passphrase, expected_original=plaintext)
    assert res.status == RecoveryStatus.EXACT_RECOVERY
    assert res.recovered_data == plaintext


def test_failure_beyond_correction_capacity_safely_rejected():
    """Verify that severe corruption beyond capacity fails safely and does NOT accept corrupted data."""
    plaintext = b"Payload doomed to catastrophic degradation." * 10
    passphrase = "CatastrophicTest"

    container, meta = RedundancyEngine.encode(plaintext, passphrase, strategy="fixed")
    
    # Inject massive 40% corruption
    corrupted, log = CorruptionSimulator.corrupt(
        container,
        corruption_type=CorruptionType.RANDOM_BYTES,
        severity=0.40,
        seed=999
    )

    res = RecoveryEngine.recover(corrupted, passphrase, expected_original=plaintext)
    # Must NOT claim exact recovery
    assert res.status in (RecoveryStatus.REJECTED, RecoveryStatus.PARTIAL_RECOVERY, RecoveryStatus.AUTHENTICATION_FAILURE, RecoveryStatus.INVALID_FORMAT)
    assert res.is_exact_match is False


def test_missing_blocks_erasure_handling():
    """Verify that dropped blocks are identified as erasures without silent corruption."""
    plaintext = b"Multi-block file test intended to observe block drops." * 15
    passphrase = "MissingBlockKey"

    container, meta = RedundancyEngine.encode(plaintext, passphrase, strategy="fixed")
    assert meta["total_blocks"] > 1

    corrupted, log = CorruptionSimulator.corrupt(
        container,
        corruption_type=CorruptionType.MISSING_BLOCKS,
        severity=0.50,
        seed=42
    )

    res = RecoveryEngine.recover(corrupted, passphrase, expected_original=plaintext)
    # Since blocks were dropped, exact match cannot be claimed
    assert res.is_exact_match is False
    assert res.recovered_blocks < res.total_blocks


def test_zero_silent_incorrect_acceptance():
    """Verify that silent incorrect acceptance is strictly zero across metrics."""
    orig = b"Secret original"
    # Create artificial mismatch
    class MockRecovery:
        status = RecoveryStatus.EXACT_RECOVERY
        recovered_data = b"Wrong corrupted data"
        recovered_blocks = 1
        total_blocks = 1
        recovery_rate = 1.0
        execution_time_ms = 5.0
        details = "Test"

    meta = MetricsCalculator.evaluate_trial(
        trial_id="T1",
        filename="f1",
        original_bytes=orig,
        encoded_meta={"strategy": "fixed", "risk_tier": "medium", "nsym": 32, "encoded_size": 100, "overhead_pct": 20.0},
        corruption_log={"type": "random_bytes", "severity": 0.05, "seed": 1},
        recovery_res=MockRecovery()
    )

    # Caught by evaluation!
    assert meta.silent_incorrect_accepted is True
    assert meta.is_exact_match is False


# -----------------------------------------------------------------------------
# 5. Web API & Upload Validation Tests
# -----------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_api_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"
    assert res.get_json()["service"] == "cryptomend"


def test_api_summary_endpoint(client):
    res = client.get("/api/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_trials" in data


def test_api_simulate_endpoint(client):
    res = client.post("/api/simulate", data={
        "text": "Hello world from pytest web client simulation!",
        "passphrase": "WebTestKey2026",
        "strategy": "fixed",
        "risk_profile": "medium",
        "corruption_type": "random_bytes",
        "severity": "0.01",
        "seed": "42"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "status" in data
    assert "recovery_rate" in data
