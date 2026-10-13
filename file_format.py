"""Binary File Format Specification for Adaptive Redundancy Encrypted Files (.aref).

Defines versioned container header structure, serialization, parsing,
validation, and block-level framing.
"""

import hmac
import hashlib
import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional
import reedsolo

MAGIC_BYTES = b"AREF"
FORMAT_VERSION = 1

# Header byte layout:
# Magic: 4B
# Version: 1B
# Strategy ID: 1B (0=none, 1=fixed, 2=adaptive)
# Risk Tier ID: 1B (0=none, 1=low, 2=medium, 3=high)
# nsym: 1B (0, 16, 32, 64)
# Plaintext size: 8B (uint64)
# Total blocks: 4B (uint32)
# Salt: 16B
# Master Nonce: 12B
# Total raw header: 4 + 1 + 1 + 1 + 1 + 8 + 4 + 16 + 12 = 48 bytes
RAW_HEADER_LEN = 48
HEADER_PARITY_NSYM = 16  # Header is protected by 16 parity symbols (recovers up to 8 byte flips)
HEADER_TAG_LEN = 16      # 16-byte HMAC-SHA256 truncated tag for header integrity
# Total header stored size = 48 + 16 + 16 = 80 bytes
STORED_HEADER_LEN = RAW_HEADER_LEN + HEADER_PARITY_NSYM + HEADER_TAG_LEN

STRATEGY_MAP = {"none": 0, "fixed": 1, "adaptive": 2}
STRATEGY_REV = {0: "none", 1: "fixed", 2: "adaptive"}

TIER_MAP = {"none": 0, "low": 1, "medium": 2, "high": 3}
TIER_REV = {0: "none", 1: "low", 2: "medium", 3: "high"}


class FormatValidationError(Exception):
    """Raised when file format validation, magic bytes, or structural layout fails."""
    pass


@dataclass
class FileHeader:
    """Represents validated file container metadata."""
    version: int
    strategy_name: str
    risk_tier: str
    nsym: int
    plaintext_size: int
    total_blocks: int
    salt: bytes
    master_nonce: bytes


@dataclass
class FormattedBlock:
    """Represents a discrete block within the container."""
    block_index: int
    payload_len: int
    tag: bytes
    ciphertext: bytes
    parity: bytes = b""


