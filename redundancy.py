"""Redundancy and Protection Engine.

Coordinates key derivation, AES-256-GCM block encryption, and Reed-Solomon
forward error correction parity generation across None, Fixed, and Adaptive strategies.
"""

import math
import struct
import time
from typing import Dict, Any, Tuple
import reedsolo

from crypto_engine import CryptoEngine
from adaptive_policy import AdaptivePolicy, PolicyDecision
from file_format import FileFormat, FileHeader


class RedundancyEngine:
    """Manages secure file packaging and parity generation."""

    @staticmethod
    def encode(
        plaintext: bytes,
        passphrase: str,
        strategy: str = "adaptive",
        risk_profile: str = "medium"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Encrypt and encode plaintext bytes with authenticated encryption
        and Reed-Solomon redundancy.
        
        Args:
            plaintext: Raw data to protect.
            passphrase: User-provided secret passphrase.
            strategy: 'none', 'fixed', or 'adaptive'.
            risk_profile: 'low', 'medium', or 'high'.
            
        Returns:
            Tuple of (encoded_container_bytes, metadata_dict).
        """
        start_time = time.perf_counter()
        
        # Calculate entropy to inform adaptive decisions
        entropy = AdaptivePolicy.calculate_entropy(plaintext)
        decision: PolicyDecision = AdaptivePolicy.evaluate(
            payload_length=len(plaintext),
            strategy=strategy,
            risk_profile=risk_profile,
            entropy=entropy
        )

        # Cryptographic initialization
        salt = CryptoEngine.generate_salt()
        master_nonce = CryptoEngine.generate_nonce()
        key = CryptoEngine.derive_key(passphrase, salt)

        # Segment plaintext into block payloads
        data_cap = decision.data_capacity
        if data_cap <= 0:
            raise ValueError(f"Invalid block data capacity: {data_cap}")

        total_bytes = len(plaintext)
        if total_bytes == 0:
            # Handle empty file as a single empty chunk
            chunks = [b""]
        else:
            chunks = [plaintext[i:i + data_cap] for i in range(0, total_bytes, data_cap)]
        
        total_blocks = len(chunks)
        blocks_data = []
        rsc = reedsolo.RSCodec(decision.nsym) if decision.nsym > 0 else None

        for idx, chunk in enumerate(chunks):
            # Unique per-block nonce
            block_nonce = CryptoEngine.derive_block_nonce(master_nonce, idx)
            # Associated Authenticated Data binds block index and payload length
            aad = struct.pack(">IH", idx, len(chunk))
            
            ciphertext, tag = CryptoEngine.encrypt_block(key, block_nonce, chunk, aad=aad)
            
            # Internal block structure: [index: 4B] + [len: 2B] + [tag: 16B] + [ciphertext]
            block_payload = aad + tag + ciphertext
            
            if decision.nsym > 0:
                # Apply Reed-Solomon error correction encoding
                codeword = bytes(rsc.encode(block_payload))
                blocks_data.append(codeword)
            else:
                blocks_data.append(block_payload)

        # Assemble container header
        header = FileHeader(
            version=1,
            strategy_name=decision.strategy_name,
            risk_tier=decision.risk_tier,
            nsym=decision.nsym,
            plaintext_size=total_bytes,
            total_blocks=total_blocks,
            salt=salt,
            master_nonce=master_nonce
        )

        container_bytes = FileFormat.serialize_container(header, blocks_data, key)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        overhead_bytes = len(container_bytes) - total_bytes
        overhead_pct = (overhead_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0

        metadata = {
            "strategy": decision.strategy_name,
            "risk_tier": decision.risk_tier,
            "nsym": decision.nsym,
            "total_blocks": total_blocks,
            "original_size": total_bytes,
            "encoded_size": len(container_bytes),
            "overhead_bytes": overhead_bytes,
            "overhead_pct": round(overhead_pct, 2),
            "encoding_time_ms": round(elapsed_ms, 2),
            "entropy": entropy,
            "rationale": decision.rationale,
            "max_correctable_errors_per_block": decision.max_correctable_errors,
            "max_correctable_erasures_per_block": decision.max_correctable_erasures,
        }

        return container_bytes, metadata
