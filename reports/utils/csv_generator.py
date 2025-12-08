# reports/utils/csv_generator.py

import csv
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _


def generate_csv_report(tickets, filters):
    """CSV hisobot yaratish (faqat ticketlar ro'yxati)"""
    
    # Response
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOM for Excel UTF-8 support
    response.write('\ufeff')
    
    # CSV Writer
    writer = csv.writer(response)
    
    # Headers
    writer.writerow([
        _('ID'),
        _('Sana'),
        _('Vaqt'),
        _('Tizim'),
        _('Viloyat'),
        _('Foydalanuvchi (F.I.Sh)'),
        _('Foydalanuvchi (Login)'),
        _('Telefon'),
        _('Holat'),
        _('Ustuvorlik'),
        _('Mas\'ul xodim'),
        _('Mas\'ul xodim (Login)'),
        _('Muammo ta\'rifi'),
        _('Baho'),
        _('Baho izohi'),
        _('Yaratilgan'),
        _('Yangilangan'),
    ])
    
    # Data rows
    for ticket in tickets:
        writer.writerow([
            ticket.get_ticket_number(),
            ticket.created_at.strftime('%d.%m.%Y'),
            ticket.created_at.strftime('%H:%M'),
            ticket.system.name,
            ticket.region.name if ticket.region else '',
            ticket.user.get_full_name(),
            ticket.user.username,
            ticket.user.phone or '',
            ticket.get_status_display(),
            ticket.get_priority_display(),
            ticket.assigned_to.get_full_name() if ticket.assigned_to else '',
            ticket.assigned_to.username if ticket.assigned_to else '',
            ticket.description[:200],  # Limit
            ticket.rating if ticket.rating else '',
            ticket.rating_comment if ticket.rating_comment else '',
            ticket.created_at.strftime('%d.%m.%Y %H:%M:%S'),
            ticket.updated_at.strftime('%d.%m.%Y %H:%M:%S'),
        ])
    
    return response