class FileFormat:
    """Serializer, deserializer, and validator for AREF file containers."""

    @staticmethod
    def pack_raw_header(header: FileHeader) -> bytes:
        """Serialize 48-byte raw header fields."""
        strat_id = STRATEGY_MAP.get(header.strategy_name, 0)
        tier_id = TIER_MAP.get(header.risk_tier, 0)
        
        packed = (
            MAGIC_BYTES +
            struct.pack(">BBBB", header.version, strat_id, tier_id, header.nsym) +
            struct.pack(">QI", header.plaintext_size, header.total_blocks) +
            header.salt +
            header.master_nonce
        )
        if len(packed) != RAW_HEADER_LEN:
            raise FormatValidationError(f"Invalid raw header length: {len(packed)} != {RAW_HEADER_LEN}")
        return packed

    @staticmethod
    def compute_header_tag(key: bytes, raw_header: bytes) -> bytes:
        """Generate a 16-byte HMAC-SHA256 authentication tag for the header."""
        h = hmac.new(key, raw_header, hashlib.sha256).digest()
        return h[:HEADER_TAG_LEN]

    @classmethod
    def serialize_container(
        cls,
        header: FileHeader,
        blocks_data: List[bytes],
        key: bytes
    ) -> bytes:
        """
        Serialize header and block list into a single binary container.
        Protects the header with Reed-Solomon parity and HMAC authentication tag.
        """
        raw_header = cls.pack_raw_header(header)
        
        # Protect header with Reed-Solomon parity
        rsc_header = reedsolo.RSCodec(HEADER_PARITY_NSYM)
        header_codeword = bytes(rsc_header.encode(raw_header))
        header_parity = header_codeword[RAW_HEADER_LEN:]
        
        # Compute header HMAC tag
        header_tag = cls.compute_header_tag(key, raw_header)
        
        stored_header = raw_header + header_parity + header_tag
        assert len(stored_header) == STORED_HEADER_LEN
        
        # Serialize blocks with 2-byte length prefix
        buffer = bytearray(stored_header)
        for blk in blocks_data:
            buffer.extend(struct.pack(">H", len(blk)))
            buffer.extend(blk)
            
        return bytes(buffer)

    @classmethod
    def parse_header(cls, file_bytes: bytes, key: Optional[bytes] = None) -> Tuple[FileHeader, bytes, int]:
        """
        Parse and validate file container header with Reed-Solomon error correction
        and HMAC integrity verification.
        
        Returns:
            Tuple of (FileHeader, raw_header_bytes, payload_offset)
        """
        if len(file_bytes) < STORED_HEADER_LEN:
            raise FormatValidationError(
                f"File too short ({len(file_bytes)} bytes). Minimum container size is {STORED_HEADER_LEN} bytes."
            )

        header_chunk = file_bytes[:STORED_HEADER_LEN]
        raw_part = header_chunk[:RAW_HEADER_LEN]
        parity_part = header_chunk[RAW_HEADER_LEN:RAW_HEADER_LEN + HEADER_PARITY_NSYM]
        header_tag = header_chunk[RAW_HEADER_LEN + HEADER_PARITY_NSYM:STORED_HEADER_LEN]

        # Attempt Reed-Solomon decoding of header if corrupted
        codeword = bytearray(raw_part + parity_part)
        try:
            rsc_header = reedsolo.RSCodec(HEADER_PARITY_NSYM)
            decoded_tuple = rsc_header.decode(codeword)
            corrected_raw = bytes(decoded_tuple[0])
        except reedsolo.ReedSolomonError:
            corrected_raw = raw_part  # Fall back to raw if RS uncorrectable

        # Validate Magic Bytes
        if corrected_raw[:4] != MAGIC_BYTES:
            raise FormatValidationError(
                f"Invalid file signature: expected {MAGIC_BYTES}, got {corrected_raw[:4]}."
            )

        # Unpack fields
        version, strat_id, tier_id, nsym = struct.unpack(">BBBB", corrected_raw[4:8])
        if version != FORMAT_VERSION:
            raise FormatValidationError(f"Unsupported format version {version}. Expected {FORMAT_VERSION}.")

        plaintext_size, total_blocks = struct.unpack(">QI", corrected_raw[8:20])
        salt = corrected_raw[20:36]
        master_nonce = corrected_raw[36:48]

        # Validate header tag if key is provided
        if key is not None:
            expected_tag = cls.compute_header_tag(key, corrected_raw)
            if not hmac.compare_digest(expected_tag, header_tag):
                raise FormatValidationError("Header authentication tag verification failed. Header was tampered.")

        strategy_name = STRATEGY_REV.get(strat_id, "adaptive")
        risk_tier = TIER_REV.get(tier_id, "medium")

        header = FileHeader(
            version=version,
            strategy_name=strategy_name,
            risk_tier=risk_tier,
            nsym=nsym,
            plaintext_size=plaintext_size,
            total_blocks=total_blocks,
            salt=salt,
            master_nonce=master_nonce
        )
        return header, corrected_raw, STORED_HEADER_LEN

    @classmethod
    def parse_blocks(cls, file_bytes: bytes, offset: int) -> List[bytes]:
        """
        Parse framing of blocks following the header.
        Safely handles truncated files and corrupted length prefixes.
        """
        blocks = []
        cur = offset
        file_len = len(file_bytes)

        while cur + 2 <= file_len:
            blk_len, = struct.unpack(">H", file_bytes[cur:cur + 2])
            cur += 2
            if cur + blk_len > file_len:
                # Truncated trailing block: capture whatever remains
                remaining = file_bytes[cur:]
                if remaining:
                    blocks.append(remaining)
                break
            blocks.append(file_bytes[cur:cur + blk_len])
            cur += blk_len

        return blocks
