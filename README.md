# CryptoMend: Adaptive Redundancy for Encrypted File Recovery

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/cryptography-AES--256--GCM-blueviolet.svg)](https://cryptography.io)
[![FEC](https://img.shields.io/badge/ECC-Reed--Solomon%20GF(2%5E8)-orange.svg)](https://github.com/tomerfiliba/reedsolomon)

A secure, high-resilience file storage and transmission framework that combines **AES-256-GCM authenticated encryption** with **context-adaptive Reed–Solomon forward error correction (FEC)**.

This repository provides the core cryptographic engine, deterministic risk-policy modeling, a reproducible degradation simulator, empirical benchmarking tools, an interactive Flask web dashboard, and deployment configurations.

---

## 1. Project Overview

Modern secure storage systems demand both confidentiality and data integrity. While authenticated encryption schemes like AES-GCM protect data against unauthorized tampering, they inherently lack fault-tolerance: altering even a single bit in a ciphertext block causes authenticated decryption to fail completely.

The **AREF (Adaptive Redundancy for Encrypted File Recovery)** system bridges this gap. By layering Galois-Field forward error correction over authenticated cryptographic containers, AREF transparently recovers from physical media corruption, burst scratches, and packet dropouts before verifying cryptographic authenticity.

---

## 2. Problem Statement & Motivation

Traditional encryption schemes are brittle in the presence of noisy or degrading channels:
* **The Integrity Paradox:** Authenticated Encryption with Associated Data (AEAD) is deliberately designed to abort whenever ciphertext or authentication tags fail validation.
* **Loss Amplification:** A 1-bit memory flip or a corrupted 512-byte disk sector results in the complete loss of an entire encrypted file.
* **Encryption Does Not Repair:** Encryption protects against eavesdropping and undetected tampering; it possesses zero mathematical capability to reconstruct damaged information.

AREF addresses this vulnerability by systematically integrating Reed–Solomon forward error correction at the block level, ensuring authenticated recovery when data suffers channel degradation while maintaining zero trust against active adversaries.

---

## 3. Core Features

* **Authenticated Symmetric Protection:** AES-256-GCM encryption with 128-bit authentication tags.
* **Hardened Key Derivation:** Passphrase-based key stretching using NIST-recommended memory-hard `scrypt` ($N=16384, r=8, p=1$).
* **IV/Nonce Uniqueness:** Guaranteed per-block unique 96-bit nonces derived from a master nonce and monotonic counter.
* **Three Redundancy Modes:**
  * `none`: 0% parity baseline.
  * `fixed`: Static RS(255, 223) with 32 parity symbols (~15.9% parity overhead).
  * `adaptive`: Deterministically chooses between 16, 32, or 64 parity symbols based on payload scale, risk tier, and Shannon entropy.
* **Zero Silent Acceptance:** Cryptographically enforces that damaged or miscorrected data is never accepted as valid without passing 128-bit AES-GCM tag verification.
* **Degradation Simulator:** Deterministic simulation of random byte flips, bit flips, contiguous burst damage, erased blocks, file truncation, and tag tampering.
* **Empirical Benchmarking & Analytics:** Generates reproducible CSV ledgers, summary JSON reports, and publication-ready Matplotlib charts.
* **Interactive Web Dashboard:** Modern, responsive UI built with Flask, HTML5, CSS3, and JavaScript featuring a live sandbox simulator, analytics view, and filterable recovery ledger.

---

## 4. Architecture & Data Flow

```
 Plaintext Input
       │
       ▼
 [Entropy & Size Analysis] ──► [Adaptive Policy Engine]
       │                                  │ (selects nsym & block capacity)
       ▼                                  ▼
 [Plaintext Chunking] ◄───────────────────┘
       │
       ▼
 [AES-256-GCM Encryption] ──► (Generates Unique Nonce, Tag, & AAD per block)
       │
       ▼
 [Reed-Solomon Codeword Generation] ──► (Computes nsym parity bytes over Header + Tag + Ciphertext)
       │
       ▼
 [.aref Binary Container Assembly]
       │
       ▼ (Channel Transmission / Environmental Noise)
       │
 [Container Header Validation] ──► (HMAC & RS Header Correction)
       │
       ▼
 [Block-Level Reed-Solomon Correction] ──► (Repairs up to ⌊nsym/2⌋ errors or nsym erasures)
       │
       ▼
 [AES-256-GCM Tag Verification]
       ├── Valid Tag   ──► Accepted Reconstructed Plaintext (Exact / Partial)
       └── Invalid Tag ──► Safely Rejected / Marked Lost (Zero Silent Acceptance)
```

---

## 5. AES-GCM and Reed–Solomon Integration

### AES-256-GCM (Galois/Counter Mode)
AES-GCM combines counter-mode encryption (providing confidentiality) with GMAC authentication (providing authenticity and integrity). Every block is bound to its index and byte length using Associated Authenticated Data (AAD):
$$\text{AAD}_i = \text{uint32}(i) \parallel \text{uint16}(\text{length}_i)$$

### Reed–Solomon Error Correction GF($2^8$)
Reed–Solomon operates over symbols of 8 bits (bytes). For a codeword of length $n = 255$ with $k$ data bytes and $p = n - k$ parity bytes:
* **Unknown Random Errors:** Corrects up to $t = \lfloor p / 2 \rfloor$ corrupted bytes.
* **Known Erasures:** Corrects up to $e = p$ missing bytes where position is known.
* **General Bound:** $2t + e \le p$.

---

## 6. Fixed vs. Adaptive Redundancy

* **Fixed Redundancy:** Employs static RS(255, 223) parameters ($p = 32$) across all files regardless of size or environment. While effective for standard files, it wastes storage on ultra-stable media and under-protects small files where a single burst defect destroys a critical percentage of blocks.
* **Adaptive Redundancy:** Evaluates observable file metadata and channel context prior to transmission:
  * **Low Risk ($p=16$):** Local NVMe/SSD, high-reliability links. Overhead: ~7.4%. Corrects up to 8 byte flips per block.
  * **Medium Risk ($p=32$):** Standard networked cloud storage. Overhead: ~15.9%. Corrects up to 16 byte flips per block.
  * **High Risk ($p=64$):** Deep archival tape, lossy wireless/satellite links. Overhead: ~37.9%. Corrects up to 32 byte flips per block.

---

## 7. Adaptive Policy Assumptions & Limitations

1. **Pre-Transmission Only:** The policy makes decisions strictly based on pre-transmission properties (file size, requested risk profile, and Shannon entropy). It possesses no foreknowledge of corruption patterns.
2. **Entropy Elevation:** Files with Shannon entropy $\ge 7.2$ bits/byte (compressed archives, image containers) receive elevated protection because compressed formats exhibit catastrophic cascading failures upon single-byte corruption.
3. **Small Payload Penalty:** Files $< 2\,\text{KB}$ are automatically elevated by one tier to mitigate small-sample vulnerability.
4. **Limitations:** The adaptive policy cannot predict adversarial intent or catastrophic media destruction exceeding maximum theoretical Galois field limits.

---

## 8. Threat Model & Security Considerations

| Threat | Mechanism | AREF Mitigation |
|---|---|---|
| **Passive Channel Noise** | Cosmic ray flips, bit rot | Reed-Solomon corrects up to $\lfloor nsym/2 \rfloor$ bytes per block before decryption. |
| **Active Ciphertext Tampering** | Adversary alters bytes | If alterations exceed RS capacity, AES-GCM tag verification fails and rejects the block. |
| **False-Positive Miscorrection** | RS decoder lands on valid polynomial | AES-GCM 128-bit authentication tag verification fails with probability $1 - 2^{-128}$. |
| **Replay / Block Swapping** | Adversary swaps block orders | Per-block nonces and AAD binding prevent block reordering and splicing. |
| **Metadata Forgery** | Header manipulation | Container header is protected by 16 parity bytes and a 16-byte HMAC tag. |

---

## 9. Supported Corruption Scenarios

1. `random_bytes`: Random byte flips distributed throughout payload.
2. `random_bits`: Single-bit inversions simulating memory bit rot.
3. `burst_damage`: Contiguous scratch or sector defect simulating media damage.
4. `missing_blocks`: Frame/packet erasure simulating dropped network frames.
5. `truncated_file`: Premature file truncation simulating interrupted transfers.
6. `modify_header`: Targeted tampering of magic bytes and container metadata.
7. `modify_auth_tags`: Direct modification of cryptographic authentication tags.

---

## 10. Technology Stack

* **Language:** Python 3.11+
* **Web Framework:** Flask 3.1+
* **Production Server:** Gunicorn 26.2+
* **Cryptography:** `cryptography` (AES-256-GCM, scrypt KDF)
* **Error Correction:** `reedsolo` (Pure-Python & C-optimized Galois Field RS codec)
* **Numerics & Analytics:** NumPy, Matplotlib
* **Testing:** pytest
* **Frontend:** HTML5, CSS3 (Modern Responsive Dark Theme), Vanilla JavaScript

---

## 11. Repository Structure

```
adaptive-file-recovery/
├── app.py                     # Flask web server and REST API endpoints
├── crypto_engine.py           # AES-256-GCM and scrypt KDF implementation
├── file_format.py             # Binary container (.aref) serialization & parser
├── redundancy.py              # Redundancy packaging engine
├── adaptive_policy.py         # Deterministic risk-based policy engine
├── corruption.py              # Reproducible degradation & corruption simulator
├── recovery.py                # Staged error-correction & verification engine
├── benchmark.py               # Systematic benchmark suite & chart generator
├── metrics.py                 # Mathematical metrics evaluator & ledger aggregator
├── requirements.txt           # Pinned production dependencies
├── Procfile                   # Process file for PaaS deployment
├── runtime.txt                # Python runtime specification
├── pytest.ini                 # Pytest configuration
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore configuration
├── templates/
│   └── index.html             # Responsive web dashboard
├── static/
│   ├── css/
│   │   └── style.css          # Modern dark-mode styling
│   └── js/
│       └── app.js             # Interactive frontend client
├── tests/
│   └── test_core.py           # Automated test suite (20 tests)
├── experiments/               # Sample evaluation files
├── results/                   # Generated charts, CSVs, and JSON reports
│   └── .gitkeep
└── docs/
    └── architecture.md        # Technical architecture & threat model
```

---

## 12. Prerequisites

* **Python:** Version 3.11, 3.12, 3.13, or 3.14.
* **Package Manager:** `pip` (v23.0+)
* **Operating System:** macOS, Linux (Ubuntu/Debian/RHEL), or Windows (10/11 / WSL2).

---

## 13. Installation & Virtual Environment Setup

### macOS & Linux

```bash
# 1. Clone or navigate to the project directory
cd "CryptoMend"

# 2. Create a virtual environment
python3 -m venv .venv

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
# 1. Navigate to the project directory
cd adaptive-file-recovery

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 14. Commands to Run Tests

Run the full automated test suite using pytest:

```bash
python -m pytest -v
```

All 20 tests validate:
* Key derivation determinism and unique block nonces.
* AES-GCM encryption and decryption round trips.
* Tamper detection and wrong-passphrase rejection.
* Adaptive policy determinism and entropy elevation.
* Container header serialization, validation, and HMAC tampering.
* Recovery from correctable random byte flips and burst scratches.
* Safe rejection when corruption exceeds Reed-Solomon capacity.
* Missing block erasure identification.
* Strict zero silent incorrect acceptance.
* Web health check, summary, and simulation API endpoints.

---

## 15. Commands to Execute Benchmarks

To execute the matched-pair empirical benchmark and regenerate all charts and ledgers:

```bash
python benchmark.py
```

### Generated Artifacts in `results/`:
* `results/benchmark_results.csv`: Summary metrics table across strategies.
* `results/benchmark_results.json`: Machine-readable benchmark report with execution timestamps.
* `results/recovery_ledger.csv`: Granular trial-by-trial audit ledger.
* `results/recovery_rate_by_strategy.png`: Outcome distribution (Exact vs Partial vs Rejected).
* `results/recovery_vs_severity.png`: Degradation curve as corruption severity scales.
* `results/storage_overhead_comparison.png`: Bar chart of storage overhead percentages.
* `results/encoding_recovery_time.png`: Runtime comparison of encoding vs recovery duration.

---

## 16. Commands to Run the Application Locally

### Development Mode

```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:5001`**

### Production Mode (Gunicorn)

```bash
gunicorn app:app --workers 4 --bind 0.0.0.0:5001 --timeout 120
```

---

## 17. Git Initialization & Push to GitHub

To publish this project to your GitHub account:

```bash
# 1. Initialize git repository
git init -b main

# 2. Add all tracked files
git add .

# 3. Create initial commit
git commit -m "feat: complete adaptive redundancy encrypted file recovery framework"

# 4. Add your GitHub remote repository
git remote add origin https://github.com/bshravyardy-maker/CryptoMend.git

# 5. Push to GitHub
git push -u origin main
```

---

## 18. Deployment Preparation

The application is prepared for deployment to any standard Python PaaS (Render, Fly.io, Railway, Heroku, AWS App Runner):

### Environment Variables
Configure the following in your hosting provider's dashboard:
* `PORT`: Port exposed by the host (default: `5001`).
* `SECRET_KEY`: High-entropy random string for session encryption.
* `FLASK_ENV`: Set to `production`.
* `FLASK_DEBUG`: Set to `0`.
* `MPLCONFIGDIR`: Set to `/tmp/matplotlib_aref` to ensure writable font cache on read-only container filesystems.

### Production Procfile
Included in repository:
```text
web: gunicorn app:app --workers 4 --bind 0.0.0.0:$PORT --timeout 120
```

### Health Check Endpoint
* `GET /health` returns HTTP 200 `{"status": "healthy", "service": "adaptive-redundancy-recovery", "version": "1.0.0"}` for orchestrator readiness and liveness probes.

---

## 19. Privacy & Upload Safeguards

* **Upload Limit:** Maximum upload size is strictly capped at 16 MB. Interactive simulator payload is capped at 2 MB.
* **Ephemeral In-Memory Handling:** Uploaded payloads are processed in memory and never written to permanent disk storage.
* **Zero Secret Logging:** Passphrases, salts, nonces, and decrypted plaintexts are never printed to server logs.
* **Sanitized Filenames:** Handled exclusively via `werkzeug.utils.secure_filename` to prevent path traversal attacks.

---

## 20. Known Limitations & Future Improvements

### Known Limitations
* **Reed–Solomon Symbol Size:** Operates on standard $GF(2^8)$ (255-byte codewords). Files larger than 200 bytes are chunked into multiple blocks rather than encoded in a single monolithic codeword.
* **Extreme Corruption:** If corruption destroys more than $\lfloor nsym / 2 \rfloor$ bytes in every block or irrecoverably destroys the container header, the file is safely rejected.

### Future Improvements
* **Extended Galois Fields:** Implement $GF(2^{16})$ for 65,535-byte codewords to reduce block framing overhead on very large files.
* **Low-Density Parity-Check (LDPC) Codes:** Explore LDPC or Fountain codes (e.g., RaptorQ) for multi-gigabyte archival streaming.
* **Hardware Acceleration:** Integrate AES-NI and SIMD-accelerated Galois field matrix multiplication for gigabit-throughput operations.

---

## 21. License & Contributions

This project is distributed under the MIT License. Contributions, issues, and feature requests are welcome via pull requests.
