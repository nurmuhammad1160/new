# reports/utils/pdf_generator.py

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
import io


def generate_pdf_report(tickets, filters, report_type, stats_data=None):
    """PDF hisobot yaratish"""
    
    # Buffer yaratish
    buffer = io.BytesIO()
    
    # PDF document
    if report_type == 'tickets':
        # Landscape for table
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )
    else:
        # Portrait for stats
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=50,
            bottomMargin=30
        )
    
    # Story (content)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    # Header
    title = Paragraph(_("IIV TEXNIK MUROJAATLAR HISOBOTI"), title_style)
    story.append(title)
    
    # Sana
    date_text = f"{_('Sana')}: {timezone.now().strftime('%d.%m.%Y %H:%M')}"
    subtitle = Paragraph(date_text, subtitle_style)
    story.append(subtitle)
    
    # Filter info
    filter_info = get_filter_info_text(filters)
    if filter_info:
        filter_para = Paragraph(f"<b>{_('Filtrlar')}:</b> {filter_info}", styles['Normal'])
        story.append(filter_para)
        story.append(Spacer(1, 20))
    
    # Content bo'yicha
    if report_type == 'tickets':
        add_tickets_table(story, tickets, styles, heading_style)
    
    elif report_type == 'statistics':
        add_statistics_content(story, stats_data, styles, heading_style)
    
    elif report_type == 'technician_performance':
        add_technician_performance(story, stats_data, styles, heading_style)
    
    elif report_type == 'system_analysis':
        add_system_analysis(story, stats_data, styles, heading_style)
    
    elif report_type == 'regional_analysis':
        add_regional_analysis(story, stats_data, styles, heading_style)
    
    # Footer
    story.append(Spacer(1, 30))
    footer_text = f"{_('IIV Support System')} • {_('Hisobot yaratildi')}: {timezone.now().strftime('%d.%m.%Y %H:%M')}"
    footer = Paragraph(footer_text, subtitle_style)
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    
    # Response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def add_tickets_table(story, tickets, styles, heading_style):
    """Ticketlar jadvali"""
    
    story.append(Paragraph(_("Murojaatlar ro'yxati"), heading_style))
    story.append(Spacer(1, 12))
    
    # Table data
    data = [
        [
            _('ID'),
            _('Sana'),
            _('Tizim'),
            _('Viloyat'),
            _('Foydalanuvchi'),
            _('Holat'),
            _('Mas\'ul'),
            _('Baho'),
        ]
    ]
    
    for ticket in tickets[:100]:  # Limit 100
        data.append([
            ticket.get_ticket_number(),
            ticket.created_at.strftime('%d.%m.%Y'),
            ticket.system.name[:20],
            ticket.region.name if ticket.region else '-',
            ticket.user.get_full_name()[:25],
            ticket.get_status_display(),
            ticket.assigned_to.get_full_name()[:20] if ticket.assigned_to else '-',
            f"{ticket.rating}⭐" if ticket.rating else '-',
        ])
    
    # Create table
    table = Table(data, colWidths=[
        0.8*inch, 0.9*inch, 1.2*inch, 1*inch, 
        1.3*inch, 1*inch, 1.2*inch, 0.7*inch
    ])
    
    # Table style
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Body
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Alternate rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    
    story.append(table)
    
    # Summary
    story.append(Spacer(1, 20))
    summary = Paragraph(
        f"<b>{_('Jami')}: {tickets.count()} {_('ta murojaat')}</b>",
        styles['Normal']
    )
    story.append(summary)


