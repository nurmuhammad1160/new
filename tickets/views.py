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
from accounts.utils import (
    get_admin_systems, 
    get_admin_regions, 
    filter_tickets_for_admin,
    get_admin_context
)


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


# tickets/views.py - create_ticket TO'G'RILASH

@login_required
def create_ticket(request):
    """Yangi murojaat yaratish"""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            
            if not request.user.region:
                messages.error(request, _('Profilingizda viloyat belgilanmagan.'))
                return redirect('accounts:profile')
            
            ticket.region = request.user.region
            ticket.status = 'new'
            
            # Mas'ul texnikni topish
            system = ticket.system
            region = ticket.region
            
            # 1. Region bo'yicha texnik
            responsible = SystemResponsible.objects.filter(
                system=system,
                region=region,
                role_in_system='technician'
            ).first()
            
            # 2. Default respublikanskiy texnik
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
                ticket.assignment_type = 'auto'
            
            ticket.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='created',
                message=_('Murojaat yaratildi')
            )
            
            # ✅ TO'G'RILANGAN: Notifikatsiyalar
            recipients = []
            
            # Respublikanskiy Admin - TO'G'RI related_name
            resp_admins = User.objects.filter(
                system_responsibilities__system=ticket.system,  # ✅ TO'G'RI!
                system_responsibilities__region__isnull=True,
                system_responsibilities__role_in_system='admin',
                is_active=True
            )
            recipients.extend(resp_admins)
            
            # Viloyat Admin - TO'G'RI related_name
            region_admins = User.objects.filter(
                system_responsibilities__system=ticket.system,  # ✅ TO'G'RI!
                system_responsibilities__region=ticket.region,
                system_responsibilities__role_in_system='admin',
                is_active=True
            )
            recipients.extend(region_admins)
            
            # Avtomatik biriktirilgan texnikga
            if ticket.assigned_to:
                recipients.append(ticket.assigned_to)
            
            # Notifikatsiya yuborish
            for recipient in recipients:
                Notification.objects.create(
                    user=recipient,
                    notification_type='new_ticket',
                    title=_('Yangi murojaat'),
                    text=_('Yangi murojaat #{}: {}').format(
                        ticket.get_ticket_number(), 
                        ticket.system.name
                    ),
                    url=f'/tickets/{ticket.id}/'
                )
            
            messages.success(request, _('Murojaat muvaffaqiyatli yuborildi!'))
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        form = TicketCreateForm()
    
    return render(request, 'tickets/create_ticket.html', {'form': form})


