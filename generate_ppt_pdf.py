"""Script to generate a 20-slide presentation PDF for CryptoMend in warm tones."""

import os
from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# 16:9 Widescreen dimensions: 13.33 x 7.5 inches = 960 x 540 points
PAGE_WIDTH = 960
PAGE_HEIGHT = 540
PAGE_SIZE = (PAGE_WIDTH, PAGE_HEIGHT)

# Warm Color Palette
BG_WARM = colors.HexColor("#FAF7F2")        # Warm cream / linen background
CARD_WARM = colors.HexColor("#FFFFFF")      # Clean white card surface
BORDER_WARM = colors.HexColor("#E8DBCF")    # Warm soft border
PRIMARY_WARM = colors.HexColor("#9C4221")   # Deep terracotta / burnt sienna
ACCENT_AMBER = colors.HexColor("#C05621")   # Warm amber-orange
ACCENT_GOLD = colors.HexColor("#B45309")    # Deep golden ochre
TEXT_DARK = colors.HexColor("#2D231E")      # Espresso / dark charcoal brown
TEXT_MUTED = colors.HexColor("#786458")     # Warm slate brown
PILL_BG = colors.HexColor("#FDF0E7")        # Warm terracotta tint
PILL_BORDER = colors.HexColor("#F4CBB7")    # Tint border
SUCCESS_GREEN = colors.HexColor("#2E7D32")  # Warm forest green
HIGHLIGHT_BG = colors.HexColor("#FFFBEB")   # Warm amber highlight
HIGHLIGHT_BORDER = colors.HexColor("#FDE68A")


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for background, top header line, and footer with slide counter."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        page_num = self._pageNumber

        # Draw warm background
        self.saveState()
        self.setFillColor(BG_WARM)
        self.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)

        # Title slide decoration vs content slides
        if page_num == 1:
            # Elegant warm geometric accents for title slide
            self.setFillColor(PRIMARY_WARM)
            self.rect(0, 0, 18, PAGE_HEIGHT, fill=True, stroke=False)
            self.setFillColor(ACCENT_AMBER)
            self.rect(18, 0, 8, PAGE_HEIGHT, fill=True, stroke=False)
            self.setFillColor(ACCENT_GOLD)
            self.rect(26, 0, 4, PAGE_HEIGHT, fill=True, stroke=False)

            # Warm decorative bar at bottom
            self.setFillColor(colors.HexColor("#EFE4D6"))
            self.rect(0, 0, PAGE_WIDTH, 40, fill=True, stroke=False)
            self.setFillColor(TEXT_MUTED)
            self.setFont("Helvetica", 10)
            self.drawString(50, 15, "Confidential Project Presentation  |  Department of Computer Science & Engineering")
            self.drawRightString(PAGE_WIDTH - 50, 15, "Academic Year 2026")
        else:
            # Top thin accent line
            self.setFillColor(PRIMARY_WARM)
            self.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=True, stroke=False)
            self.setFillColor(ACCENT_AMBER)
            self.rect(40, PAGE_HEIGHT - 6, 120, 6, fill=True, stroke=False)

            # Footer
            self.setStrokeColor(BORDER_WARM)
            self.setLineWidth(0.8)
            self.line(40, 36, PAGE_WIDTH - 40, 36)

            self.setFillColor(TEXT_MUTED)
            self.setFont("Helvetica-Bold", 9)
            self.drawString(40, 20, "CryptoMend : Adaptive Redundancy for Encrypted File Recovery")
            self.setFont("Helvetica", 9)
            self.drawString(380, 20, "B. Shravya Reddy (24R11A6204)  |  K. Manasa (25R15A6204)")

            # Slide Number Pill
            pill_text = f"Slide {page_num} of {total_pages}"
            self.setFont("Helvetica-Bold", 9)
            self.setFillColor(PRIMARY_WARM)
            self.drawRightString(PAGE_WIDTH - 40, 20, pill_text)

        self.restoreState()


