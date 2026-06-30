from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import io
from datetime import datetime

# ── Brand colors ──────────────────────────────────────────────────────────────
PURPLE      = HexColor("#6B21C8")
DARK_PURPLE = HexColor("#4A0080")
PINK        = HexColor("#E91E8C")
LIGHT_BG    = HexColor("#F7F5FF")
LIGHT_BORDER= HexColor("#E9D5FF")
DARK_TEXT   = HexColor("#1A0533")
GRAY_TEXT   = HexColor("#6B7280")
GREEN       = HexColor("#00A651")
ORANGE      = HexColor("#F97316")
RED         = HexColor("#DC2626")

def determination_color(determination):
    if determination == "APPROVE":
        return GREEN
    elif determination == "FLAG FOR REVIEW":
        return ORANGE
    return RED

def build_pdf_report(claim_record: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        fontSize=22,
        fontName="Helvetica-Bold",
        textColor=white,
        alignment=TA_LEFT,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontSize=10,
        fontName="Helvetica",
        textColor=HexColor("#D8B4FE"),
        alignment=TA_LEFT,
        spaceAfter=2
    )
    section_header_style = ParagraphStyle(
        "SectionHeader",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=PURPLE,
        spaceBefore=16,
        spaceAfter=6,
        borderPadding=(0, 0, 4, 0)
    )
    body_style = ParagraphStyle(
        "Body",
        fontSize=9,
        fontName="Helvetica",
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=4
    )
    label_style = ParagraphStyle(
        "Label",
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=GRAY_TEXT,
        spaceAfter=2
    )
    mono_style = ParagraphStyle(
        "Mono",
        fontSize=8,
        fontName="Courier",
        textColor=PURPLE,
        spaceAfter=2
    )

    story = []

    # ── Header banner ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("PayGuard AI-Audit Report", title_style),
        Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}<br/>"
            f"Case ID: {claim_record['case_id']}",
            ParagraphStyle(
                "HeaderRight", fontSize=8, fontName="Helvetica",
                textColor=HexColor("#D8B4FE"), alignment=TA_RIGHT
            )
        )
    ]]
    header_table = Table(header_data, colWidths=[4.5*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_PURPLE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_PURPLE]),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 20),
        ("LEFTPADDING", (0, 0), (0, -1), 20),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [8]),
        ("LINEBELOW", (0, 0), (-1, 0), 3, PINK),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    # ── Determination banner ──────────────────────────────────────────────────
    determination = claim_record.get("determination", "UNKNOWN")
    det_color = determination_color(determination)
    det_icon = {"APPROVE": "✅", "FLAG FOR REVIEW": "🚩"}.get(determination, "❌")
    confidence = claim_record.get("confidence")
    conf_str = f"   |   AI Confidence: {confidence}%" if confidence else ""

    det_data = [[
        Paragraph(
            f"{det_icon}  FINAL DETERMINATION: {determination}{conf_str}",
            ParagraphStyle(
                "Det", fontSize=12, fontName="Helvetica-Bold",
                textColor=white, alignment=TA_CENTER
            )
        )
    ]]
    det_table = Table(det_data, colWidths=[7*inch])
    det_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), det_color),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 16))

    # ── Claim summary table ───────────────────────────────────────────────────
    story.append(Paragraph("CLAIM INFORMATION", section_header_style))
    story.append(HRFlowable(
        width="100%", thickness=1,
        color=LIGHT_BORDER, spaceAfter=8
    ))

    summary_data = [
        ["Provider", claim_record.get("provider_name", "N/A"),
         "Specialty", claim_record.get("specialty", "N/A")],
        ["Case ID", claim_record.get("case_id", "N/A"),
         "Billed Amount", f"${claim_record.get('billed_amount', 0):,}"],
        ["Risk Score", claim_record.get("risk_score", "N/A"),
         "Est. Recoverable", f"${claim_record.get('recoverable', 0):,}"],
        ["Analyzed At", claim_record.get("timestamp", "N/A"),
         "Determination", determination],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[1.4*inch, 2.1*inch, 1.4*inch, 2.1*inch]
    )
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("TEXTCOLOR", (2, 0), (2, -1), GRAY_TEXT),
        ("TEXTCOLOR", (1, 0), (1, -1), DARK_TEXT),
        ("TEXTCOLOR", (3, 0), (3, -1), DARK_TEXT),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # ── Agent outputs ─────────────────────────────────────────────────────────
    sections = [
        ("🧠 AGENT 1 — CLINICAL NECESSITY REVIEW",
         claim_record.get("clinical_analysis", "")),
        ("🔍 AGENT 2 — FWA DETECTION ANALYSIS",
         claim_record.get("fwa_analysis", "")),
        ("⚖️ AGENT 3 — FINAL DETERMINATION",
         claim_record.get("decision", "")),
    ]

    for section_title, content in sections:
        story.append(Paragraph(section_title, section_header_style))
        story.append(HRFlowable(
            width="100%", thickness=1,
            color=LIGHT_BORDER, spaceAfter=8
        ))

        # Clean and wrap content
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue
            # Section headers in output
            if line.isupper() and len(line) < 60 and ":" in line:
                story.append(Paragraph(line, label_style))
            elif line.startswith("CPT") and "|" in line:
                story.append(Paragraph(line, mono_style))
            else:
                # Escape special chars for ReportLab
                line = (line.replace("&", "&amp;")
                           .replace("<", "&lt;")
                           .replace(">", "&gt;"))
                story.append(Paragraph(line, body_style))

        story.append(Spacer(1, 8))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=LIGHT_BORDER, spaceAfter=8
    ))
    footer_data = [[
        Paragraph(
            "PayGuard AI  |  Built by Neha Save  |  "
            "Powered by GPT-4o-mini + Live CMS API",
            ParagraphStyle(
                "Footer", fontSize=7, fontName="Helvetica",
                textColor=GRAY_TEXT, alignment=TA_LEFT
            )
        ),
        Paragraph(
            "Synthetic data only — no real PHI used",
            ParagraphStyle(
                "FooterR", fontSize=7, fontName="Helvetica",
                textColor=GRAY_TEXT, alignment=TA_RIGHT
            )
        )
    ]]
    footer_table = Table(footer_data, colWidths=[4.5*inch, 2.5*inch])
    footer_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_table)

    doc.build(story)
    return buffer.getvalue()