@login_required
def ticket_detail(request, pk):
    """Murojaat tafsilotlari - ADMIN RUXSATLARI BILAN"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # ============================================
    # RUXSAT TEKSHIRISH
    # ============================================
    
    # 1. Oddiy foydalanuvchi - faqat o'z ticketini
    if request.user.role == 'user':
        if request.user != ticket.user:
            messages.error(request, _('Sizda bu murojaatni ko\'rish huquqi yo\'q.'))
            return redirect('tickets:dashboard')
    
    # 2. Texnik - faqat o'ziga biriktirilgan ticketni
    elif request.user.is_technician() and not request.user.is_admin():
        if request.user != ticket.assigned_to:
            messages.error(request, _('Sizda bu murojaatni ko\'rish huquqi yo\'q.'))
            return redirect('tickets:technician_tickets')
    
    # 3. Admin - tizim va viloyat bo'yicha ruxsat tekshirish
    elif request.user.is_admin() and not request.user.is_superadmin():
        from accounts.utils import can_admin_see_ticket
        
        if not can_admin_see_ticket(request.user, ticket):
            messages.error(request, _('Sizda bu murojaatni ko\'rish huquqi yo\'q. Bu murojaat sizning biriktirilgan tizim yoki viloyatingizga tegishli emas.'))
            return redirect('tickets:admin_dashboard')
    
    # 4. SuperAdmin - hamma narsani ko'radi (ruxsat tekshirilmaydi)
    
    # ============================================
    # CHAT XABARLARI
    # ============================================
    messages_list = ticket.messages.all().order_by('created_at')
    
    # ============================================
    # TARIX (AUDIT LOG)
    # ============================================
    history = ticket.history.all().order_by('timestamp')
    
    # ============================================
    # YANGI XABAR FORMASI
    # ============================================
    message_form = TicketMessageForm()
    
    # ============================================
    # BAHOLASH FORMASI
    # ============================================
    rating_form = None
    if ticket.status == 'pending_approval' and request.user == ticket.user:
        rating_form = TicketRatingForm(instance=ticket)
    
    # ============================================
    # MAS'UL TEXNIKLAR RO'YXATI (ADMIN UCHUN)
    # ============================================
    available_technicians = None
    
    if request.user.is_admin():
        # SuperAdmin uchun - barcha texniklar
        if request.user.is_superadmin():
            available_technicians = User.objects.filter(
                role__in=['technician', 'admin'],
                is_active=True
            ).order_by('first_name')
        
        # Oddiy admin uchun - faqat o'z tizimi va viloyati bo'yicha texniklar
        else:
            from accounts.utils import get_admin_systems, get_admin_regions
            from systems.models import SystemResponsible
            
            allowed_systems = get_admin_systems(request.user)
            allowed_regions = get_admin_regions(request.user)
            
            if allowed_systems is not None:
                # Faqat ruxsat berilgan tizimlar bo'yicha texniklar
                system_ids = allowed_systems.values_list('id', flat=True)
                
                technician_ids = SystemResponsible.objects.filter(
                    system_id__in=system_ids,
                    role_in_system='technician'
                ).values_list('user_id', flat=True)
                
                available_technicians = User.objects.filter(
                    id__in=technician_ids,
                    is_active=True
                ).order_by('first_name')
                
                # Agar viloyat admin bo'lsa - faqat o'z viloyati bo'yicha
                if allowed_regions and allowed_regions != []:
                    available_technicians = available_technicians.filter(
                        region_id__in=allowed_regions
                    )
            else:
                # Agar allowed_systems None bo'lsa - barcha texniklar
                available_technicians = User.objects.filter(
                    role__in=['technician', 'admin'],
                    is_active=True
                ).order_by('first_name')
    
    # ============================================
    # CONTEXT
    # ============================================
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


# tickets/views.py - rate_ticket TO'G'RILASH

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
            
            ticket.status = 'resolved'
            ticket.resolved_at = timezone.now()
            ticket.save()
            
            # Audit log
            TicketHistory.objects.create(
                ticket=ticket,
                changed_by=request.user,
                action_type='rated',
                old_value='pending_approval',
                new_value='resolved',
                message=_('Foydalanuvchi {}⭐ baho berdi. Murojaat hal qilindi.').format(rating)
            )
            
            # ✅ TO'G'RILANGAN: Notifikatsiya
            recipients = []
            
            # 1. Texnikka
            if ticket.assigned_to:
                recipients.append(ticket.assigned_to)
            
            # 2. Viloyat Admin - TO'G'RI related_name
            region_admins = User.objects.filter(
                system_responsibilities__system=ticket.system,  # ✅ TO'G'RI!
                system_responsibilities__region=ticket.region,
                system_responsibilities__role_in_system='admin',
                is_active=True
            )
            recipients.extend(region_admins)
            
            # 3. Respublikanskiy Admin - TO'G'RI related_name
            resp_admins = User.objects.filter(
                system_responsibilities__system=ticket.system,  # ✅ TO'G'RI!
                system_responsibilities__region__isnull=True,
                system_responsibilities__role_in_system='admin',
                is_active=True
            )
            recipients.extend(resp_admins)
            
            # Notifikatsiya yuborish
            for recipient in recipients:
                if rating >= 4:
                    notif_text = _('Murojaat {} {}⭐ bilan baholandi (Yaxshi!)').format(
                        ticket.get_ticket_number(), rating
                    )
                else:
                    notif_text = _('Murojaat {} {}⭐ bilan baholandi (Past baho)').format(
                        ticket.get_ticket_number(), rating
                    )
                
                Notification.objects.create(
                    user=recipient,
                    notification_type='ticket_rated',
                    title=_('Murojaat baholandi'),
                    text=notif_text,
                    url=f'/tickets/{ticket.id}/'
                )
            
            # Message
            if rating >= 4:
                messages.success(request, _('Baholash uchun rahmat! Murojaat hal qilindi.'))
            else:
                messages.success(
                    request, 
                    _('Baholash uchun rahmat! Agar muammo hal bo\'lmagan bo\'lsa, "Qayta ochish" tugmasini bosing.')
                )
            
            return redirect('tickets:ticket_detail', pk=pk)
    
    return redirect('tickets:ticket_detail', pk=pk)



@login_required
def reopen_ticket(request, pk):
    """Murojaatni qayta ochish - YANGILANGAN"""
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    
    # Faqat "resolved" ticketlarni qayta ochish mumkin
    if ticket.status != 'resolved':
        messages.error(request, _('Faqat hal qilingan murojaatlarni qayta ochish mumkin.'))
        return redirect('tickets:ticket_detail', pk=pk)
    
    # ✅ 2-3 kun muddat tekshirish (ixtiyoriy)
    if ticket.resolved_at:
        days_since_resolved = (timezone.now() - ticket.resolved_at).days
        if days_since_resolved > 3:
            messages.error(
                request, 
                _('Qayta ochish muddati tugagan (3 kundan ortiq vaqt o\'tgan).')
            )
            return redirect('tickets:ticket_detail', pk=pk)
    
    # Status o'zgartirish
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
    
    # Texnikga notification
    if ticket.assigned_to:
        Notification.objects.create(
            user=ticket.assigned_to,
            notification_type='ticket_reopened',
            title=_('Murojaat qayta ochildi'),
            text=_('Foydalanuvchi tomonidan qayta ochildi: {}').format(
                ticket.get_ticket_number()
            ),
            url=f'/tickets/{ticket.id}/'
        )
    
    messages.success(request, _('Murojaat qayta ochildi. Texnik yana ko\'rib chiqadi.'))
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

@login_required
def system_responsibles_modal_view(request, system_id):
    system = get_object_or_404(System, id=system_id)
    
    # Shu tizimga tegishli BARCHA mas'ullar (Admin va Texniklar)
    # Viloyatlar bo'yicha tartiblaymiz
    responsibles = SystemResponsible.objects.filter(
        system=system
    ).select_related('user', 'region').order_by('role_in_system', 'region__name')
    
    context = {
        'system': system,
        'responsibles': responsibles
    }
    
    # Biz to'liq sahifa emas, faqat modal ichini qaytaramiz
    return render(request, 'tickets/partials/modal_content.html', context)


# ============================================
# TECHNICIAN VIEWS
# ============================================

# tickets/views.py - technician_tickets YANGILASH

# tickets/views.py - technician_tickets YANGILASH

# tickets/views.py - technician_tickets TO'G'RILASH

@login_required
@require_technician
def technician_tickets(request):
    """Texnik xodim - o'ziga biriktirilgan VA yangi ticketlar"""
    
    # Yangi murojaatlar
    new_tickets_query = Ticket.objects.filter(
        assigned_to__isnull=True,
        status='new'
    )
    
    # Texnik mas'ul bo'lgan tizimlar
    responsible_systems = SystemResponsible.objects.filter(
        user=request.user,
        role_in_system='technician'
    ).values_list('system_id', flat=True)
    
    new_tickets_query = new_tickets_query.filter(system_id__in=responsible_systems)
    
    # ✅ YANGI LOGIKA: Default texnik/admin ekanligini tekshirish
    is_default_tech = SystemResponsible.objects.filter(
        user=request.user,
        role_in_system='technician',
        is_default=True
    ).exists()
    
    # Agar default texnik EMAS va viloyat texniki bo'lsa - faqat o'z viloyati
    if not is_default_tech and request.user.region:
        new_tickets_query = new_tickets_query.filter(region=request.user.region)
    # Agar default texnik bo'lsa - barcha viloyatlar (filter yo'q)
    
    new_tickets = new_tickets_query.order_by('-created_at')[:20]
    
    # Mening murojaatlarim
    my_tickets = Ticket.objects.filter(assigned_to=request.user)
    
    # Statistika
    stats = {
        'new': my_tickets.filter(status='new').count(),
        'in_progress': my_tickets.filter(status='in_progress').count(),
        'pending': my_tickets.filter(status='pending_approval').count(),
        'resolved_today': my_tickets.filter(
            status='resolved',
            resolved_at__date=timezone.now().date()
        ).count(),
        'new_available': new_tickets.count(),
    }
    
    # Filter
    filter_form = TicketFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('status'):
            my_tickets = my_tickets.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('priority'):
            my_tickets = my_tickets.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data.get('system'):
            my_tickets = my_tickets.filter(system=filter_form.cleaned_data['system'])
    
    my_tickets = my_tickets.order_by('-created_at')[:50]
    
    context = {
        'stats': stats,
        'new_tickets': new_tickets,
        'my_tickets': my_tickets,
        'filter_form': filter_form,
    }
    
    return render(request, 'tickets/technician_tickets.html', context)



