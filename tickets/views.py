from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Ticket, TicketMessage, TicketHistory
from .forms import TicketCreateForm, TicketMessageForm, TicketRatingForm, TicketFilterForm
from systems.models import SystemResponsible, System
from notifications.models import Notification
from accounts.models import User


# ============================================
# DECORATORS
# ============================================

def require_technician(view_func):
    """Texnik yoki admin bo'lishini talab qiluvchi decorator"""
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_technician() or request.user.is_admin()):
            messages.error(request, _('Sizda bu sahifaga kirish huquqi yo\'q.'))
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_admin(view_func):
    """Admin bo'lishini talab qiluvchi decorator"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, _('Sizda bu sahifaga kirish huquqi yo\'q.'))
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# USER VIEWS
# ============================================

@login_required
def dashboard(request):
    """Foydalanuvchi dashboard"""
    user = request.user
    
    # Texnik yoki admin bo'lsa - o'z dashboardiga yo'naltirish
    if user.is_technician() and not user.is_admin():
        return redirect('tickets:technician_tickets')
    elif user.is_admin():
        return redirect('tickets:admin_dashboard')
    
    # Statistika
    tickets = Ticket.objects.filter(user=user)
    
    stats = {
        'today': tickets.filter(created_at__date=timezone.now().date()).count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status='resolved').count(),
        'rejected': tickets.filter(status='rejected').count(),
    }
    
    # Filter form
    filter_form = TicketFilterForm(request.GET)
    
    # Filtrlash
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('system'):
            tickets = tickets.filter(system=filter_form.cleaned_data['system'])
        if filter_form.cleaned_data.get('status'):
            tickets = tickets.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('priority'):
            tickets = tickets.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data.get('date_from'):
            tickets = tickets.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            tickets = tickets.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    tickets = tickets.order_by('-created_at')[:50]
    
    # Tizimlar ro'yxati (modal uchun)
    all_systems = System.objects.filter(is_active=True).order_by('name')
    
    context = {
        'stats': stats,
        'tickets': tickets,
        'filter_form': filter_form,
        'all_systems': all_systems,
    }
    
    return render(request, 'tickets/dashboard.html', context)


@login_required
def create_ticket(request):
    """Yangi murojaat yaratish"""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            
            # Region tekshirish
            if not request.user.region:
                messages.error(request, _('Profilingizda viloyat belgilanmagan. Iltimos profilni to\'ldiring.'))
                return redirect('accounts:profile')
            
            ticket.region = request.user.region
            ticket.status = 'new'
            
            # Mas'ul texnikni topish
            system = ticket.system
            region = ticket.region
            
            # 1. Avval region bo'yicha mas'ul texnikni qidirish
            responsible = SystemResponsible.objects.filter(
                system=system,
                region=region,
                role_in_system='technician'
            ).first()
            
            # 2. Topilmasa - respublika miqyosidagi default mas'ulni olish
            if not responsible:
                responsible = SystemResponsible.objects.filter(
                    system=system,
                    region__isnull=True,
                    is_default=True,
                    role_in_system='technician'
                ).first()
            
            # 3. Agar topilsa - assigned_to ga belgilash
            if responsible:
                ticket.assigned_to = responsible.user
            
            ticket.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='created',
                message=_('Murojaat yaratildi')
            )
            
            # Notification (mas'ul xodimga)
            if ticket.assigned_to:
                Notification.objects.create(
                    user=ticket.assigned_to,
                    notification_type='new_ticket',
                    title=_('Yangi murojaat'),
                    text=_('Sizga yangi murojaat biriktirildi: {}').format(ticket.get_ticket_number()),
                    url=f'/tickets/{ticket.id}/'
                )
            
            messages.success(request, _('Murojaat muvaffaqiyatli yuborildi!'))
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        form = TicketCreateForm()
    
    return render(request, 'tickets/create_ticket.html', {'form': form})


@login_required
def ticket_detail(request, pk):
    """Murojaat tafsilotlari"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Ruxsat tekshirish
    if not (request.user == ticket.user or 
            request.user == ticket.assigned_to or 
            request.user.is_admin()):
        messages.error(request, _('Sizda bu murojaatni ko\'rish huquqi yo\'q.'))
        return redirect('tickets:dashboard')
    
    # Chat xabarlari
    messages_list = ticket.messages.all().order_by('created_at')
    
    # Tarix
    history = ticket.history.all().order_by('timestamp')
    
    # Yangi xabar formasi
    message_form = TicketMessageForm()
    
    # Baholash formasi (agar status "pending_approval" bo'lsa)
    rating_form = None
    if ticket.status == 'pending_approval' and request.user == ticket.user:
        rating_form = TicketRatingForm(instance=ticket)
    
    # Mas'ul texniklar ro'yxati (admin uchun)
    available_technicians = None
    if request.user.is_admin():
        available_technicians = User.objects.filter(
            role__in=['technician', 'admin'],
            is_active=True
        ).order_by('first_name')
    
    context = {
        'ticket': ticket,
        'messages': messages_list,
        'history': history,
        'message_form': message_form,
        'rating_form': rating_form,
        'available_technicians': available_technicians,
    }
    
    return render(request, 'tickets/ticket_detail.html', context)


