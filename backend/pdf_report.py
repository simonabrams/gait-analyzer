"""
On-demand branded PDF report generation for a completed run (Pro feature).
Built from data already on hand (results_json + dashboard PNG) rather than
during the async pipeline, so it costs nothing for runs nobody exports.
"""
import os
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend import storage
from backend.heuristics import (
    CADENCE_MIN_SPM,
    KNEE_FLEXION_MIN_DEG,
    OVERSTRIDE_CM_THRESHOLD,
    TRUNK_LEAN_MAX_DEG,
    VERTICAL_OSC_MAX_CM,
)

_PRIMARY = colors.HexColor("#00C896")
_DARK = colors.HexColor("#0F0F0F")

_METRIC_ROWS = [
    ("Cadence", "cadence_avg", "spm", f"≥ {CADENCE_MIN_SPM} spm"),
    ("Bounce", "vertical_osc_avg_cm", "cm", f"≤ {VERTICAL_OSC_MAX_CM} cm"),
    ("Knee drive", "knee_angle_strike_avg_deg", "°", f"≥ {KNEE_FLEXION_MIN_DEG}°"),
    ("Foot strike position", "foot_strike_position_avg_cm", "cm", f"≤ {OVERSTRIDE_CM_THRESHOLD} cm"),
    ("Trunk lean", "trunk_lean_avg_deg", "°", f"≤ {TRUNK_LEAN_MAX_DEG}°"),
]


def build_run_report_pdf(run, output_path: str) -> None:
    """Assemble a branded PDF report for `run` (a Run ORM row with results_json
    and dashboard_image_r2_key already populated) and write it to output_path."""
    results = run.results_json or {}
    summary = results.get("summary", {})
    flags = results.get("flags", [])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("RunlensTitle", parent=styles["Title"], textColor=_DARK)
    heading_style = ParagraphStyle("RunlensHeading", parent=styles["Heading2"], textColor=_DARK)
    body_style = styles["BodyText"]
    warn_style = ParagraphStyle(
        "RunlensLowConfidence", parent=body_style, textColor=colors.HexColor("#B45309")
    )

    doc = SimpleDocTemplate(
        output_path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch
    )
    story = [
        Paragraph("Runlens Gait Report", title_style),
        Paragraph(f"Recorded: {run.recorded_at or run.created_at}", body_style),
        Spacer(1, 0.2 * inch),
    ]

    gate = (results.get("meta") or {}).get("confidence_gate") or {}
    if gate.get("low_confidence"):
        usable = gate.get("usable_stride_count")
        note = (
            f"Based on {usable} detected strides — lower confidence than usual."
            if usable is not None
            else "Lower confidence than usual — fewer strides detected than ideal."
        )
        story.append(Paragraph(f"<b>{note}</b>", warn_style))
        story.append(Spacer(1, 0.15 * inch))

    metric_rows = [["Metric", "Value", "Target"]]
    for label, key, unit, target in _METRIC_ROWS:
        value = summary.get(key)
        metric_rows.append([label, f"{value} {unit}" if value is not None else "—", target])
    table = Table(metric_rows, colWidths=[2.2 * inch, 1.8 * inch, 1.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    dashboard_tmp_path = None
    try:
        if run.dashboard_image_r2_key:
            fd, dashboard_tmp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            storage.download_file(run.dashboard_image_r2_key, dashboard_tmp_path)
            story.append(
                Image(dashboard_tmp_path, width=6.5 * inch, height=3.9 * inch, kind="proportional")
            )
            story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Flagged issues and recommendations", heading_style))
        if flags:
            for f in flags:
                story.append(
                    Paragraph(
                        f"<b>{f.get('metric', '')}</b> — value {f.get('value')} "
                        f"(threshold: {f.get('threshold')})",
                        body_style,
                    )
                )
                story.append(Paragraph(f.get("recommendation", ""), body_style))
                for ex in f.get("exercises") or []:
                    story.append(
                        Paragraph(f"&bull; {ex.get('name', '')}: {ex.get('description', '')}", body_style)
                    )
                story.append(Spacer(1, 0.15 * inch))
        else:
            story.append(Paragraph("No issues flagged. Metrics within target ranges.", body_style))

        # doc.build() must run before the temp file is unlinked below: platypus's
        # Image flowable reads the file lazily at build time, not at construction.
        doc.build(story)
    finally:
        if dashboard_tmp_path:
            Path(dashboard_tmp_path).unlink(missing_ok=True)
