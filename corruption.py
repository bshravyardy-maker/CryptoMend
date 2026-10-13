"""Corruption Simulator for Resilience and Recovery Testing.

Provides deterministic, reproducible degradation models including:
- Random byte flips
- Single-bit flips
- Contiguous burst damage (scratches / sector loss)
- Block erasures / missing frames
- File truncation
- Header and metadata corruption
- Authentication tag tampering
"""

import random
import struct
from typing import Tuple, Dict, Any, Optional
from file_format import STORED_HEADER_LEN, RAW_HEADER_LEN, FileFormat


class CorruptionType:
    RANDOM_BYTES = "random_bytes"
    RANDOM_BITS = "random_bits"
    BURST_DAMAGE = "burst_damage"
    MISSING_BLOCKS = "missing_blocks"
    TRUNCATED_FILE = "truncated_file"
    MODIFY_HEADER = "modify_header"
    MODIFY_AUTH_TAGS = "modify_auth_tags"


class CorruptionSimulator:
    """Injects precise, reproducible damage into file containers."""

    @classmethod
    def corrupt(
        cls,
        data: bytes,
        corruption_type: str,
        severity: float = 0.05,
        seed: Optional[int] = 42
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Apply corruption to container bytes.
        
        Args:
            data: Original container bytes.
            corruption_type: Type from CorruptionType constants.
            severity: Float from 0.0 to 1.0 indicating corruption scale.
            seed: Random seed for 100% reproducibility.
            
        Returns:
            Tuple of (corrupted_bytes, corruption_log_dict).
        """
        if not data:
            return b"", {"type": corruption_type, "severity": severity, "corrupted_bytes": 0}

        rng = random.Random(seed)
        buf = bytearray(data)
        log: Dict[str, Any] = {
            "type": corruption_type,
            "severity": severity,
            "seed": seed,
            "original_length": len(data),
            "corrupted_bytes": 0,
            "details": ""
        }

        severity = max(0.001, min(1.0, float(severity)))

        if corruption_type == CorruptionType.RANDOM_BYTES:
            # Corrupt a percentage of bytes in the payload region (after header)
            payload_start = min(STORED_HEADER_LEN, len(buf))
            target_indices = list(range(payload_start, len(buf)))
            if not target_indices:
                target_indices = list(range(len(buf)))
            
            num_corruptions = max(1, int(len(target_indices) * severity))
            chosen = rng.sample(target_indices, min(num_corruptions, len(target_indices)))
            
            for idx in chosen:
                orig = buf[idx]
                delta = rng.randint(1, 255)
                buf[idx] = orig ^ delta
                
            log["corrupted_bytes"] = len(chosen)
            log["details"] = f"Flipped {len(chosen)} random bytes across payload region."

        elif corruption_type == CorruptionType.RANDOM_BITS:
            # Corrupt single bits randomly
            payload_start = min(STORED_HEADER_LEN, len(buf))
            target_indices = list(range(payload_start, len(buf)))
            if not target_indices:
                target_indices = list(range(len(buf)))
                
            num_bits = max(1, int(len(target_indices) * 8 * severity))
            # Pick distinct bit positions
            chosen = rng.sample(range(len(target_indices) * 8), min(num_bits, len(target_indices) * 8))
            
            for bit_pos in chosen:
                byte_idx = target_indices[bit_pos // 8]
                bit_in_byte = bit_pos % 8
                buf[byte_idx] ^= (1 << bit_in_byte)
                
            log["corrupted_bytes"] = len(set([target_indices[b // 8] for b in chosen]))
            log["details"] = f"Flipped {len(chosen)} individual bits."

        elif corruption_type == CorruptionType.BURST_DAMAGE:
            # Contiguous scratch or sector loss
            payload_start = min(STORED_HEADER_LEN, len(buf))
            available = len(buf) - payload_start
            if available > 0:
                burst_len = max(1, int(available * severity))
                max_start = len(buf) - burst_len
                start_pos = rng.randint(payload_start, max(payload_start, max_start))
                end_pos = min(len(buf), start_pos + burst_len)
                
                for i in range(start_pos, end_pos):
                    buf[i] = rng.randint(0, 255)
                    
                log["corrupted_bytes"] = end_pos - start_pos
                log["details"] = f"Injected contiguous burst damage from byte {start_pos} to {end_pos} ({end_pos - start_pos} bytes)."
            else:
                log["details"] = "File too small for burst corruption."

        elif corruption_type == CorruptionType.MISSING_BLOCKS:
            # Erase one or more complete blocks from the container
            if len(buf) > STORED_HEADER_LEN:
                header_part = buf[:STORED_HEADER_LEN]
                raw_blocks = FileFormat.parse_blocks(bytes(buf), STORED_HEADER_LEN)
                if raw_blocks:
                    num_to_drop = max(1, int(len(raw_blocks) * severity))
                    drop_indices = set(rng.sample(range(len(raw_blocks)), min(num_to_drop, len(raw_blocks))))
                    
                    kept_blocks = [blk for i, blk in enumerate(raw_blocks) if i not in drop_indices]
                    
                    # Reconstruct file with missing blocks
                    new_buf = bytearray(header_part)
                    for blk in kept_blocks:
                        new_buf.extend(struct.pack(">H", len(blk)))
                        new_buf.extend(blk)
                    
                    buf = new_buf
                    log["corrupted_bytes"] = len(data) - len(buf)
                    log["details"] = f"Erased {len(drop_indices)} complete blocks (indices: {sorted(drop_indices)})."

        elif corruption_type == CorruptionType.TRUNCATED_FILE:
            # Premature truncation
            cut_fraction = max(0.1, 1.0 - severity)
            new_len = max(10, int(len(buf) * cut_fraction))
            buf = buf[:new_len]
            log["corrupted_bytes"] = len(data) - len(buf)
            log["details"] = f"Truncated file from {len(data)} to {new_len} bytes (lost {log['corrupted_bytes']} bytes)."

        elif corruption_type == CorruptionType.MODIFY_HEADER:
            # Corrupt magic bytes or header metadata
            # Target bytes within the first 48 bytes
            mod_count = max(1, int(RAW_HEADER_LEN * severity))
            mod_indices = rng.sample(range(min(RAW_HEADER_LEN, len(buf))), min(mod_count, RAW_HEADER_LEN))
            for idx in mod_indices:
                buf[idx] ^= rng.randint(1, 255)
            log["corrupted_bytes"] = len(mod_indices)
            log["details"] = f"Modified {len(mod_indices)} header metadata bytes (indices: {mod_indices})."

        elif corruption_type == CorruptionType.MODIFY_AUTH_TAGS:
            # Tamper specifically with authentication tags
            # Header tag is at STORED_HEADER_LEN - 16
            tag_mod_count = 0
            if len(buf) >= STORED_HEADER_LEN:
                # Corrupt header HMAC tag
                buf[STORED_HEADER_LEN - 1] ^= 0xFF
                tag_mod_count += 1
            
            # Corrupt block AES-GCM tags in payload
            raw_blocks = FileFormat.parse_blocks(bytes(buf), STORED_HEADER_LEN)
            if raw_blocks:
                num_blocks_to_tamper = max(1, int(len(raw_blocks) * severity))
                tamper_indices = rng.sample(range(len(raw_blocks)), min(num_blocks_to_tamper, len(raw_blocks)))
                
                # Rebuild blocks with flipped tag bytes
                new_blocks = []
                for i, blk in enumerate(raw_blocks):
                    blk_arr = bytearray(blk)
                    if i in tamper_indices and len(blk_arr) >= 22:
                        # Tag is at offset 6..22
                        tag_pos = rng.randint(6, 21)
                        blk_arr[tag_pos] ^= 0xAA
                        tag_mod_count += 1
                    new_blocks.append(blk_arr)
                    
                new_buf = bytearray(buf[:STORED_HEADER_LEN])
                for blk in new_blocks:
                    new_buf.extend(struct.pack(">H", len(blk)))
                    new_buf.extend(blk)
                buf = new_buf
                
            log["corrupted_bytes"] = tag_mod_count
            log["details"] = f"Tampered with {tag_mod_count} cryptographic authentication tags."

        else:
            raise ValueError(f"Unknown corruption type: {corruption_type}")

        log["corrupted_length"] = len(buf)
        return bytes(buf), log