@login_required
def send_message(request, pk):
    """Chat xabari yuborish"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Ruxsat tekshirish
    if not (request.user == ticket.user or 
            request.user == ticket.assigned_to or 
            request.user.is_admin()):
        messages.error(request, _('Sizda bu murojaatga xabar yuborish huquqi yo\'q.'))
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            ticket_message = form.save(commit=False)
            ticket_message.ticket = ticket
            ticket_message.sender = request.user
            ticket_message.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='comment',
                message=_('Yangi xabar qo\'shildi')
            )
            
            # Notification (qabul qiluvchiga)
            recipient = ticket.user if request.user == ticket.assigned_to else ticket.assigned_to
            if recipient:
                Notification.objects.create(
                    user=recipient,
                    notification_type='new_message',
                    title=_('Yangi xabar'),
                    text=_('Murojaat bo\'yicha yangi xabar: {}').format(ticket.get_ticket_number()),
                    url=f'/tickets/{ticket.id}/'
                )
            
            messages.success(request, _('Xabar yuborildi.'))
    
    return redirect('tickets:ticket_detail', pk=pk)


@login_required
def rate_ticket(request, pk):
    """Murojaatni baholash"""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    
    if ticket.status != 'pending_approval':
        messages.error(request, _('Bu murojaatni hozir baholab bo\'lmaydi.'))
        return redirect('tickets:ticket_detail', pk=pk)
    
    if request.method == 'POST':
        form = TicketRatingForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            rating = ticket.rating
            
            # Baholashga qarab status o'zgartirish
            if rating >= 4:
                # Yaxshi baho - hal qilindi
                ticket.status = 'resolved'
                ticket.resolved_at = timezone.now()
                status_message = _('Murojaat hal qilindi deb belgilandi')
            else:
                # Yomon baho - qayta ochish
                ticket.status = 'reopened'
                status_message = _('Murojaat qayta ochildi')
            
            ticket.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='rated',
                new_value=str(rating),
                message=status_message
            )
            
            # Notification (mas'ul xodimga)
            if ticket.assigned_to:
                Notification.objects.create(
                    user=ticket.assigned_to,
                    notification_type='rating_request',
                    title=_('Murojaat baholandi'),
                    text=_('Murojaat {} baho bilan baholandi: {}').format(rating, ticket.get_ticket_number()),
                    url=f'/tickets/{ticket.id}/'
                )
            
            messages.success(request, _('Baholash saqlandi. Rahmat!'))
            return redirect('tickets:ticket_detail', pk=pk)
    
    return redirect('tickets:ticket_detail', pk=pk)


@login_required
def reopen_ticket(request, pk):
    """Murojaatni qayta ochish"""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    
    if ticket.status != 'resolved':
        messages.error(request, _('Faqat hal qilingan murojaatlarni qayta ochish mumkin.'))
        return redirect('tickets:ticket_detail', pk=pk)
    
    ticket.status = 'reopened'
    ticket.save()
    
    # Audit log
    TicketHistory.objects.create(
        ticket=ticket,
        changed_by=request.user,
        action_type='reopened',
        old_value='resolved',
        new_value='reopened',
        message=_('Foydalanuvchi tomonidan qayta ochildi')
    )
    
    # Notification (mas'ul xodimga)
    if ticket.assigned_to:
        Notification.objects.create(
            user=ticket.assigned_to,
            notification_type='status_changed',
            title=_('Murojaat qayta ochildi'),
            text=_('Murojaat foydalanuvchi tomonidan qayta ochildi: {}').format(ticket.get_ticket_number()),
            url=f'/tickets/{ticket.id}/'
        )
    
    messages.success(request, _('Murojaat qayta ochildi.'))
    return redirect('tickets:ticket_detail', pk=pk)


@login_required
def system_responsibles_view(request):
    """Tizimlar bo'yicha mas'ullar ro'yxati"""
    user_region = request.user.region
    
    # Foydalanuvchi viloyati bo'yicha mas'ullar
    systems = System.objects.filter(is_active=True)
    
    responsibles_data = []
    for system in systems:
        # Region bo'yicha mas'ul admin
        admin = SystemResponsible.objects.filter(
            system=system,
            region=user_region,
            role_in_system='admin'
        ).first()
        
        # Agar topilmasa - respublika admini
        if not admin:
            admin = SystemResponsible.objects.filter(
                system=system,
                region__isnull=True,
                is_default=True,
                role_in_system='admin'
            ).first()
        
        # Region bo'yicha mas'ul texniklar
        technicians = SystemResponsible.objects.filter(
            system=system,
            region=user_region,
            role_in_system='technician'
        )
        
        # Agar topilmasa - respublika texniklari
        if not technicians.exists():
            technicians = SystemResponsible.objects.filter(
                system=system,
                region__isnull=True,
                is_default=True,
                role_in_system='technician'
            )
        
        responsibles_data.append({
            'system': system,
            'admin': admin,
            'technicians': technicians,
        })
    
    context = {
        'responsibles_data': responsibles_data,
    }
    
    return render(request, 'tickets/system_responsibles.html', context)