def create_presentation(output_pdf: str):
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=PAGE_SIZE,
        leftMargin=50,
        rightMargin=50,
        topMargin=40,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=32,
        leading=38,
        textColor=PRIMARY_WARM,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        fontName="Helvetica",
        fontSize=17,
        leading=22,
        textColor=TEXT_DARK,
        spaceAfter=20
    )

    slide_header_style = ParagraphStyle(
        "SlideHeader",
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=26,
        textColor=PRIMARY_WARM,
        spaceAfter=3
    )

    slide_sub_style = ParagraphStyle(
        "SlideSubHeader",
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=TEXT_MUTED,
        spaceAfter=14
    )

    card_title_style = ParagraphStyle(
        "CardTitle",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=PRIMARY_WARM,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodyDark",
        fontName="Helvetica",
        fontSize=10,
        leading=14.5,
        textColor=TEXT_DARK,
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        "BodyDarkBold",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14.5,
        textColor=TEXT_DARK
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_DARK,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        "CodeText",
        fontName="Courier-Bold",
        fontSize=9,
        leading=12,
        textColor=PRIMARY_WARM
    )

    pill_style = ParagraphStyle(
        "PillText",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=PRIMARY_WARM
    )

    story = []

    def make_card(header_text, items, width=410, min_height=140):
        flowables = [Paragraph(f"<b>{header_text}</b>", card_title_style)]
        for item in items:
            flowables.append(Paragraph(f"• {item}", bullet_style))
        t = Table([[flowables]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_WARM),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_WARM),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        return t

    def make_stat_box(val, label, subtext, width=200):
        p1 = Paragraph(f"<font color='{PRIMARY_WARM.hexval()}'><b>{val}</b></font>", ParagraphStyle('StatV', fontName='Helvetica-Bold', fontSize=22, leading=24, alignment=1))
        p2 = Paragraph(f"<b>{label}</b>", ParagraphStyle('StatL', fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=1, textColor=TEXT_DARK))
        p3 = Paragraph(f"{subtext}", ParagraphStyle('StatS', fontName='Helvetica', fontSize=8, leading=10, alignment=1, textColor=TEXT_MUTED))
        t = Table([[p1], [p2], [p3]], colWidths=[width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_WARM),
            ('BOX', (0, 0), (-1, -1), 1, BORDER_WARM),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        return t

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("CryptoMend: Adaptive Redundancy for Encrypted File Recovery", title_style))
    story.append(Paragraph("Resilient Authenticated Encryption with Layered Galois-Field Forward Error Correction", subtitle_style))
    story.append(Spacer(1, 15))

    # Presenters Card
    pres_p1 = Paragraph("<b>PROJECT PRESENTATION</b>", ParagraphStyle('PresH', fontName='Helvetica-Bold', fontSize=10, textColor=ACCENT_AMBER, spaceAfter=8))
    pres_p2 = Paragraph("<b>Presented By:</b>", ParagraphStyle('PresB', fontName='Helvetica-Bold', fontSize=11, textColor=PRIMARY_WARM, spaceAfter=4))
    pres_p3 = Paragraph("<b>1. B. Shravya Reddy</b> &nbsp;&nbsp;|&nbsp;&nbsp; Roll No: <b>24R11A6204</b>", ParagraphStyle('Pres1', fontName='Helvetica', fontSize=12, leading=16, textColor=TEXT_DARK))
    pres_p4 = Paragraph("<b>2. K. Manasa</b> &nbsp;&nbsp;|&nbsp;&nbsp; Roll No: <b>25R15A6204</b>", ParagraphStyle('Pres2', fontName='Helvetica', fontSize=12, leading=16, textColor=TEXT_DARK))

    pres_card = Table([[pres_p1], [pres_p2], [pres_p3], [pres_p4]], colWidths=[520])
    pres_card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_WARM),
        ('BOX', (0, 0), (-1, -1), 1.5, BORDER_WARM),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
    ]))

    story.append(pres_card)
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Keywords:</b> AES-256-GCM &bull; Reed–Solomon GF(2⁸) &bull; scrypt KDF &bull; Zero Silent Acceptance &bull; Adaptive Policy", ParagraphStyle('Kw', fontName='Helvetica', fontSize=9, textColor=TEXT_MUTED)))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 2: Executive Summary & Motivation
    # =========================================================================
    story.append(Paragraph("1. Executive Summary & Problem Motivation", slide_header_style))
    story.append(Paragraph("The fundamental conflict between cryptographic integrity and physical channel fault tolerance.", slide_sub_style))

    c1 = make_card("The Traditional Storage Vulnerability", [
        "Modern cloud, wireless, and deep archival systems inevitably suffer from <b>channel degradation</b>: bit rot, cosmic-ray flips, and burst sector loss.",
        "Traditional storage applies authenticated encryption (AEAD like AES-GCM) to protect against eavesdropping and malicious tampering.",
        "<b>Catastrophic Loss:</b> If even 1 single bit flips in a 10 MB ciphertext, standard AEAD immediately aborts decryption, destroying 100% of the data."
    ], width=420)

    c2 = make_card("The CryptoMend Breakthrough", [
        "<b>Encryption never repairs data:</b> Confidentiality ciphers have zero mathematical capability to mend damaged bits.",
        "CryptoMend introduces a <b>staged error-correction boundary</b> combining AES-256-GCM with context-adaptive Reed–Solomon coding.",
        "<b>Self-Mending Resilience:</b> Transparently heals physical corruption before authentication, guaranteeing <b>0.0% silent incorrect acceptance</b>."
    ], width=420)

    t_s2 = Table([[c1, c2]], colWidths=[430, 430])
    t_s2.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(t_s2)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 3: Problem Formulation: The Fragility of Encrypted Data
    # =========================================================================
    story.append(Paragraph("2. Problem Formulation: The Integrity Paradox", slide_header_style))
    story.append(Paragraph("Why authenticated ciphers fail catastrophically in noisy environments.", slide_sub_style))

    c1 = make_card("Plaintext Degradation vs. Ciphertext Fragility", [
        "<b>Plaintext Fault Tolerance:</b> A corrupted byte in an unencrypted ASCII log or JPEG image usually causes a minor, isolated glitch.",
        "<b>Ciphertext Fragility (AEAD Paradox):</b> In AES-GCM or ChaCha20-Poly1305, alteration of any ciphertext byte scrambles the GMAC tag calculation.",
        "<b>All-or-Nothing Decryption:</b> The verification algorithm cannot differentiate between a harmless physical cosmic-ray bit-flip and an active cyberattack."
    ], width=420)

    c2 = make_card("Real-World Consequence Scenarios", [
        "<b>Flash Memory Wear:</b> NAND flash gate leakage causes single-bit flips over retention periods.",
        "<b>Deep Archival Tape:</b> Magnetic oxide degradation causes localized burst scratches.",
        "<b>Tactical Wireless Links:</b> High packet jitter and dropouts in hostile network channels.",
        "<b>Mission Outcome:</b> Total mission data loss despite 99.99% of original bits surviving intact."
    ], width=420)

    t_s3 = Table([[c1, c2]], colWidths=[430, 430])
    story.append(t_s3)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 4: Project Objectives & Innovations
    # =========================================================================
    story.append(Paragraph("3. Core Project Objectives & Key Contributions", slide_header_style))
    story.append(Paragraph("Architecting an authenticated, fault-tolerant, and adaptive encrypted recovery ecosystem.", slide_sub_style))

    c1 = make_card("Primary Engineering Objectives", [
        "<b>1. Layered Self-Healing:</b> Design a defensible container format where error correction repairs transmission noise before cryptographic decryption.",
        "<b>2. Dynamic Context Adaptation:</b> Construct an adaptive policy engine that chooses redundancy tiers based on pre-transmission context without future knowledge.",
        "<b>3. Zero Silent Acceptance:</b> Enforce 100% cryptographic tag validation so no corrupted file is ever silently accepted as authentic."
    ], width=420)

    c2 = make_card("Measurable Deliverables Achieved", [
        "<b>Working Software Framework:</b> Fully tested Python 3.11+ implementation with Flask dashboard, automated tests, and benchmark engine.",
        "<b>Empirical Verification:</b> 63 matched-pair trials proving recovery rates jump from 14.3% (baseline) to 33.3% (adaptive) with <b>0.0% silent error</b>.",
        "<b>Deployable Architecture:</b> GitHub-ready repository with Gunicorn server, Dockerfile, and Render Blueprint."
    ], width=420)

    t_s4 = Table([[c1, c2]], colWidths=[430, 430])
    story.append(t_s4)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 5: High-Level Architecture & Layered Dataflow
    # =========================================================================
    story.append(Paragraph("4. System Architecture & Layered Dataflow", slide_header_style))
    story.append(Paragraph("Strict boundary separation between cryptographic authentication and channel coding.", slide_sub_style))

    flow_box = [
        Paragraph("<b>ENCODING PIPELINE:</b><br/>"
                  "Plaintext &rarr; Chunking ($D$ bytes) &rarr; AES-256-GCM (Unique IV, AAD) &rarr; "
                  "Codeword assembly &rarr; RS Encoding ($nsym$ Parity) &rarr; .aref Container", body_style),
        Spacer(1, 6),
        Paragraph("<b>CHANNEL DEGRADATION (Simulated or Real):</b><br/>"
                  "Noise, Bit Rot, Contiguous Burst Scratches, Missing Frames, Adversarial Tampering", body_style),
        Spacer(1, 6),
        Paragraph("<b>RECOVERY PIPELINE:</b><br/>"
                  ".aref Container &rarr; Header ECC & HMAC Check &rarr; Frame Extraction &rarr; "
                  "Reed–Solomon Error/Erasure Repair &rarr; AES-GCM Tag Verification &rarr; Reconstructed Plaintext", body_style)
    ]
    t_flow = Table([[flow_box]], colWidths=[860])
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_WARM),
        ('BOX', (0, 0), (-1, -1), 1.2, BORDER_WARM),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 10))

    c1 = make_card("Why Encode Over Ciphertext?", [
        "Encrypt-then-Code ensures parity symbols protect ciphertext and metadata.",
        "Parity contains <b>zero plaintext information</b>, preserving complete semantic security."
    ], width=420)
    c2 = make_card("Zero Trust on Reconstructed Blocks", [
        "Reed–Solomon repair is treated as an <b>untrusted suggestion</b>.",
        "Plaintext is rejected unless the 128-bit AES-GCM authentication tag verifies successfully."
    ], width=420)
    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 6: Cryptographic Engine: AES-256-GCM
    # =========================================================================
    story.append(Paragraph("5. Cryptographic Core: AES-256-GCM", slide_header_style))
    story.append(Paragraph("Authenticated Symmetric Protection with Associated Authenticated Data (AAD).", slide_sub_style))

    c1 = make_card("Galois/Counter Mode Mechanics", [
        "<b>Confidentiality:</b> AES-256 in CTR mode encrypts plaintext blocks via keystream XOR.",
        "<b>Authenticity (GMAC):</b> Computes a 128-bit polynomial MAC over ciphertext and Associated Authenticated Data (AAD) in Galois Field $GF(2^{128})$.",
        "<b>Cryptographic Strength:</b> 256-bit symmetric security level resistent to modern quantum and classical cryptanalytic attacks."
    ], width=420)

    c2 = make_card("Associated Authenticated Data (AAD) Binding", [
        "<b>Format:</b> $\\text{AAD}_i = \\text{uint32}(i) \\parallel \\text{uint16}(\\text{length}_i)$.",
        "<b>Replay Defense:</b> Binds block index directly into the authentication tag.",
        "<b>Frame Swapping Prevention:</b> Attackers cannot reorder blocks, duplicate frames, or splice data from another file without tag failure."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 7: Key Derivation Function: scrypt
    # =========================================================================
    story.append(Paragraph("6. Key Derivation: Memory-Hard scrypt KDF", slide_header_style))
    story.append(Paragraph("Resilience against GPU/ASIC dictionary and brute-force password cracking.", slide_sub_style))

    c1 = make_card("scrypt KDF Configuration (RFC 7914)", [
        "<b>CPU/Memory Cost ($N$):</b> 16,384 ($2^{14}$ iterations) &mdash; NIST recommended.",
        "<b>Block Size Parameter ($r$):</b> 8 sequential memory blocks.",
        "<b>Parallelization Parameter ($p$):</b> 1 independent execution thread.",
        "<b>Output Key Length:</b> 32 bytes (256-bit symmetric AES key).",
        "<b>Random Salt:</b> 16 cryptographically secure random bytes (`os.urandom(16)`)."
    ], width=420)

    c2 = make_card("Why Not PBKDF2 or SHA-256?", [
        "<b>GPU Acceleration Threat:</b> Standard SHA-256 or PBKDF2 can be computed billions of times per second on commodity hardware.",
        "<b>Memory Hardness:</b> scrypt forces attackers to allocate large memory buffers (16 MB per guess), neutralizing massive parallel ASIC arrays.",
        "<b>Salt Isolation:</b> Two identical passphrases generate completely distinct keys."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 8: Deterministic IV & Nonce Management
    # =========================================================================
    story.append(Paragraph("7. IV Management: Deterministic Zero-Reuse", slide_header_style))
    story.append(Paragraph("Guaranteeing that no two blocks ever share a cryptographic nonce under the same key.", slide_sub_style))

    c1 = make_card("The Nonce-Reuse Disaster in AES-GCM", [
        "<b>The Cryptographic Catastrophe:</b> Reusing a nonce with the same key in AES-GCM destroys the authenticator completely.",
        "An adversary can compute the secret polynomial authentication hash key $H$, allowing them to forge tags and alter ciphertexts arbitrarily.",
        "<b>Requirement:</b> Nonce uniqueness must be strictly guaranteed across all blocks in all files."
    ], width=420)

    c2 = make_card("CryptoMend's Monotonic Derivation Scheme", [
        "<b>Master Nonce:</b> 12 random bytes generated per file container.",
        "<b>Block Nonce Derivation:</b><br/>"
        "$\\text{Nonce}_i = \\text{Master}[0..8] \\parallel (\\text{Master}[8..12] \\oplus \\text{uint32}(i))$",
        "<b>Uniqueness Guarantee:</b> Monotonic counter ensures mathematically zero probability of IV collision across up to $2^{32}$ ($4.29$ billion) blocks."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 9: Forward Error Correction: Reed–Solomon GF(2^8)
    # =========================================================================
    story.append(Paragraph("8. Forward Error Correction: Reed–Solomon GF(2⁸)", slide_header_style))
    story.append(Paragraph("Algebraic byte-level error correction over Galois Field polynomials.", slide_sub_style))

    c1 = make_card("Galois Field GF(2⁸) Mechanics", [
        "<b>Symbol Unit:</b> Each symbol is an 8-bit byte ($0 \\dots 255$).",
        "<b>Maximum Codeword Length ($n$):</b> $2^8 - 1 = 255$ symbols per block.",
        "<b>Data Symbols ($k$):</b> Usable payload capacity $k = n - nsym$.",
        "<b>Parity Symbols ($nsym$):</b> Evaluated polynomials appended to the block payload."
    ], width=420)

    c2 = make_card("Mathematical Correction Limits", [
        "<b>Unknown Errors ($t$):</b> Corrects up to $t = \\lfloor nsym / 2 \\rfloor$ corrupted bytes at unknown offsets.",
        "<b>Known Erasures ($e$):</b> Corrects up to $e = nsym$ missing bytes at known offsets.",
        "<b>Combined Capability:</b> Correctable if and only if: $2t + e \\le nsym$.",
        "<b>Optimal Distance:</b> Reed–Solomon achieves the Singleton bound (MDS code)."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 10: The Three Redundancy Strategies Compared
    # =========================================================================
    story.append(Paragraph("9. Redundancy Strategies: None vs. Fixed vs. Adaptive", slide_header_style))
    story.append(Paragraph("Comparative architectural models for error correction allocation.", slide_sub_style))

    c1 = make_card("1. None (Baseline) & 2. Fixed RS", [
        "<b>Strategy 'none' (Baseline):</b><br/>"
        "&bull; Parity: $0$ bytes ($nsym = 0$).<br/>"
        "&bull; Overhead: Format headers only (~27%).<br/>"
        "&bull; Recovery: $0$ byte resilience. Any bit flip causes fatal reject.",
        "<br/><b>Strategy 'fixed' (Static RS-32):</b><br/>"
        "&bull; Parity: Static $32$ parity bytes per block across all files.<br/>"
        "&bull; Recovery Capacity: 16 symbol errors or 32 erasures per block.<br/>"
        "&bull; Limitation: Over-allocates on safe storage; under-protects small files."
    ], width=420)

    c2 = make_card("3. Strategy 'adaptive' (Dynamic)", [
        "<b>Context-Driven Allocation:</b> Automatically selects low ($16$), medium ($32$), or high ($64$) parity symbols based on environmental risk assumptions.",
        "<b>Micro-Payload Elevation:</b> Automatically escalates small files ($< 2$ KB) to higher tiers because losing 1 block destroys 25%&ndash;100% of data.",
        "<b>Brittle Stream Defense:</b> High Shannon entropy data receives elevated parity to prevent decompressor crash cascades."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 11: The Adaptive Policy Engine
    # =========================================================================
    story.append(Paragraph("10. Adaptive Policy: Deterministic Context Evaluation", slide_header_style))
    story.append(Paragraph("Documented risk modeling operating strictly without foresight into future error positions.", slide_sub_style))

    c1 = make_card("Documented Risk Assumptions", [
        "<b>1. Pre-Transmission Observability:</b> Operates strictly on payload length, requested storage profile, and Shannon entropy.",
        "<b>2. Zero Foresight Principle:</b> Never accesses benchmark error locations or simulated channel parameters.",
        "<b>3. Small-File Fragility:</b> Large files distribute risks across hundreds of blocks; small files (1&ndash;5 blocks) face catastrophic failure from a single defect."
    ], width=420)

    c2 = make_card("Policy Decision Tiers", [
        "<b>Low Risk Profile:</b> Local NVMe/SSD, high reliability ($nsym=16$, ~7% parity overhead, $t=8$).",
        "<b>Medium Risk Profile:</b> Cloud transit, networked storage ($nsym=32$, ~16% parity overhead, $t=16$).",
        "<b>High Risk Profile:</b> Hostile channel, satellite, magnetic tape ($nsym=64$, ~38% parity overhead, $t=32$).",
        "<b>Deterministic Guarantee:</b> Identical inputs yield identical decisions."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 12: Binary File Format Specification (.aref)
    # =========================================================================
    story.append(Paragraph("11. Binary Container Format (.aref Specification)", slide_header_style))
    story.append(Paragraph("Versioned container layout with dual-layer header protection.", slide_sub_style))

    fmt_data = [
        [Paragraph("<b>Offset</b>", body_bold), Paragraph("<b>Field</b>", body_bold), Paragraph("<b>Size</b>", body_bold), Paragraph("<b>Purpose</b>", body_bold)],
        [Paragraph("0..3", body_style), Paragraph("Magic Signature", body_style), Paragraph("4 Bytes", body_style), Paragraph("Fixed ASCII `AREF`", body_style)],
        [Paragraph("4..7", body_style), Paragraph("Version & Policy", body_style), Paragraph("4 Bytes", body_style), Paragraph("Version (0x01), Strategy ID, Risk Tier, nsym", body_style)],
        [Paragraph("8..19", body_style), Paragraph("Lengths & Blocks", body_style), Paragraph("12 Bytes", body_style), Paragraph("uint64 plaintext size, uint32 total blocks", body_style)],
        [Paragraph("20..47", body_style), Paragraph("Salt & Master IV", body_style), Paragraph("28 Bytes", body_style), Paragraph("16B scrypt salt, 12B master AES-GCM nonce", body_style)],
        [Paragraph("48..63", body_style), Paragraph("Header RS Parity", body_style), Paragraph("16 Bytes", body_style), Paragraph("Reed–Solomon parity (corrects 8 byte flips in header)", body_style)],
        [Paragraph("64..79", body_style), Paragraph("Header HMAC Tag", body_style), Paragraph("16 Bytes", body_style), Paragraph("HMAC-SHA256 authentication tag over header", body_style)],
        [Paragraph("80..End", body_style), Paragraph("Block Frames", body_style), Paragraph("Variable", body_style), Paragraph("uint16 length prefix + RS Codeword per block", body_style)],
    ]
    t_fmt = Table(fmt_data, colWidths=[80, 160, 90, 530])
    t_fmt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HIGHLIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_WARM),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('BACKGROUND', (0, 1), (-1, -1), CARD_WARM),
    ]))
    story.append(t_fmt)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 13: Staged Recovery Pipeline & Zero-Trust
    # =========================================================================
    story.append(Paragraph("12. Staged Recovery Pipeline & Zero-Trust Verification", slide_header_style))
    story.append(Paragraph("A zero-trust cryptographic boundary prevents corrupted data from entering the application.", slide_sub_style))

    c1 = make_card("Four-Stage Recovery Execution", [
        "<b>Stage 1: Header ECC Repair:</b> Decodes header codeword using RS(48+16). Recovers metadata even if header bytes flipped.",
        "<b>Stage 2: Header HMAC Authentication:</b> Derives key via scrypt; verifies HMAC-SHA256 tag. Rejects tampered files immediately.",
        "<b>Stage 3: Block Framing & Erasure Map:</b> Detects missing block indices (erasures).",
        "<b>Stage 4: Reed–Solomon Decoding:</b> Corrects up to $\\lfloor nsym/2 \\rfloor$ symbol errors per block frame."
    ], width=420)

    c2 = make_card("The Cryptographic Integrity Gate", [
        "<b>Decoupled Trust:</b> Reed–Solomon is non-cryptographic; an uncorrectable pattern could theoretically decode to invalid bytes.",
        "<b>AES-GCM Verification:</b> The AES-256-GCM decryptor checks the 128-bit authentication tag with the per-block nonce and AAD.",
        "<b>Result:</b> If tag check fails, block is marked lost. Reconstructed data is <b>never accepted without cryptographic verification</b>."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 14: Corruption Simulation Engine
    # =========================================================================
    story.append(Paragraph("13. Degradation Simulator: Empirical Testing Models", slide_header_style))
    story.append(Paragraph("Deterministic and reproducible channel degradation injection.", slide_sub_style))

    c1 = make_card("Physical & Transmission Degradation Models", [
        "<b>`random_bytes`:</b> Flips pseudo-random bytes in the payload region (simulating bit rot and cosmic noise).",
        "<b>`random_bits`:</b> Flips individual bits within words (simulating RAM memory retention faults).",
        "<b>`burst_damage`:</b> Injects localized contiguous byte corruption (simulating scratches or bad disk sectors).",
        "<b>`missing_blocks`:</b> Erases entire blocks from the stream (simulating UDP packet loss)."
    ], width=420)

    c2 = make_card("Adversarial & Structural Attack Models", [
        "<b>`truncated_file`:</b> Cuts off file trailing bytes (simulating aborted downloads).",
        "<b>`modify_header`:</b> Directly tampers with magic bytes or version metadata.",
        "<b>`modify_auth_tags`:</b> Inverts bits in cryptographic authentication tags.",
        "<b>Reproducibility:</b> Controlled via deterministic RNG seeds (`seed=42`, `seed=101`)."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 15: Benchmark Methodology & Experimental Setup
    # =========================================================================
    story.append(Paragraph("14. Empirical Benchmark Methodology", slide_header_style))
    story.append(Paragraph("Systematic matched-pair experiments across diverse data formats and corruption profiles.", slide_sub_style))

    c1 = make_card("Controlled Experimental Matrix", [
        "<b>Input File Profiles:</b><br/>"
        "&bull; `mission_log.txt` (1 KB structured text &bull; Shannon entropy 4.6)<br/>"
        "&bull; `sensor_telemetry.bin` (2 KB high-entropy binary &bull; entropy 7.9)<br/>"
        "&bull; `system_manifest.json` (512 B structured JSON configuration)",
        "<b>Strategies Tested:</b> `none`, `fixed`, `adaptive`.",
        "<b>Severities Tested:</b> 1%, 2%, 4%, 5%, 10%, 15% corruption scales."
    ], width=420)

    c2 = make_card("Evaluation Rigor & Non-Fabrication", [
        "<b>Matched Conditions:</b> Every strategy undergoes identical corruption seeds and byte flip positions.",
        "<b>Zero Fabrication Guarantee:</b> All benchmark values recorded directly from physical test executions into `benchmark_results.csv` and `recovery_ledger.csv`.",
        "<b>Total Benchmark Runs:</b> 63 complete encode-corrupt-recover trial iterations."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 16: Benchmark Results: Recovery Rates
    # =========================================================================
    story.append(Paragraph("15. Benchmark Results: Exact Recovery Resilience", slide_header_style))
    story.append(Paragraph("Empirical proof of adaptive forward error correction efficacy.", slide_sub_style))

    s_box1 = make_stat_box("14.3%", "NONE (Baseline)", "Exact 100% Recovery", 270)
    s_box2 = make_stat_box("28.6%", "FIXED (RS-32)", "Exact 100% Recovery", 270)
    s_box3 = make_stat_box("33.3%", "ADAPTIVE", "Exact 100% Recovery (+133%)", 270)

    story.append(Table([[s_box1, s_box2, s_box3]], colWidths=[285, 285, 285]))
    story.append(Spacer(1, 14))

    c1 = make_card("Key Resilience Findings", [
        "<b>Baseline Failure:</b> The `none` strategy failed on 85.7% of corrupted files, surviving only when noise hit non-critical padding bytes.",
        "<b>Fixed Parity Gain:</b> Fixed RS-32 doubled the exact recovery rate to <b>28.6%</b> and achieved 52.4% partial chunk recovery.",
        "<b>Adaptive Dominance:</b> Adaptive policy reached the highest exact recovery rate (<b>33.3%</b>) by selectively escalating high-entropy and micro-payloads."
    ], width=860)
    story.append(c1)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 17: Critical Security Guarantee: Zero Silent Acceptance
    # =========================================================================
    story.append(Paragraph("16. Critical Security Proof: Zero Silent Acceptance", slide_header_style))
    story.append(Paragraph("Eliminating the risk of undetected corruption or false-positive error correction.", slide_sub_style))

    c1 = make_card("What Is Silent Incorrect Acceptance?", [
        "<b>The Danger:</b> A system repairs a damaged file, declares recovery successful, but returns corrupted bytes to the user.",
        "<b>Catastrophic Impact:</b> In medical records, financial ledgers, or avionics, silent false recovery is far more dangerous than an honest error rejection.",
        "<b>RS Reed–Solomon Weakness:</b> If errors exceed $t$, RS decoders can occasionally land on an incorrect valid polynomial."
    ], width=420)

    c2 = make_card("CryptoMend's 0.0% Empirical Guarantee", [
        "<b>128-Bit Tag Verification:</b> Even if RS decoder makes an error, the AES-256-GCM authentication tag catches it with probability $1 - 2^{-128}$.",
        "<b>Measured Outcome:</b> Across all 63 benchmark trials, the silent incorrect acceptance rate was strictly <b>0.00%</b>.",
        "<b>Honest Rejection:</b> Severe corruption is safely marked `REJECTED` or `AUTHENTICATION_FAILURE`."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 18: Storage Overhead & Computational Latency Trade-offs
    # =========================================================================
    story.append(Paragraph("17. Storage Overhead & Computational Latency Trade-offs", slide_header_style))
    story.append(Paragraph("Analyzing the performance costs of forward error correction.", slide_sub_style))

    perf_data = [
        [Paragraph("<b>Strategy</b>", body_bold), Paragraph("<b>Exact Recovery</b>", body_bold), Paragraph("<b>Safe Rejection</b>", body_bold), Paragraph("<b>Silent Errors</b>", body_bold), Paragraph("<b>Avg Overhead</b>", body_bold), Paragraph("<b>Avg Encoding</b>", body_bold), Paragraph("<b>Avg Recovery</b>", body_bold)],
        [Paragraph("<b>none</b> (Baseline)", body_style), Paragraph("14.3%", body_style), Paragraph("47.6%", body_style), Paragraph("<font color='green'><b>0.0%</b></font>", body_style), Paragraph("+27.07%", body_style), Paragraph("74.19 ms", body_style), Paragraph("70.35 ms", body_style)],
        [Paragraph("<b>fixed</b> (RS-32)", body_style), Paragraph("28.6%", body_style), Paragraph("19.1%", body_style), Paragraph("<font color='green'><b>0.0%</b></font>", body_style), Paragraph("+48.48%", body_style), Paragraph("72.52 ms", body_style), Paragraph("75.84 ms", body_style)],
        [Paragraph("<b>adaptive</b> (Dynamic)", body_style), Paragraph("<font color='brown'><b>33.3%</b></font>", body_style), Paragraph("19.1%", body_style), Paragraph("<font color='green'><b>0.0%</b></font>", body_style), Paragraph("+64.95%", body_style), Paragraph("74.17 ms", body_style), Paragraph("79.21 ms", body_style)],
    ]
    t_perf = Table(perf_data, colWidths=[130, 110, 110, 100, 110, 120, 120])
    t_perf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HIGHLIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_WARM),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, -1), CARD_WARM),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#FDF6EE")),
    ]))
    story.append(t_perf)
    story.append(Spacer(1, 10))

    c_takeaway = make_card("Engineering Trade-off Conclusion", [
        "<b>Latency:</b> Reed–Solomon decoding adds less than <b>9 milliseconds</b> of compute overhead per file.",
        "<b>Overhead Justification:</b> The +64% storage overhead in adaptive mode is dominated by container header structures on micro-benchmarks; on larger multi-megabyte payloads, overhead asymptotically approaches the theoretical ~16% to ~38% parity ratio."
    ], width=860)
    story.append(c_takeaway)
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 19: Interactive Dashboard & Web Application Architecture
    # =========================================================================
    story.append(Paragraph("18. Interactive Web Dashboard & RESTful Architecture", slide_header_style))
    story.append(Paragraph("Production-ready interface for live sandbox simulation and audit ledger tracking.", slide_sub_style))

    c1 = make_card("Web Application Capabilities", [
        "<b>Flask REST API:</b> Endpoints for `/health`, `/api/summary`, `/api/ledger`, `/api/export-ledger`, and `/api/simulate`.",
        "<b>Live Degradation Sandbox:</b> Interactive slider controls for corruption severity, degradation models, and passphrases with live hex previews.",
        "<b>Empirical Recovery Ledger:</b> Real-time filtering by strategy, recovery status, and corruption type with live CSV export."
    ], width=420)

    c2 = make_card("DevOps & Production Packaging", [
        "<b>Security Safeguards:</b> Ephemeral in-memory handling up to 16 MB, sanitized filenames, and zero passphrase logging.",
        "<b>Production Server:</b> Served via Gunicorn WSGI with 4 worker processes and request timeouts.",
        "<b>Containerized & Cloud Ready:</b> Packaged with multi-stage `Dockerfile` and automated `render.yaml` Blueprint."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(PageBreak())

    # =========================================================================
    # SLIDE 20: Conclusion, Future Roadmap & Q&A
    # =========================================================================
    story.append(Paragraph("19. Conclusion & Future Roadmap", slide_header_style))
    story.append(Paragraph("Summary of project contributions and prospective advancements.", slide_sub_style))

    c1 = make_card("Summary of Project Contributions", [
        "<b>1. Solved the AEAD Fragility Paradox:</b> Successfully demonstrated that layered Reed–Solomon error correction restores authenticated files without compromising security.",
        "<b>2. Deterministic Adaptive Policy:</b> Proved that risk-aware contextual redundancy maximizes recovery rates while minimizing wasted storage.",
        "<b>3. Zero Silent Error Proof:</b> Verified that authenticated decryption strictly eliminates false recoveries ($0.0\\%$ silent acceptance)."
    ], width=420)

    c2 = make_card("Future Technical Extensions", [
        "<b>Extended Galois Fields:</b> Transition from $GF(2^8)$ to $GF(2^{16})$ for 65,535-byte codewords on multi-gigabyte archives.",
        "<b>Hardware Acceleration:</b> Leverage AES-NI instructions and SIMD Galois field matrix vectorization for gigabit-per-second streaming.",
        "<b>Fountain / RaptorQ Codes:</b> Integrate rateless fountain erasure codes for lossy peer-to-peer distributed storage."
    ], width=420)

    story.append(Table([[c1, c2]], colWidths=[430, 430]))
    story.append(Spacer(1, 15))

    # Presenter signoff box
    signoff = Table([[
        Paragraph("<font color='#9C4221'><b>Thank You! &nbsp;&bull;&nbsp; Questions & Discussion</b></font><br/>"
                  "<font color='#786458'>Presented by: <b>B. Shravya Reddy</b> (24R11A6204) &nbsp;|&nbsp; <b>K. Manasa</b> (25R15A6204)<br/>"
                  "GitHub Repository: <b>https://github.com/bshravyardy-maker/CryptoMend</b></font>",
                  ParagraphStyle('Signoff', fontName='Helvetica', fontSize=10, leading=14, alignment=1))
    ]], colWidths=[860])
    signoff.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HIGHLIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, HIGHLIGHT_BORDER),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(signoff)

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated presentation PDF: {output_pdf}")


if __name__ == "__main__":
    out_file = "/Users/badalashravyareddy/PBL'S/Cryptography/CryptoMend_Presentation.pdf"
    create_presentation(out_file)
