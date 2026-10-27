
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape

from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .utils import format_duration


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

DECIMAL_PLACES = Decimal("0.01")

NAVY = colors.HexColor("#224B75")
LIGHT_GREY = colors.HexColor("#F1F5F9")
MID_GREY = colors.HexColor("#64748B")
DARK_GREY = colors.HexColor("#334155")
BORDER_GREY = colors.HexColor("#CBD5E1")


# ---------------------------------------------------------------------
# Allowance calculation
# ---------------------------------------------------------------------

def calculate_allowance(start_date, end_date, monthly_allowance):
    """
    Calculate the allowance for a date range.

    Full months receive the full monthly allowance.
    Partial months are prorated by calendar days.
    The start and end dates are inclusive.
    """

    if start_date > end_date:
        return Decimal("0.00")

    monthly_allowance = Decimal(monthly_allowance)
    total_allowance = Decimal("0.00")
    current_date = start_date

    while current_date <= end_date:
        days_in_month = monthrange(
            current_date.year,
            current_date.month,
        )[1]

        last_day_of_month = current_date.replace(
            day=days_in_month,
        )

        period_end = min(end_date, last_day_of_month)

        days_in_period = (
            period_end - current_date
        ).days + 1

        monthly_fraction = (
            Decimal(days_in_period) / Decimal(days_in_month)
        )

        total_allowance += monthly_allowance * monthly_fraction

        current_date = period_end + timedelta(days=1)

    return total_allowance.quantize(
        DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


# ---------------------------------------------------------------------
# PDF report generation
# ---------------------------------------------------------------------

def build_work_report(records, start_date, end_date, monthly_allowance):
    """
    Build and return a downloadable PDF work contribution report.
    """

    records = list(records)
    monthly_allowance = Decimal(monthly_allowance)

    # Calculate total recorded hours.
    # Keep all calculations in decimal hours.
    total_hours = sum( (Decimal(record.duration_hours) for record in records), Decimal("0.00"), ).quantize( DECIMAL_PLACES, rounding=ROUND_HALF_UP, )

    allowance = calculate_allowance( start_date, end_date, monthly_allowance, )

    difference = (total_hours - allowance).quantize( DECIMAL_PLACES, rounding=ROUND_HALF_UP, )

    # Create the PDF response.

    filename = f"work-report-{start_date:%Y%m%d}-{end_date:%Y%m%d}.pdf"


    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] =  f'attachment; filename="{filename}"'
    

    # Configure the PDF document.

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Work Contribution Report",
        author="Work Log",
    )

    # Define report styles.

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=26,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=MID_GREY,
            alignment=TA_CENTER,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Cell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=DARK_GREY,
            spaceAfter=0,
            spaceBefore=0,
            wordWrap="LTR",
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCell",
            parent=styles["Cell"],
            fontSize=7,
            leading=9,
            textColor=MID_GREY,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SummaryLabel",
            parent=styles["Cell"],
            fontName="Helvetica-Bold",
            fontSize=9,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SummaryValue",
            parent=styles["Cell"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=NAVY,
        )
    )

    story = []

    # -----------------------------------------------------------------
    # Report heading
    # -----------------------------------------------------------------

    story.append(
        Paragraph(
            "Work Contribution Report",
            styles["ReportTitle"],
        )
    )

    story.append(
        Paragraph(
            f"{start_date:%d %B %Y} to {end_date:%d %B %Y}",
            styles["ReportSubtitle"],
        )
    )

    story.append(
        Paragraph(
            "A record of work undertaken during the selected period.",
            styles["ReportSubtitle"],
        )
    )

    story.append(Spacer(1, 8 * mm))

    # -----------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------

    story.append(
        Paragraph(
            "Summary",
            styles["SectionHeading"],
        )
    )

    summary_rows = [
        [
            Paragraph("Total recorded time", styles["SummaryLabel"]),
            Paragraph(
                format_duration(total_hours),
                styles["SummaryValue"],
            ),
        ],
        [
            Paragraph("Monthly allowance", styles["SummaryLabel"]),
            Paragraph(
                format_duration(monthly_allowance),
                styles["SummaryValue"],
            ),
        ],
        [
            Paragraph(
                "Allowance for selected period",
                styles["SummaryLabel"],
            ),
            Paragraph(
                format_duration(allowance),
                styles["SummaryValue"],
            ),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[115 * mm, 55 * mm],
        hAlign="LEFT",
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(summary_table)

    # -----------------------------------------------------------------
    # Allowance comparison
    # -----------------------------------------------------------------

    story.append(
        Paragraph(
            "Allowance comparison",
            styles["SectionHeading"],
        )
    )

    if difference > 0:
        comparison_text = (
            f"{format_duration(difference)} "
            "above the calculated allowance."
        )
    elif difference < 0:
        comparison_text = (
            f"{format_duration(abs(difference))} "
            "below the calculated allowance."
        )
    else:
        comparison_text = (
            "Recorded hours match the calculated allowance."
        )

    # Format the difference with its sign kept separate
    # from the duration formatter.

    if difference > 0:
        difference_display = f"+{format_duration(abs(difference))}"
    elif difference < 0:
        difference_display = f"-{format_duration(abs(difference))}"
    else:
        difference_display = format_duration(Decimal("0.00"))

    comparison_rows = [
        [
            Paragraph("Recorded time", styles["Cell"]),
            Paragraph("Calculated allowance", styles["Cell"]),
            Paragraph("Difference", styles["Cell"]),
        ],
        [
            Paragraph(
                format_duration(total_hours),
                styles["SummaryValue"],
            ),
            Paragraph(
                format_duration(allowance),
                styles["SummaryValue"],
            ),
            Paragraph(
                difference_display,
                styles["SummaryValue"],
            ),
        ],
    ]

    comparison_table = Table(
        comparison_rows,
        colWidths=[56 * mm, 57 * mm, 57 * mm],
        hAlign="LEFT",
    )

    comparison_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(comparison_table)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(comparison_text, styles["Cell"]))

    story.append(
        Paragraph(
            "The allowance is prorated by calendar days for any partial months "
            "within the selected date range. This comparison is provided for "
            "information and does not determine payment entitlement.",
            styles["SmallCell"],
        )
    )

    # -----------------------------------------------------------------
    # Detailed work log
    # -----------------------------------------------------------------

    story.append(
        Paragraph(
            "Work log",
            styles["SectionHeading"],
        )
    )

    def cell(value):
        """
        Safely convert plain text into a ReportLab paragraph.

        Escaping prevents user-entered text from being interpreted
        as ReportLab paragraph markup.
        """

        text = escape(str(value or "—")).replace("\n", "<br/>")
        return Paragraph(text, styles["Cell"])

    rows = [
        [
            cell("Date"),
            cell("Project and task"),
            cell("Status"),
            cell("Duration"),
        ]
    ]

    for record in records:
        description = (
            f"<b>{escape(record.project)}</b><br/>"
            f"{escape(record.task_description).replace(chr(10), '<br/>')}"
        )

        if record.notes:
            description += (
                f"<br/><font color='#64748B'>Notes: "
                f"{escape(record.notes).replace(chr(10), '<br/>')}</font>"
            )

        rows.append(
            [
                cell(record.date.strftime("%d %b %Y")),
                Paragraph(description, styles["Cell"]),
                cell(record.get_status_display()),
                cell(format_duration(record.duration_hours)),
            ]
        )

    if not records:
        rows.append(
            [
                Paragraph(
                    "No work records were found for this period.",
                    styles["Cell"],
                ),
                "",
                "",
                "",
            ]
        )

    rows.append(
        [
            cell(""),
            cell("Total recorded time"),
            cell(""),
            cell(format_duration(total_hours)),
        ]
    )

    work_table = Table(
        rows,
        colWidths=[24 * mm, 94 * mm, 32 * mm, 20 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )

    work_table.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                # Body
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -2),
                    [colors.white, LIGHT_GREY],
                ),
                ("GRID", (0, 0), (-1, -2), 0.3, BORDER_GREY),

                # Total row
                ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GREY),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),

                # Spacing and alignment
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )

    story.append(work_table)

    # -----------------------------------------------------------------
    # Page numbers
    # -----------------------------------------------------------------

    def add_page_number(canvas, document):
        canvas.saveState()

        canvas.setStrokeColor(BORDER_GREY)
        canvas.setLineWidth(0.5)
        canvas.line(
            17 * mm,
            14 * mm,
            A4[0] - 17 * mm,
            14 * mm,
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MID_GREY)

        canvas.drawString(
            17 * mm,
            9 * mm,
            "Work Contribution Report",
        )

        canvas.drawRightString(
            A4[0] - 17 * mm,
            9 * mm,
            f"Page {document.page}",
        )

        canvas.restoreState()

    # Build the PDF and return it as a downloadable response.

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return response