# tickets/views.py - YANGI VIEW QO'SHISH

@login_required
@require_technician
def take_ticket(request, pk):
    """Texnik murojaatni o'zi oladi"""
    
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Tekshirish: hali hech kimga berilmaganmi?
    if ticket.assigned_to is not None:
        messages.error(request, _('Bu murojaat allaqachon biriktirilgan.'))
        return redirect('tickets:technician_tickets')
    
    # Tekshirish: texnik shu tizimga mas'ulmi?
    from systems.models import SystemResponsible
    is_responsible = SystemResponsible.objects.filter(
        user=request.user,
        system=ticket.system,
        role_in_system='technician'
    ).exists()
    
    if not is_responsible:
        messages.error(request, _('Sizda bu tizim bo\'yicha murojaat olish huquqi yo\'q.'))
        return redirect('tickets:technician_tickets')
    
    # Agar viloyat texniki bo'lsa - faqat o'z viloyatini
    if request.user.region and ticket.region != request.user.region:
        messages.error(request, _('Bu murojaat boshqa viloyatga tegishli.'))
        return redirect('tickets:technician_tickets')
    
    # ✅ Biriktirish
    ticket.assigned_to = request.user
    ticket.status = 'in_progress'
    ticket.assignment_type = 'self'  # ✅ Texnik o'zi oldi
    ticket.save()
    
    # Audit log
    TicketHistory.objects.create(
        ticket=ticket,
        changed_by=request.user,
        action_type='assigned',
        new_value=request.user.get_full_name(),
        message=_("{} murojaatni o'zi qabul qildi").format(request.user.get_full_name())
    )
    
    # Notifikatsiya (foydalanuvchiga)
    Notification.objects.create(
        user=ticket.user,
        notification_type='ticket_assigned',
        title=_('Murojaatingiz qabul qilindi'),
        text=_('Murojaat {} texnik tomonidan qabul qilindi: {}').format(
            ticket.get_ticket_number(),
            request.user.get_full_name()
        ),
        url=f'/tickets/{ticket.id}/'
    )
    
    messages.success(request, _('Murojaat muvaffaqiyatli qabul qilindi!'))
    return redirect('tickets:ticket_detail', pk=pk)

