"""File Recovery and Authentication Verification Engine.

Performs staged Reed-Solomon error correction, AES-256-GCM authentication verification,
and erasure handling. Enforces strict zero-trust validation: reconstructed data is
never accepted without successful cryptographic authentication.
"""

import struct
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List
import reedsolo

from crypto_engine import CryptoEngine, AuthenticationError
from file_format import FileFormat, FileHeader, FormatValidationError


class RecoveryStatus:
    """Standardized recovery outcome states."""
    EXACT_RECOVERY = "EXACT_RECOVERY"
    PARTIAL_RECOVERY = "PARTIAL_RECOVERY"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    INVALID_FORMAT = "INVALID_FORMAT"
    REJECTED = "REJECTED"


@dataclass
class RecoveryResult:
    """Detailed result of a file recovery attempt."""
    status: str
    recovered_data: bytes
    total_blocks: int
    recovered_blocks: int
    lost_blocks: int
    recovery_rate: float
    execution_time_ms: float
    details: str
    is_exact_match: bool = False


class RecoveryEngine:
    """Decodes, repairs, and authenticates AREF files."""

    @classmethod
    def recover(
        cls,
        container_bytes: bytes,
        passphrase: str,
        expected_original: Optional[bytes] = None
    ) -> RecoveryResult:
        """
        Attempt recovery of an encrypted file container.
        
        Args:
            container_bytes: Raw bytes of the (potentially corrupted) .aref file.
            passphrase: User passphrase for key derivation.
            expected_original: Optional ground-truth bytes to verify exact match.
            
        Returns:
            RecoveryResult containing outcome status, recovered bytes, and audit details.
        """
        start_time = time.perf_counter()

        if not container_bytes:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RecoveryResult(
                status=RecoveryStatus.INVALID_FORMAT,
                recovered_data=b"",
                total_blocks=0,
                recovered_blocks=0,
                lost_blocks=0,
                recovery_rate=0.0,
                execution_time_ms=round(elapsed_ms, 2),
                details="Empty container provided."
            )

        # Stage 1: Parse and validate file container header
        try:
            # We first parse without key to extract salt, then derive key
            header, _, header_offset = FileFormat.parse_header(container_bytes, key=None)
        except FormatValidationError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RecoveryResult(
                status=RecoveryStatus.INVALID_FORMAT,
                recovered_data=b"",
                total_blocks=0,
                recovered_blocks=0,
                lost_blocks=0,
                recovery_rate=0.0,
                execution_time_ms=round(elapsed_ms, 2),
                details=f"Container header corrupted or invalid format: {str(e)}"
            )

        # Stage 2: Derive symmetric key and verify header authentication
        try:
            key = CryptoEngine.derive_key(passphrase, header.salt)
            # Re-verify header HMAC with derived key
            FileFormat.parse_header(container_bytes, key=key)
        except FormatValidationError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RecoveryResult(
                status=RecoveryStatus.AUTHENTICATION_FAILURE,
                recovered_data=b"",
                total_blocks=header.total_blocks,
                recovered_blocks=0,
                lost_blocks=header.total_blocks,
                recovery_rate=0.0,
                execution_time_ms=round(elapsed_ms, 2),
                details="Header authentication failed: invalid passphrase or header tampering."
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RecoveryResult(
                status=RecoveryStatus.INVALID_FORMAT,
                recovered_data=b"",
                total_blocks=header.total_blocks,
                recovered_blocks=0,
                lost_blocks=header.total_blocks,
                recovery_rate=0.0,
                execution_time_ms=round(elapsed_ms, 2),
                details=f"Key derivation failed: {str(e)}"
            )

        # Stage 3: Parse blocks from container
        raw_blocks = FileFormat.parse_blocks(container_bytes, header_offset)
        total_expected_blocks = header.total_blocks
        recovered_block_map: Dict[int, bytes] = {}
        rsc = reedsolo.RSCodec(header.nsym) if header.nsym > 0 else None

        # Stage 4: Process and decode available blocks
        for block_bytes in raw_blocks:
            # Step A: Reed-Solomon Forward Error Correction
            decoded_payload: Optional[bytes] = None
            if rsc is not None:
                try:
                    # Reed-Solomon automatically locates and corrects symbol errors up to nsym // 2
                    decoded_tuple = rsc.decode(bytearray(block_bytes))
                    decoded_payload = bytes(decoded_tuple[0])
                except reedsolo.ReedSolomonError:
                    # Errors exceeded Reed-Solomon correction capacity
                    continue
                except Exception:
                    continue
            else:
                decoded_payload = block_bytes

            # Step B: Framing validation: [index: 4B] + [len: 2B] + [tag: 16B] + [ciphertext]
            if len(decoded_payload) < 22:
                continue

            blk_idx, payload_len = struct.unpack(">IH", decoded_payload[:6])
            tag = decoded_payload[6:22]
            ciphertext = decoded_payload[22:22 + payload_len]

            if blk_idx >= total_expected_blocks or len(ciphertext) != payload_len:
                # Corrupted block metadata that escaped RS or invalid index
                continue

            # Step C: AES-256-GCM Authenticated Decryption
            block_nonce = CryptoEngine.derive_block_nonce(header.master_nonce, blk_idx)
            aad = struct.pack(">IH", blk_idx, payload_len)

            try:
                plaintext_chunk = CryptoEngine.decrypt_block(
                    key=key,
                    nonce=block_nonce,
                    ciphertext=ciphertext,
                    tag=tag,
                    aad=aad
                )
                recovered_block_map[blk_idx] = plaintext_chunk
            except AuthenticationError:
                # Authentication tag failed: block was corrupted beyond repair or tampered
                continue

        recovered_count = len(recovered_block_map)
        lost_count = total_expected_blocks - recovered_count
        recovery_rate = (recovered_count / total_expected_blocks) if total_expected_blocks > 0 else 0.0

        # Assemble recovered data in correct sequential order
        assembled_chunks = []
        for i in range(total_expected_blocks):
            if i in recovered_block_map:
                assembled_chunks.append(recovered_block_map[i])
            else:
                # Mark missing chunk as missing
                break
        
        # If all sequentially recovered up to recovered_count
        recovered_data = b"".join([recovered_block_map[i] for i in sorted(recovered_block_map.keys())])

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Stage 5: Evaluate recovery status
        if recovered_count == total_expected_blocks and len(recovered_data) == header.plaintext_size:
            is_match = (recovered_data == expected_original) if expected_original is not None else True
            if is_match:
                status = RecoveryStatus.EXACT_RECOVERY
                details = f"All {total_expected_blocks} blocks authenticated and recovered with 100% fidelity."
            else:
                # Mismatch despite tag (cryptographically improbable with AES-GCM)
                status = RecoveryStatus.REJECTED
                is_match = False
                details = "Data integrity mismatch against expected ground truth."
        elif recovered_count > 0:
            status = RecoveryStatus.PARTIAL_RECOVERY
            is_match = False
            details = f"Partial recovery: {recovered_count}/{total_expected_blocks} blocks successfully authenticated ({recovery_rate * 100:.1f}%)."
        else:
            status = RecoveryStatus.REJECTED
            is_match = False
            details = f"All {total_expected_blocks} blocks failed authentication or Reed-Solomon correction."

        return RecoveryResult(
            status=status,
            recovered_data=recovered_data,
            total_blocks=total_expected_blocks,
            recovered_blocks=recovered_count,
            lost_blocks=lost_count,
            recovery_rate=round(recovery_rate, 4),
            execution_time_ms=round(elapsed_ms, 2),
            details=details,
            is_exact_match=is_match
        )