def add_statistics_content(story, stats_data, styles, heading_style):
    """Statistika content"""
    
    story.append(Paragraph(_("Umumiy statistika"), heading_style))
    story.append(Spacer(1, 12))
    
    # Status bo'yicha
    if stats_data.get('by_status'):
        story.append(Paragraph(_("Holat bo'yicha"), styles['Heading3']))
        data = [[_('Holat'), _('Soni')]]
        for item in stats_data['by_status']:
            data.append([item['status'], str(item['count'])])
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(get_simple_table_style())
        story.append(table)
        story.append(Spacer(1, 15))
    
    # Tizim bo'yicha
    if stats_data.get('by_system'):
        story.append(Paragraph(_("Tizimlar bo'yicha (Top 10)"), styles['Heading3']))
        data = [[_('Tizim'), _('Soni')]]
        for item in stats_data['by_system']:
            data.append([item['system__name'], str(item['count'])])
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(get_simple_table_style())
        story.append(table)
        story.append(Spacer(1, 15))


def add_technician_performance(story, performance_data, styles, heading_style):
    """Texniklar samaradorligi"""
    
    story.append(Paragraph(_("Texniklar samaradorligi"), heading_style))
    story.append(Spacer(1, 12))
    
    data = [
        [
            _('Texnik'),
            _('Jami'),
            _('Hal qilingan'),
            _('Jarayonda'),
            _('Qayta ochilgan'),
            _('O\'rtacha baho'),
        ]
    ]
    
    for item in performance_data:
        full_name = f"{item['assigned_to__first_name']} {item['assigned_to__last_name']}"
        data.append([
            full_name,
            str(item['total_assigned']),
            str(item['resolved']),
            str(item['in_progress']),
            str(item['reopened']),
            f"{item['avg_rating']:.1f}⭐" if item['avg_rating'] else '-',
        ])
    
    table = Table(data)
    table.setStyle(get_simple_table_style())
    story.append(table)


def add_system_analysis(story, analysis_data, styles, heading_style):
    """Tizimlar tahlili"""
    
    story.append(Paragraph(_("Tizimlar tahlili"), heading_style))
    story.append(Spacer(1, 12))
    
    data = [
        [_('Tizim'), _('Jami'), _('Hal qilingan'), _('O\'rtacha baho'), _('Yuqori ustuvorlik')]
    ]
    
    for item in analysis_data:
        data.append([
            item['system__name'],
            str(item['total']),
            str(item['resolved']),
            f"{item['avg_rating']:.1f}⭐" if item['avg_rating'] else '-',
            str(item['high_priority']),
        ])
    
    table = Table(data)
    table.setStyle(get_simple_table_style())
    story.append(table)


def add_regional_analysis(story, analysis_data, styles, heading_style):
    """Viloyatlar tahlili"""
    
    story.append(Paragraph(_("Viloyatlar tahlili"), heading_style))
    story.append(Spacer(1, 12))
    
    data = [
        [_('Viloyat'), _('Jami'), _('Hal qilingan'), _('Jarayonda'), _('O\'rtacha baho')]
    ]
    
    for item in analysis_data:
        data.append([
            item['region__name'] or '-',
            str(item['total']),
            str(item['resolved']),
            str(item['in_progress']),
            f"{item['avg_rating']:.1f}⭐" if item['avg_rating'] else '-',
        ])
    
    table = Table(data)
    table.setStyle(get_simple_table_style())
    story.append(table)


def get_simple_table_style():
    """Oddiy jadval style"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ])


def get_filter_info_text(filters):
    """Filter ma'lumotlari"""
    parts = []
    
    if filters.get('date_from') and filters.get('date_to'):
        parts.append(f"{filters['date_from'].strftime('%d.%m.%Y')} - {filters['date_to'].strftime('%d.%m.%Y')}")
    
    if filters.get('system'):
        parts.append(f"{_('Tizim')}: {filters['system'].name}")
    
    if filters.get('region'):
        parts.append(f"{_('Viloyat')}: {filters['region'].name}")
    
    if filters.get('status'):
        parts.append(f"{_('Holat')}: {filters['status']}")
    
    if filters.get('assigned_to'):
        parts.append(f"{_('Mas\'ul')}: {filters['assigned_to'].get_full_name()}")
    
    return " • ".join(parts)