# tickets/views.py - YANGI VIEW QO'SHISH

# tickets/views.py - new_tickets_list TO'G'RILASH

@login_required
@require_technician
def new_tickets_list(request):
    """Yangi murojaatlar - alohida sahifa"""
    
    # Yangi murojaatlar
    new_tickets_query = Ticket.objects.filter(
        assigned_to__isnull=True,
        status='new'
    )
    
    # Texnik mas'ul bo'lgan tizimlar
    responsible_systems = SystemResponsible.objects.filter(
        user=request.user,
        role_in_system='technician'
    ).values_list('system_id', flat=True)
    
    new_tickets_query = new_tickets_query.filter(system_id__in=responsible_systems)
    
    # ✅ YANGI LOGIKA: Default texnik/admin ekanligini tekshirish
    is_default_tech = SystemResponsible.objects.filter(
        user=request.user,
        role_in_system='technician',
        is_default=True
    ).exists()
    
    # Agar default texnik EMAS va viloyat texniki bo'lsa - faqat o'z viloyati
    if not is_default_tech and request.user.region:
        new_tickets_query = new_tickets_query.filter(region=request.user.region)
    # Agar default texnik bo'lsa - barcha viloyatlar (filter yo'q)
    
    # FILTRLASH
    filter_form = TicketFilterForm(request.GET)
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('system'):
            new_tickets_query = new_tickets_query.filter(system=filter_form.cleaned_data['system'])
        
        if filter_form.cleaned_data.get('priority'):
            new_tickets_query = new_tickets_query.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data.get('date_from'):
            new_tickets_query = new_tickets_query.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            new_tickets_query = new_tickets_query.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    new_tickets = new_tickets_query.order_by('-created_at')
    
    # Statistika
    stats = {
        'total': new_tickets.count(),
        'today': new_tickets.filter(created_at__date=timezone.now().date()).count(),
        'low': new_tickets.filter(priority='low').count(),
        'medium': new_tickets.filter(priority='medium').count(),
        'high': new_tickets.filter(priority='high').count(),
    }
    
    # ✅ YANGI: Default texnik ekanligini templatega yuborish
    context = {
        'new_tickets': new_tickets,
        'stats': stats,
        'filter_form': filter_form,
        'is_default_tech': is_default_tech,  # ✅ YANGI
    }
    
    return render(request, 'tickets/new_tickets_list.html', context)