# ============================================
# TECHNICIAN VIEWS
# ============================================

@login_required
@require_technician
def technician_tickets(request):
    """Texnik xodim - o'ziga biriktirilgan ticketlar"""
    tickets = Ticket.objects.filter(assigned_to=request.user)
    
    # Statistika
    stats = {
        'new': tickets.filter(status='new').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'pending': tickets.filter(status='pending_approval').count(),
        'resolved_today': tickets.filter(
            status='resolved',
            resolved_at__date=timezone.now().date()
        ).count(),
    }
    
    # Filter
    filter_form = TicketFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('status'):
            tickets = tickets.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('priority'):
            tickets = tickets.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data.get('system'):
            tickets = tickets.filter(system=filter_form.cleaned_data['system'])
    
    tickets = tickets.order_by('-created_at')[:50]
    
    context = {
        'stats': stats,
        'tickets': tickets,
        'filter_form': filter_form,
    }
    
    return render(request, 'tickets/technician_tickets.html', context)


@login_required
@require_technician
def change_ticket_status(request, pk):
    """Ticket holati o'zgartirish"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Ruxsat tekshirish
    if not (request.user == ticket.assigned_to or request.user.is_admin()):
        messages.error(request, _('Sizda bu murojaatni o\'zgartirish huquqi yo\'q.'))
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # Status o'zgarishini tekshirish
        valid_transitions = {
            'new': ['in_progress', 'rejected'],
            'in_progress': ['pending_approval', 'rejected'],
            'reopened': ['in_progress', 'rejected'],
        }
        
        current_status = ticket.status
        if new_status in valid_transitions.get(current_status, []):
            old_status = ticket.get_status_display()
            ticket.status = new_status
            ticket.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='status_changed',
                old_value=current_status,
                new_value=new_status,
                message=_('Status o\'zgartirildi: {} → {}').format(
                    old_status,
                    ticket.get_status_display()
                )
            )
            
            # Notification (foydalanuvchiga)
            Notification.objects.create(
                user=ticket.user,
                notification_type='status_changed',
                title=_('Murojaat holati o\'zgartirildi'),
                text=_('Murojaat {} holati: {}').format(
                    ticket.get_ticket_number(),
                    ticket.get_status_display()
                ),
                url=f'/tickets/{ticket.id}/'
            )
            
            messages.success(request, _('Murojaat holati o\'zgartirildi.'))
        else:
            messages.error(request, _('Noto\'g\'ri holat o\'zgarishi.'))
    
    return redirect('tickets:ticket_detail', pk=pk)


# ============================================
# ADMIN VIEWS
# ============================================

@login_required
@require_admin
def admin_dashboard(request):
    """Admin dashboard - barcha ticketlar va statistika"""
    # Vaqt davri
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    tickets = Ticket.objects.all()
    
    # Umumiy statistika
    stats = {
        'total': tickets.count(),
        'today': tickets.filter(created_at__date=today).count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status='resolved').count(),
        'rejected': tickets.filter(status='rejected').count(),
        'reopened': tickets.filter(status='reopened').count(),
        'avg_rating': tickets.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    # Tizimlar bo'yicha
    by_system = tickets.values('system__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Viloyatlar bo'yicha
    by_region = tickets.values('region__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Texniklar bo'yicha baholash
    technician_stats = tickets.filter(
        rating__isnull=False,
        assigned_to__isnull=False
    ).values(
        'assigned_to__first_name',
        'assigned_to__last_name'
    ).annotate(
        avg_rating=Avg('rating'),
        total_tickets=Count('id')
    ).order_by('-avg_rating')[:10]
    
    # Filter
    filter_form = TicketFilterForm(request.GET)
    filtered_tickets = tickets
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('system'):
            filtered_tickets = filtered_tickets.filter(system=filter_form.cleaned_data['system'])
        if filter_form.cleaned_data.get('status'):
            filtered_tickets = filtered_tickets.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('priority'):
            filtered_tickets = filtered_tickets.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data.get('date_from'):
            filtered_tickets = filtered_tickets.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            filtered_tickets = filtered_tickets.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    filtered_tickets = filtered_tickets.order_by('-created_at')[:100]
    
    context = {
        'stats': stats,
        'by_system': by_system,
        'by_region': by_region,
        'technician_stats': technician_stats,
        'tickets': filtered_tickets,
        'filter_form': filter_form,
    }
    
    return render(request, 'tickets/admin_dashboard.html', context)


@login_required
@require_admin
def assign_ticket(request, pk):
    """Ticketni texnikga biriktirish"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        new_assigned_id = request.POST.get('assigned_to')
        
        if new_assigned_id:
            new_assigned = get_object_or_404(User, pk=new_assigned_id)
            old_assigned = ticket.assigned_to
            
            ticket.assigned_to = new_assigned
            ticket.save()
            
            # Audit log
            action_type = 'reassigned' if old_assigned else 'assigned'
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type=action_type,
                old_value=old_assigned.get_full_name() if old_assigned else '',
                new_value=new_assigned.get_full_name(),
                message=_('Mas\'ul xodim o\'zgartirildi')
            )
            
            # Notification (yangi mas'ul xodimga)
            Notification.objects.create(
                user=new_assigned,
                notification_type='ticket_assigned',
                title=_('Sizga murojaat biriktirildi'),
                text=_('Yangi murojaat: {}').format(ticket.get_ticket_number()),
                url=f'/tickets/{ticket.id}/'
            )
            
            messages.success(request, _('Mas\'ul xodim o\'zgartirildi.'))
    
    return redirect('tickets:ticket_detail', pk=pk)


@login_required
@require_admin
def users_list(request):
    """Foydalanuvchilar ro'yxati"""
    users = User.objects.all().order_by('-date_joined')
    
    # Filter
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    region = request.GET.get('region')
    if region:
        users = users.filter(region_id=region)
    
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search)
        )
    
    from accounts.models import Region
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    context = {
        'users': users[:100],
        'all_regions': all_regions,
    }
    
    return render(request, 'tickets/users_list.html', context)


@login_required
@require_admin
def change_user_role(request, user_id):
    """Foydalanuvchi rolini o'zgartirish"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in ['user', 'technician', 'admin', 'superadmin']:
            # Faqat superadmin boshqa adminlarni o'zgartira oladi
            if user.is_admin() and not request.user.is_superadmin():
                messages.error(request, _('Sizda admin rolini o\'zgartirish huquqi yo\'q.'))
            else:
                old_role = user.get_role_display()
                user.role = new_role
                user.save()
                messages.success(
                    request,
                    _('Foydalanuvchi roli o\'zgartirildi: {} → {}').format(
                        old_role,
                        user.get_role_display()
                    )
                )
    
    return redirect('tickets:users_list')