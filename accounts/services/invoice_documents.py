from io import BytesIO

from django.core.exceptions import ValidationError

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from accounts.models import Invoice
from business.services.settings import get_business_settings


def build_invoice_pdf(invoice):
    """
    Build and return the invoice PDF as bytes.
    """
    invoice = Invoice.objects.select_related("customer").prefetch_related("lines").get(pk=invoice.pk)
    
    if invoice.status in {"DRAFT", "VOID"}:
        raise ValidationError( "A PDF can only be generated for a posted invoice." )

    business_settings = get_business_settings()

    lines = list(invoice.lines.all())

    if not lines:
        raise ValidationError( "An invoice must contain at least one line item." )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=invoice.invoice_number,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        spaceAfter=6,
    )

    heading_style = ParagraphStyle(
        "InvoiceHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceAfter=5,
    )

    body_style = ParagraphStyle(
        "InvoiceBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    small_style = ParagraphStyle(
        "InvoiceSmall",
        parent=body_style,
        fontSize=8,
        leading=10,
    )

    right_style = ParagraphStyle(
        "InvoiceRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )

    story = []

    # Header
    header_data = [
        [
            Paragraph(
                business_settings.business_name,
                title_style,
            ),
            Paragraph(
                "<b>INVOICE</b><br/>"
                f"{invoice.invoice_number}",
                ParagraphStyle(
                    "InvoiceNumber",
                    parent=body_style,
                    fontSize=13,
                    leading=18,
                    alignment=TA_RIGHT,
                ),
            ),
        ]
    ]

    header_table = Table(
        header_data,
        colWidths=[110 * mm, 60 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 12 * mm))

    # Customer / dates
    customer_data = [
        [
            Paragraph("<b>Bill to</b>", heading_style),
            Paragraph("<b>Invoice details</b>", heading_style),
        ],
        [
            Paragraph(
                f"{invoice.client_name}<br/>"
                f"{invoice.client_email or ''}",
                body_style,
            ),
            Paragraph(
                f"Issue date: "
                f"{invoice.issue_date.strftime('%d/%m/%Y')}<br/>"
                f"Due date: "
                f"{invoice.due_date.strftime('%d/%m/%Y')}",
                body_style,
            ),
        ],
    ]

    customer_table = Table(
        customer_data,
        colWidths=[90 * mm, 80 * mm],
    )

    customer_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(customer_table)
    story.append(Spacer(1, 10 * mm))

    # Lines
    line_data = [
        [
            Paragraph("<b>Description</b>", small_style),
            Paragraph("<b>Qty</b>", right_style),
            Paragraph("<b>Unit price</b>", right_style),
            Paragraph("<b>VAT</b>", right_style),
            Paragraph("<b>Total</b>", right_style),
        ]
    ]

    for line in lines:
        line_data.append(
            [
                Paragraph(line.description, body_style),
                Paragraph(
                    f"{line.quantity:.2f}",
                    right_style,
                ),
                Paragraph(
                    f"£{line.unit_price:.2f}",
                    right_style,
                ),
                Paragraph(
                    f"{line.vat_amount:.2f}",
                    right_style,
                ),
                Paragraph(
                    f"£{line.gross_amount:.2f}",
                    right_style,
                ),
            ]
        )

    line_table = Table(
        line_data,
        colWidths=[
            75 * mm,
            20 * mm,
            27 * mm,
            20 * mm,
            28 * mm,
        ],
        repeatRows=1,
    )

    line_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#224B75")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9DEE3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(line_table)
    story.append(Spacer(1, 8 * mm))

    # Totals
    totals_data = [
        [
            Paragraph("Net", body_style),
            Paragraph(
                f"£{invoice.total_net:.2f}",
                right_style,
            ),
        ],
        [
            Paragraph("VAT", body_style),
            Paragraph(
                f"£{invoice.total_vat:.2f}",
                right_style,
            ),
        ],
        [
            Paragraph("<b>Total</b>", body_style),
            Paragraph(
                f"<b>£{invoice.total_gross:.2f}</b>",
                right_style,
            ),
        ],
    ]

    totals_table = Table(
        totals_data,
        colWidths=[135 * mm, 35 * mm],
        hAlign="RIGHT",
    )

    totals_table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 2), (-1, 2), 0.8, colors.HexColor("#224B75")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(totals_table)

    document.build(story)

    return buffer.getvalue()