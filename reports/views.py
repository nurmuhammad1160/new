# reports/views.py - TO'G'RILANGAN

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta

from tickets.models import Ticket, TicketHistory
from accounts.models import User, Region
from systems.models import System
from .forms import ReportFilterForm
from .utils.pdf_generator import generate_pdf_report
from .utils.excel_generator import generate_excel_report
from .utils.csv_generator import generate_csv_report


def require_admin(view_func):
    """Admin yoki SuperAdmin bo'lishi kerak"""
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_admin() or request.user.is_superadmin()):
            messages.error(request, _('Sizda hisobotlarni ko\'rish huquqi yo\'q.'))
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@require_admin
def reports_dashboard(request):
    """Hisobotlar asosiy sahifasi"""
    
    form = ReportFilterForm(request.GET or None)
    
    # Default: oxirgi 30 kun
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = timezone.now().strftime('%Y-%m-%d')
    
    # ✅ YANGILANGAN: Tezkor statistika
    quick_stats = get_quick_stats(date_from, date_to, request.user)
    
    context = {
        'form': form,
        'date_from': date_from,
        'date_to': date_to,
        'quick_stats': quick_stats,
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
@require_admin
def generate_report(request):
    """Hisobot yaratish va export qilish"""
    
    if request.method != 'POST' and request.method != 'GET':
        return redirect('reports:dashboard')
    
    form = ReportFilterForm(request.POST or request.GET)
    
    if not form.is_valid():
        messages.error(request, _('Filterlarni to\'g\'ri to\'ldiring.'))
        return redirect('reports:dashboard')
    
    # Filter parametrlari
    filters = get_filters_from_form(form)
    
    # Ticketlarni olish
    tickets = Ticket.objects.all()
    
    # ✅ YANGI: Admin ruxsatlariga qarab filtrlash
    from accounts.utils import filter_tickets_for_admin
    tickets = filter_tickets_for_admin(tickets, request.user)
    
    # Filtrlash
    if filters['date_from']:
        tickets = tickets.filter(created_at__date__gte=filters['date_from'])
    
    if filters['date_to']:
        tickets = tickets.filter(created_at__date__lte=filters['date_to'])
    
    if filters['system']:
        tickets = tickets.filter(system=filters['system'])
    
    if filters['region']:
        tickets = tickets.filter(region=filters['region'])
    
    if filters['status']:
        tickets = tickets.filter(status=filters['status'])
    
    if filters['priority']:
        tickets = tickets.filter(priority=filters['priority'])
    
    if filters['assigned_to']:
        tickets = tickets.filter(assigned_to=filters['assigned_to'])
    
    if filters['rating']:
        if filters['rating'] == 'none':
            tickets = tickets.filter(rating__isnull=True)
        else:
            tickets = tickets.filter(rating=int(filters['rating']))
    
    # Export format
    export_format = form.cleaned_data.get('export_format')
    report_type = form.cleaned_data.get('report_type', 'tickets')
    
    # Statistika hisobotlar uchun
    if report_type == 'statistics':
        stats_data = get_statistics_data(tickets, filters)
    elif report_type == 'technician_performance':
        stats_data = get_technician_performance(tickets, filters)
    elif report_type == 'system_analysis':
        stats_data = get_system_analysis(tickets, filters)
    elif report_type == 'regional_analysis':
        stats_data = get_regional_analysis(tickets, filters)
    else:
        stats_data = None
    
    # Export
    if export_format == 'pdf':
        return generate_pdf_report(tickets, filters, report_type, stats_data)
    
    elif export_format == 'excel':
        return generate_excel_report(tickets, filters, report_type, stats_data)
    
    elif export_format == 'csv':
        return generate_csv_report(tickets, filters)
    
    # Web ko'rinish
    else:
        context = {
            'form': form,
            'tickets': tickets.order_by('-created_at')[:500],  # Limitlash
            'filters': filters,
            'report_type': report_type,
            'stats_data': stats_data,
            'total_count': tickets.count(),
        }
        
        if report_type == 'tickets':
            return render(request, 'reports/tickets_report.html', context)
        else:
            return render(request, 'reports/stats_report.html', context)


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_filters_from_form(form):
    """Form dan filterlarni olish"""
    return {
        'date_from': form.cleaned_data.get('date_from'),
        'date_to': form.cleaned_data.get('date_to'),
        'system': form.cleaned_data.get('system'),
        'region': form.cleaned_data.get('region'),
        'status': form.cleaned_data.get('status'),
        'priority': form.cleaned_data.get('priority'),
        'assigned_to': form.cleaned_data.get('assigned_to'),
        'rating': form.cleaned_data.get('rating'),
    }


# reports/views.py - get_quick_stats TO'G'RILASH

def get_quick_stats(date_from, date_to, user):
    """Tezkor statistika - TO'G'RILANGAN"""
    
    # Barcha ticketlar (sana filtri bilan)
    all_tickets = Ticket.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    # ✅ YANGI: Biriktirilmagan - ADMIN FILTRSIZ!
    # Sabab: Biriktirilmagan murojaatlar hali hech qaysi adminga tegishli emas
    unassigned_tickets = all_tickets.filter(
        assigned_to__isnull=True, 
        status='new'
    )
    
    # ✅ Agar admin bo'lsa - faqat o'z tizim/viloyati bo'yicha biriktirilmaganlarni ko'rsatish
    from accounts.utils import get_admin_systems, get_admin_regions
    
    if user.is_admin() and not user.is_superadmin():
        # Tizimlar bo'yicha filtrlash
        allowed_systems = get_admin_systems(user)
        if allowed_systems is not None:
            unassigned_tickets = unassigned_tickets.filter(system__in=allowed_systems)
        
        # Viloyatlar bo'yicha filtrlash
        allowed_regions = get_admin_regions(user)
        if allowed_regions is not None and allowed_regions != []:
            unassigned_tickets = unassigned_tickets.filter(region_id__in=allowed_regions)
    
    # Boshqa statistikalar - admin ruxsatlariga qarab
    from accounts.utils import filter_tickets_for_admin
    filtered_tickets = filter_tickets_for_admin(all_tickets, user)
    
    return {
        'total': filtered_tickets.count(),
        'unassigned': unassigned_tickets.count(),  # ✅ Alohida filtrlangan
        'in_progress': filtered_tickets.filter(status='in_progress').count(),
        'resolved': filtered_tickets.filter(status='resolved').count(),
        'avg_rating': filtered_tickets.filter(rating__isnull=False).aggregate(
            Avg('rating')
        )['rating__avg'] or 0,
    }


def get_statistics_data(tickets, filters):
    """Umumiy statistika"""
    
    # Status bo'yicha
    by_status = tickets.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Tizim bo'yicha
    by_system = tickets.values('system__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Viloyat bo'yicha
    by_region = tickets.values('region__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Ustuvorlik bo'yicha
    by_priority = tickets.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Baholash bo'yicha
    by_rating = tickets.filter(rating__isnull=False).values('rating').annotate(
        count=Count('id')
    ).order_by('-rating')
    
    return {
        'by_status': by_status,
        'by_system': by_system,
        'by_region': by_region,
        'by_priority': by_priority,
        'by_rating': by_rating,
    }


def get_technician_performance(tickets, filters):
    """Texniklar samaradorligi"""
    
    performance = tickets.filter(
        assigned_to__isnull=False
    ).values(
        'assigned_to__first_name',
        'assigned_to__last_name',
        'assigned_to__id'
    ).annotate(
        total_assigned=Count('id'),
        resolved=Count('id', filter=Q(status='resolved')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        reopened=Count('id', filter=Q(status='reopened')),
        avg_rating=Avg('rating'),
    ).order_by('-resolved')
    
    return performance


def get_system_analysis(tickets, filters):
    """Tizimlar tahlili"""
    
    analysis = tickets.values('system__name').annotate(
        total=Count('id'),
        resolved=Count('id', filter=Q(status='resolved')),
        avg_rating=Avg('rating'),
        high_priority=Count('id', filter=Q(priority='high')),
    ).order_by('-total')
    
    return analysis


def get_regional_analysis(tickets, filters):
    """Viloyatlar tahlili"""
    
    analysis = tickets.values('region__name').annotate(
        total=Count('id'),
        resolved=Count('id', filter=Q(status='resolved')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        avg_rating=Avg('rating'),
    ).order_by('-total')
    
    return analysis