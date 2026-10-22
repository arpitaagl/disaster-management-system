"""Exportable, source-labelled situation reports for ResQ-AI."""
from __future__ import annotations
import csv, io, json
from datetime import datetime, timezone
from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

def _stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def situation_report(center: Any, live_alerts: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = center.metrics()
    incidents = sorted(center.incidents, key=lambda r: int(r.get("priority_score") or 0), reverse=True)
    return {
        "report_title": "ResQ-AI Situation Report",
        "generated_at": _stamp(),
        "data_mode": "simulated_demo_data" if getattr(center, "demo_mode", True) else "application_state",
        "disclaimer": "Decision support only. Verify all facts and capacity with responsible authorities. Not a dispatch order.",
        "metrics": metrics,
        "incidents": incidents,
        "assignments": center.assignments,
        "resources": center.resources,
        "hospitals": center.hospitals,
        "shelters": center.shelters,
        "roads": center.roads,
        "recent_events": center.events[:50],
        "live_alerts": live_alerts or {"status": "not_attached", "note": "Live alerts were not fetched for this report."},
    }

def json_report(center: Any, live_alerts: dict[str, Any] | None = None) -> str:
    return json.dumps(situation_report(center, live_alerts), indent=2, ensure_ascii=False, default=str)

def incidents_csv(center: Any) -> str:
    fields = ["id","disaster_type","priority_score","urgency","status","people_affected","medical_emergency","vulnerable_population","accessibility","lat","lon","reported_at","reporter","summary","recommended_action","source"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(center.incidents)
    return stream.getvalue()

def event_log_csv(center: Any) -> str:
    stream = io.StringIO(newline="")
    rows = center.events[:]
    fields = sorted({key for row in rows for key in row}) or ["ts","category","message"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()

def situation_report_markdown(center: Any) -> str:
    report = situation_report(center)
    m = report["metrics"]
    lines = ["# ResQ-AI Situation Report", "", f"Generated: {report['generated_at']}", f"Data mode: {report['data_mode']}", "",
    "> Decision support only. Verify reports and capacities with authorities. Not a dispatch order.", "",
    "## Situation summary", "", f"- Active incidents: {m.get('active_incidents', 0)}", f"- Critical incidents: {m.get('critical_incidents', 0)}",
    f"- People affected (reported): {m.get('people_affected', 0)}", f"- Available resources (reported): {m.get('available_resources', 0)}",
    f"- Hospital beds available (reported): {m.get('hospital_beds_available', 0)}", f"- Shelter spaces available (reported): {m.get('shelter_spaces_available', 0)}", "",
    "## Priority incidents", ""]
    for item in report["incidents"][:20]:
        lines.append(f"- **{item.get('id')}** — {item.get('disaster_type')}; score {item.get('priority_score', 0)}/100; status {item.get('status')}; people affected {item.get('people_affected', 0)}. {item.get('summary') or item.get('description') or ''}")
    lines += ["", "## Recommended assignments", ""]
    for item in report["assignments"][:30]:
        lines.append(f"- {item.get('incident_id')}: {item.get('resource_name') or item.get('resource_id') or 'Unassigned'}; {item.get('reason') or 'No recommendation reason supplied'}")
    return "\n".join(lines) + "\n"


_NAVY = colors.HexColor("#10233F")
_TEAL = colors.HexColor("#0E9F9A")
_PALE = colors.HexColor("#EEF5F8")
_INK = colors.HexColor("#24364B")
_MUTED = colors.HexColor("#64748B")


def _pdf_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=_NAVY, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontSize=9, leading=13, textColor=_MUTED, spaceAfter=12),
        "section": ParagraphStyle("ReportSection", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=_NAVY, spaceBefore=10, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("ReportBody", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=_INK, wordWrap="CJK"),
        "small": ParagraphStyle("ReportSmall", parent=base["BodyText"], fontSize=7.2, leading=9.5, textColor=_INK, wordWrap="CJK"),
        "code": ParagraphStyle("ReportCode", parent=base["Code"], fontName="Courier", fontSize=6.6, leading=8.4, textColor=_INK, wordWrap="CJK"),
        "metric_label": ParagraphStyle("MetricLabel", parent=base["Normal"], fontSize=7.2, leading=9, textColor=_MUTED),
        "metric_value": ParagraphStyle("MetricValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=_NAVY),
        "table_head": ParagraphStyle("TableHeader", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white),
    }


def _pdf_paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    text = "Not provided" if value is None or value == "" else str(value)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _pdf_table(headers: list[str], rows: list[list[Any]], widths: list[float], styles: dict) -> LongTable:
    cells = [[_pdf_paragraph(head, styles["table_head"]) for head in headers]]
    cells += [[_pdf_paragraph(value, styles["small"]) for value in row] for row in rows]
    table = LongTable(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _PALE]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D8E2EA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _build_pdf(title: str, center: Any, body: list[Any], *, wide: bool = False) -> bytes:
    output = io.BytesIO()
    page_size = landscape(A4) if wide else A4
    doc = SimpleDocTemplate(
        output, pagesize=page_size, rightMargin=16 * mm, leftMargin=16 * mm,
        topMargin=18 * mm, bottomMargin=17 * mm, title=title, author="ResQ-AI",
    )
    styles = _pdf_styles()
    story = [
        Paragraph("RESQ-AI  /  DISASTER INTELLIGENCE", ParagraphStyle(
            "Brand", fontName="Helvetica-Bold", fontSize=8, textColor=_TEAL,
            tracking=0.7, spaceAfter=9,
        )),
        Paragraph(escape(title), styles["title"]),
        Paragraph(f"Generated {escape(_stamp())} UTC  |  {'Demo snapshot' if getattr(center, 'demo_mode', True) else 'Application state'}", styles["subtitle"]),
        Table([["DECISION SUPPORT ONLY", "Verify reports and capacity with responsible authorities. This report is not a dispatch order."]], colWidths=[39 * mm, doc.width - 39 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _PALE), ("TEXTCOLOR", (0, 0), (0, 0), _TEAL),
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7.4),
            ("TEXTCOLOR", (1, 0), (1, 0), _INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])),
        Spacer(1, 10),
    ] + body

    def decorate_page(canvas, page_doc):
        canvas.saveState()
        w, h = page_doc.pagesize
        canvas.setStrokeColor(_TEAL)
        canvas.setLineWidth(2)
        canvas.line(page_doc.leftMargin, h - 10 * mm, page_doc.leftMargin + 22 * mm, h - 10 * mm)
        canvas.setStrokeColor(colors.HexColor("#D8E2EA"))
        canvas.setLineWidth(0.5)
        canvas.line(page_doc.leftMargin, 12 * mm, w - page_doc.rightMargin, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(_MUTED)
        canvas.drawString(page_doc.leftMargin, 7.5 * mm, "RESQ-AI  |  Confidential operational snapshot")
        canvas.drawRightString(w - page_doc.rightMargin, 7.5 * mm, f"Page {page_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    return output.getvalue()


def _metrics_panel(metrics: dict[str, Any], width: float, styles: dict) -> Table:
    fields = [
        ("Active incidents", "active_incidents"), ("Critical", "critical_incidents"),
        ("People affected", "people_affected"), ("Resources available", "available_resources"),
        ("Hospital beds", "hospital_beds_available"), ("Shelter spaces", "shelter_spaces_available"),
    ]
    card_width = width / 3
    rows = []
    for start in range(0, len(fields), 3):
        cards = []
        for label, key in fields[start:start + 3]:
            cards.append(Table([
                [Paragraph(escape(label.upper()), styles["metric_label"])],
                [Paragraph(escape(str(metrics.get(key, 0))), styles["metric_value"])],
            ], colWidths=[card_width - 12], style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _PALE), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])))
        rows.append(cards)
    table = Table(rows, colWidths=[card_width] * 3, hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return table


def situation_report_pdf(center: Any) -> bytes:
    report = situation_report(center)
    styles = _pdf_styles()
    width = A4[0] - 32 * mm
    body = [Paragraph("Situation overview", styles["section"]), _metrics_panel(report["metrics"], width, styles)]
    body.append(Paragraph("Priority incidents", styles["section"]))
    incidents = report["incidents"]
    if incidents:
        rows = [[i.get("id"), i.get("disaster_type"), i.get("priority_score"), i.get("workflow_status") or i.get("status"), i.get("people_affected"), i.get("summary") or i.get("description")] for i in incidents]
        body.append(_pdf_table(["ID", "Type", "Priority", "Status", "People", "Summary"], rows, [23 * mm, 29 * mm, 17 * mm, 23 * mm, 18 * mm, width - 110 * mm], styles))
    else:
        body.append(Paragraph("No incidents are currently available in this snapshot.", styles["body"]))
    assignments = report["assignments"]
    body.append(Paragraph("Recommended assignments", styles["section"]))
    if assignments:
        rows = [[a.get("incident_id"), a.get("resource_name") or a.get("resource_id"), a.get("reason")] for a in assignments]
        body.append(_pdf_table(["Incident", "Resource", "Reason"], rows, [35 * mm, 48 * mm, width - 83 * mm], styles))
    else:
        body.append(Paragraph("No assignments are currently available.", styles["body"]))
    return _build_pdf("Situation Report", center, body)


def _section_records(title: str, records: list[dict], page_width: float, styles: dict) -> list[Any]:
    body: list[Any] = [Paragraph(escape(title), styles["section"])]
    if not records:
        body.append(Paragraph("No records in this snapshot.", styles["body"]))
        return body
    keys = sorted({key for record in records for key in record})
    # Render each record as a compact label/value block so irregular snapshot fields remain readable.
    for index, record in enumerate(records, 1):
        identity = record.get("id") or record.get("incident_id") or f"Record {index}"
        record_type = record.get("disaster_type") or record.get("name") or record.get("category")
        label = f"{identity} - {record_type}" if record_type else str(identity)
        body.append(Paragraph(escape(label), ParagraphStyle(
            f"RecordHeading{index}", parent=styles["body"], fontName="Helvetica-Bold",
            textColor=_TEAL, spaceBefore=3, spaceAfter=3, keepWithNext=True,
        )))
        rows = [[key.replace("_", " ").title(), json.dumps(record.get(key), ensure_ascii=False, default=str)] for key in keys if key in record]
        body.append(_pdf_table(["Field", "Value"], rows, [43 * mm, page_width - 43 * mm], styles))
        body.append(Spacer(1, 6))
    return body


def full_snapshot_pdf(center: Any) -> bytes:
    report = situation_report(center)
    styles = _pdf_styles()
    width = A4[0] - 32 * mm
    body: list[Any] = [Paragraph("Summary metrics", styles["section"]), _metrics_panel(report["metrics"], width, styles)]
    body.append(Paragraph("Detailed incident, assignment, resource, facility, road, event, and live-alert records follow on the next pages.", styles["subtitle"]))
    for key, title in (("incidents", "Incidents"), ("assignments", "Assignments"), ("resources", "Resources"), ("hospitals", "Hospitals"), ("shelters", "Shelters"), ("roads", "Roads"), ("recent_events", "Recent events")):
        body += _section_records(title, report.get(key, []), width, styles)
    body += _section_records("Live alerts", [report.get("live_alerts", {})], width, styles)
    return _build_pdf("Full Command Center Snapshot", center, body)


def incident_register_pdf(center: Any) -> bytes:
    incidents = sorted(center.incidents, key=lambda row: int(row.get("priority_score") or 0), reverse=True)
    styles = _pdf_styles()
    width = landscape(A4)[0] - 32 * mm
    body: list[Any] = [Paragraph(f"{len(incidents)} incident record(s), ordered by priority", styles["body"]), Spacer(1, 6)]
    if incidents:
        rows = []
        for incident in incidents:
            action = str(incident.get("recommended_action") or "Not provided")
            if action.casefold().startswith("recommended action:"):
                action = action.split(":", 1)[1].strip()
            rows.append([
                incident.get("id"),
                incident.get("disaster_type"),
                f"Priority: {incident.get('priority_score', 0)}/100\nUrgency: {incident.get('urgency', 'Not provided')}\nStatus: {incident.get('workflow_status') or incident.get('status', 'Not provided')}",
                f"People: {incident.get('people_affected', 0)}\nMedical: {incident.get('medical_emergency', 'Not provided')}\nVulnerable: {incident.get('vulnerable_population', 0)}",
                f"Access: {incident.get('accessibility', 'Not provided')}\nCoordinates: {incident.get('lat', 'Not provided')}, {incident.get('lon', 'Not provided')}\nReported: {incident.get('reported_at', 'Not provided')}\nReporter / source: {incident.get('reporter', 'Not provided')} / {incident.get('source', 'Not provided')}",
                f"Summary: {incident.get('summary') or incident.get('description') or 'Not provided'}\nRecommended action: {action}",
            ])
        weights = [8, 12, 14, 14, 22, 30]
        body.append(_pdf_table(
            ["ID", "Incident type", "Priority & status", "Impact", "Location & reporting", "Summary & recommended action"],
            rows,
            [width * weight / sum(weights) for weight in weights],
            styles,
        ))
    else:
        body.append(Paragraph("No incident records are available.", styles["body"]))
    return _build_pdf("Incident Register", center, body, wide=True)


def event_log_pdf(center: Any) -> bytes:
    records = center.events[:]
    fields = sorted({key for row in records for key in row}) or ["ts", "category", "message"]
    styles = _pdf_styles()
    width = landscape(A4)[0] - 32 * mm
    rows = [[record.get(field) for field in fields] for record in records]
    col_width = width / max(len(fields), 1)
    body = [Paragraph(f"{len(records)} audit/event record(s), newest first", styles["body"]), Spacer(1, 6)]
    if rows:
        body.append(_pdf_table([field.replace("_", " ").title() for field in fields], rows, [col_width] * len(fields), styles))
    else:
        body.append(Paragraph("No audit/event records are available.", styles["body"]))
    return _build_pdf("Audit and Event Log", center, body, wide=True)