@login_required
@require_technician
def change_ticket_status(request, pk):
    """Ticket holati o'zgartirish - YANGILANGAN"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Ruxsat tekshirish
    if not (request.user == ticket.assigned_to or request.user.is_admin()):
        messages.error(request, _('Sizda bu murojaatni o\'zgartirish huquqi yo\'q.'))
        return redirect('tickets:dashboard')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # ✅ YANGILANGAN: Status o'zgarishini tekshirish
        valid_transitions = {
            'new': ['in_progress', 'rejected'],
            'in_progress': ['pending_approval', 'rejected'],
            'reopened': ['in_progress', 'pending_approval', 'rejected'],  # ✅ YANGI!
        }
        
        current_status = ticket.status
        if new_status in valid_transitions.get(current_status, []):
            old_status_display = ticket.get_status_display()
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
                    old_status_display,
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
    """Admin dashboard - TIZIM VA VILOYAT BO'YICHA FILTRLANGAN"""
    
    # Vaqt davri
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # ✅ Admin context
    from accounts.utils import get_admin_context, filter_tickets_for_admin
    admin_ctx = get_admin_context(request.user)
    
    # ✅ Faqat ruxsat berilgan ticketlar
    tickets = Ticket.objects.all()
    tickets = filter_tickets_for_admin(tickets, request.user)
    
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
    
    # ✅ Filter form
    filter_form = TicketFilterForm(request.GET)
    
    # ✅ Filter formani cheklash (admin uchun)
    if admin_ctx:
        # Tizimlarni cheklash
        if admin_ctx['allowed_systems'] is not None:
            filter_form.fields['system'].queryset = admin_ctx['allowed_systems']
        
        # Viloyatlarni cheklash
        if admin_ctx['allowed_regions'] is not None and admin_ctx['allowed_regions'] != []:
            from accounts.models import Region
            filter_form.fields['region'].queryset = Region.objects.filter(
                id__in=admin_ctx['allowed_regions']
            )
    
    # ✅ Filtrlash
    filtered_tickets = tickets
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('system'):
            filtered_tickets = filtered_tickets.filter(system=filter_form.cleaned_data['system'])
        
        # ✅ Region filter
        if filter_form.cleaned_data.get('region'):
            filtered_tickets = filtered_tickets.filter(region=filter_form.cleaned_data['region'])
        
        if filter_form.cleaned_data.get('status'):
            filtered_tickets = filtered_tickets.filter(status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data.get('priority'):
            filtered_tickets = filtered_tickets.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data.get('assigned_to'):
            filtered_tickets = filtered_tickets.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        
        if filter_form.cleaned_data.get('date_from'):
            filtered_tickets = filtered_tickets.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            filtered_tickets = filtered_tickets.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    # ✅ Pagination (optional)
    filtered_tickets = filtered_tickets.order_by('-created_at')[:100]
    
    # ✅ All regions for template
    from accounts.models import Region
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    context = {
        'stats': stats,
        'by_system': by_system,
        'by_region': by_region,
        'technician_stats': technician_stats,
        'tickets': filtered_tickets,
        'filter_form': filter_form,
        'admin_context': admin_ctx,
        'all_regions': all_regions,  # ✅ Template uchun
    }
    
    return render(request, 'tickets/admin_dashboard.html', context)

@login_required
@require_admin
def assign_ticket(request, pk):
    """Ticketni texnikga biriktirish - RUXSAT TEKSHIRISH"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # ✅ YANGI: Admin ruxsat tekshirish
    from accounts.utils import can_admin_see_ticket
    
    if request.user.is_admin() and not can_admin_see_ticket(request.user, ticket):
        messages.error(request, _('Sizda bu murojaatni o\'zgartirish huquqi yo\'q.'))
        return redirect('tickets:admin_dashboard')
    
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
            
            # Notification
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