from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Avg
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import random
import string

from accounts.models import User, Region, Department
from .models import Ticket, TicketHistory, TicketMessage
from systems.models import System, SystemResponsible
from notifications.models import Notification


# ============================================
# DECORATORS
# ============================================

def require_superadmin(view_func):
    """Bosh admin bo'lishini talab qiluvchi decorator"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superadmin():
            messages.error(request, _('Sizda bu sahifaga kirish huquqi yo\'q. Faqat bosh adminlar kirishi mumkin.'))
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# SUPERADMIN DASHBOARD
# ============================================

@login_required
@require_superadmin
def superadmin_dashboard(request):
    """Bosh admin - to'liq nazorat paneli"""
    
    # Vaqt davri
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # UMUMIY STATISTIKA
    total_users = User.objects.count()
    total_tickets = Ticket.objects.count()
    total_systems = System.objects.count()
    
    # ROLLAR BO'YICHA FOYDALANUVCHILAR
    users_by_role = User.objects.values('role').annotate(count=Count('id'))
    role_stats = {
        'superadmin': 0,
        'admin': 0,
        'technician': 0,
        'user': 0,
    }
    for item in users_by_role:
        role_stats[item['role']] = item['count']
    
    # FAOL/BLOKLANGAN FOYDALANUVCHILAR
    active_users = User.objects.filter(is_active=True).count()
    blocked_users = User.objects.filter(is_active=False).count()
    
    # TICKET STATISTIKA
    tickets_today = Ticket.objects.filter(created_at__date=today).count()
    tickets_week = Ticket.objects.filter(created_at__date__gte=week_ago).count()
    tickets_month = Ticket.objects.filter(created_at__date__gte=month_ago).count()
    
    # HOLAT BO'YICHA
    tickets_by_status = Ticket.objects.values('status').annotate(count=Count('id'))
    status_stats = {}
    for item in tickets_by_status:
        status_stats[item['status']] = item['count']
    
    # O'RTACHA BAHOLASH
    avg_rating = Ticket.objects.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0
    
    # ENG FAOL TEXNIKLAR (ko'p ticket hal qilganlar)
    top_technicians = Ticket.objects.filter(
        assigned_to__isnull=False,
        status='resolved'
    ).values(
        'assigned_to__first_name',
        'assigned_to__last_name',
        'assigned_to__id'
    ).annotate(
        resolved_count=Count('id'),
        avg_rating=Avg('rating')
    ).order_by('-resolved_count')[:10]
    
    # ENG KO'P MUROJAAT KELGAN TIZIMLAR
    top_systems = Ticket.objects.values(
        'system__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # VILOYATLAR BO'YICHA
    tickets_by_region = Ticket.objects.values(
        'region__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:14]
    
    # OXIRGI FAOLLIK
    recent_users = User.objects.order_by('-last_login')[:10]
    recent_tickets = Ticket.objects.order_by('-created_at')[:10]
    
    # TIZIM SOGLIGI (System Health)
    unassigned_tickets = Ticket.objects.filter(assigned_to__isnull=True).count()
    pending_ratings = Ticket.objects.filter(status='pending_approval').count()
    reopened_tickets = Ticket.objects.filter(status='reopened').count()
    
    context = {
        # Umumiy
        'total_users': total_users,
        'total_tickets': total_tickets,
        'total_systems': total_systems,
        
        # Foydalanuvchilar
        'role_stats': role_stats,
        'active_users': active_users,
        'blocked_users': blocked_users,
        
        # Ticketlar
        'tickets_today': tickets_today,
        'tickets_week': tickets_week,
        'tickets_month': tickets_month,
        'status_stats': status_stats,
        'avg_rating': round(avg_rating, 2),
        
        # Top lists
        'top_technicians': top_technicians,
        'top_systems': top_systems,
        'tickets_by_region': tickets_by_region,
        
        # Recent activity
        'recent_users': recent_users,
        'recent_tickets': recent_tickets,
        
        # System health
        'unassigned_tickets': unassigned_tickets,
        'pending_ratings': pending_ratings,
        'reopened_tickets': reopened_tickets,
    }
    
    return render(request, 'tickets/superadmin/dashboard.html', context)


# ============================================
# USER MANAGEMENT (SUPERADMIN)
# ============================================

@login_required
@require_superadmin
def superadmin_users_list(request):
    """Barcha foydalanuvchilar ro'yxati (bosh admin uchun)"""
    users = User.objects.all().select_related('region').order_by('-date_joined')
    
    # Filter by role
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    # Filter by region
    region_id = request.GET.get('region')
    if region_id:
        users = users.filter(region_id=region_id)
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'blocked':
        users = users.filter(is_active=False)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(middle_name__icontains=search)
        )
    
    # Har bir user uchun statistika
    users_data = []
    for user in users[:100]:  # Pagination kerak bo'lsa
        tickets_created = Ticket.objects.filter(user=user).count()
        tickets_assigned = Ticket.objects.filter(assigned_to=user).count()
        avg_rating = Ticket.objects.filter(
            assigned_to=user,
            rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg'] or 0
        
        users_data.append({
            'user': user,
            'tickets_created': tickets_created,
            'tickets_assigned': tickets_assigned,
            'avg_rating': round(avg_rating, 2),
        })
    
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    context = {
        'users_data': users_data,
        'all_regions': all_regions,
        'search': search,
        'role': role,
        'region_id': region_id,
        'status': status,
    }
    
    return render(request, 'tickets/superadmin/users_list.html', context)


@login_required
@require_superadmin
def superadmin_user_detail(request, user_id):
    """Foydalanuvchi to'liq ma'lumotlari"""
    user = get_object_or_404(User, pk=user_id)
    
    # Statistika
    tickets_created = Ticket.objects.filter(user=user)
    tickets_assigned = Ticket.objects.filter(assigned_to=user)
    
    stats = {
        'tickets_created_total': tickets_created.count(),
        'tickets_created_resolved': tickets_created.filter(status='resolved').count(),
        'tickets_assigned_total': tickets_assigned.count(),
        'tickets_assigned_resolved': tickets_assigned.filter(status='resolved').count(),
        'avg_rating': tickets_assigned.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    # Oxirgi faoliyat
    recent_tickets = tickets_created.order_by('-created_at')[:10]
    recent_messages = TicketMessage.objects.filter(sender=user).order_by('-created_at')[:10]
    
    # Mas'ul bo'lgan tizimlar
    responsible_systems = SystemResponsible.objects.filter(user=user).select_related('system', 'region')
    
    context = {
        'user_obj': user,
        'stats': stats,
        'recent_tickets': recent_tickets,
        'recent_messages': recent_messages,
        'responsible_systems': responsible_systems,
    }
    
    return render(request, 'tickets/superadmin/user_detail.html', context)


@login_required
@require_superadmin
def superadmin_change_role(request, user_id):
    """Foydalanuvchi rolini o'zgartirish (faqat bosh admin)"""
    user = get_object_or_404(User, pk=user_id)
    
    # O'zini o'zgartirmaslik uchun
    if user == request.user:
        messages.error(request, _('O\'z rolingizni o\'zgartira olmaysiz!'))
        return redirect('tickets:superadmin_users_list')
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        
        if new_role in ['user', 'technician', 'admin', 'superadmin']:
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
            
            # Notification userga
            Notification.objects.create(
                user=user,
                notification_type='status_changed',
                title=_('Sizning rolingiz o\'zgartirildi'),
                text=_('Yangi rol: {}').format(user.get_role_display()),
                url='/accounts/profile/'
            )
        else:
            messages.error(request, _('Noto\'g\'ri rol tanlandi.'))
    
    return redirect('tickets:superadmin_user_detail', user_id=user_id)


@login_required
@require_superadmin
def superadmin_toggle_user_status(request, user_id):
    """Foydalanuvchini bloklash/aktivlashtirish"""
    user = get_object_or_404(User, pk=user_id)
    
    # O'zini bloklamaslik
    if user == request.user:
        messages.error(request, _('O\'zingizni bloklay olmaysiz!'))
        return redirect('tickets:superadmin_users_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status_text = _('aktivlashtirildi') if user.is_active else _('bloklandi')
    messages.success(
        request,
        _('Foydalanuvchi {}: {}').format(status_text, user.get_full_name())
    )
    
    return redirect('tickets:superadmin_user_detail', user_id=user_id)


# ============================================
# PASSWORD MANAGEMENT (FAQAT BOSH ADMIN!)
# ============================================

@login_required
@require_superadmin
def superadmin_reset_password(request, user_id):
    """Foydalanuvchi parolini o'zgartirish (faqat bosh admin) - FIXED"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # ✅ TO'G'RI FIELD NOMLARI
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validation
        if not new_password1 or len(new_password1) < 6:
            messages.error(request, _('Parol kamida 6 belgidan iborat bo\'lishi kerak.'))
            return render(request, 'tickets/superadmin/reset_password.html', {'user_obj': user})
        
        if new_password1 != new_password2:
            messages.error(request, _('Parollar bir xil emas.'))
            return render(request, 'tickets/superadmin/reset_password.html', {'user_obj': user})
        
        # ✅ Parolni o'rnatish (to'g'ri usul)
        user.set_password(new_password1)
        user.save()
        
        messages.success(
            request,
            _('Foydalanuvchi {} uchun yangi parol o\'rnatildi. Endi {} parol bilan kirishi mumkin.').format(
                user.get_full_name(),
                new_password1  # Debug uchun (production da olib tashlash kerak!)
            )
        )
        
        # Notification userga
        Notification.objects.create(
            user=user,
            notification_type='status_changed',
            title=_('Parolingiz o\'zgartirildi'),
            text=_('Bosh admin tomonidan parolingiz o\'zgartirildi. Yangi parol bilan tizimga kiring.'),
            url='/accounts/login/'
        )
        
        return redirect('tickets:superadmin_user_detail', user_id=user_id)
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'tickets/superadmin/reset_password.html', context)


@login_required
@require_superadmin
def superadmin_generate_temp_password(request, user_id):
    """Vaqtinchalik parol generatsiya qilish"""
    user = get_object_or_404(User, pk=user_id)
    
    # Random parol (8 belgili)
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    user.set_password(temp_password)
    user.save()
    
    messages.success(
        request,
        _('Vaqtinchalik parol yaratildi: {} (Foydalanuvchiga yuboring!)').format(temp_password)
    )
    
    return redirect('tickets:superadmin_user_detail', user_id=user_id)


# ============================================
# USER CREATION (FAQAT BOSH ADMIN)
# ============================================

@login_required
@require_superadmin
def superadmin_create_user(request):
    """Yangi foydalanuvchi yaratish (bosh admin)"""
    from accounts.forms import UserRegistrationForm
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Role'ni formdan olish
            role = request.POST.get('role', 'user')
            if role in ['user', 'technician', 'admin', 'superadmin']:
                user.role = role
            
            user.save()
            
            messages.success(
                request,
                _('Yangi foydalanuvchi yaratildi: {} (Rol: {})').format(
                    user.get_full_name(),
                    user.get_role_display()
                )
            )
            
            return redirect('tickets:superadmin_user_detail', user_id=user.id)
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'tickets/superadmin/create_user.html', context)


@login_required
@require_superadmin
def superadmin_delete_user(request, user_id):
    """Foydalanuvchini o'chirish (EHTIYOTKORLIK!)"""
    user = get_object_or_404(User, pk=user_id)
    
    # O'zini o'chirmaslik
    if user == request.user:
        messages.error(request, _('O\'zingizni o\'chira olmaysiz!'))
        return redirect('tickets:superadmin_users_list')
    
    if request.method == 'POST':
        username = user.get_full_name()
        
        # Ticketlar bormi tekshirish
        tickets_count = Ticket.objects.filter(user=user).count()
        assigned_count = Ticket.objects.filter(assigned_to=user).count()
        
        if tickets_count > 0 or assigned_count > 0:
            messages.error(
                request,
                _('Bu foydalanuvchi bilan bog\'liq {} ta murojaat mavjud. Avval ularni hal qiling.').format(
                    tickets_count + assigned_count
                )
            )
            return redirect('tickets:superadmin_user_detail', user_id=user_id)
        
        user.delete()
        messages.success(request, _('Foydalanuvchi o\'chirildi: {}').format(username))
        return redirect('tickets:superadmin_users_list')
    
    context = {
        'user_obj': user,
        'tickets_count': Ticket.objects.filter(user=user).count(),
        'assigned_count': Ticket.objects.filter(assigned_to=user).count(),
    }
    
    return render(request, 'tickets/superadmin/confirm_delete_user.html', context)


# ============================================
# SYSTEM SETTINGS (GLOBAL)
# ============================================

@login_required
@require_superadmin
def superadmin_system_settings(request):
    """Tizim sozlamalari (global)"""
    
    # Default responsibles
    default_responsibles = SystemResponsible.objects.filter(
        is_default=True,
        region__isnull=True
    ).select_related('system', 'user')
    
    # Barcha tizimlar
    all_systems = System.objects.filter(is_active=True)
    
    # Har bir tizim uchun default mas'ullar
    systems_data = []
    for system in all_systems:
        default_admin = default_responsibles.filter(
            system=system,
            role_in_system='admin'
        ).first()
        
        default_techs = default_responsibles.filter(
            system=system,
            role_in_system='technician'
        )
        
        systems_data.append({
            'system': system,
            'default_admin': default_admin,
            'default_techs': default_techs,
        })
    
    context = {
        'systems_data': systems_data,
    }
    
    return render(request, 'tickets/superadmin/system_settings.html', context)


# ============================================
# AUDIT LOGS
# ============================================

@login_required
@require_superadmin
def superadmin_audit_logs(request):
    """Barcha audit loglar"""
    logs = TicketHistory.objects.select_related(
        'ticket', 'changed_by'
    ).order_by('-timestamp')
    
    # Filter by action type
    action_type = request.GET.get('action_type')
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    # Filter by user
    user_id = request.GET.get('user_id')
    selected_user_name = ''
    if user_id:
        try:
            user_obj = User.objects.get(pk=user_id)
            selected_user_name = user_obj.get_full_name()
            logs = logs.filter(changed_by_id=user_id)
        except User.DoesNotExist:
            pass
    
    # Apply slice at the end
    logs = logs[:200]
    
    context = {
        'logs': logs,
        'action_type': action_type,
        'user_id': user_id,
        'selected_user_name': selected_user_name,  # ✅ QO'SHILDI
    }
    
    return render(request, 'tickets/superadmin/audit_logs.html', context)


# ============================================
# AJAX ENDPOINTS
# ============================================

@login_required
@require_superadmin
def superadmin_users_search_ajax(request):
    """AJAX - foydalanuvchilarni qidirish"""
    search = request.GET.get('q', '')
    
    users = User.objects.filter(
        Q(first_name__icontains=search) |
        Q(last_name__icontains=search) |
        Q(username__icontains=search)
    )[:20]
    
    results = []
    for user in users:
        results.append({
            'id': user.id,
            'full_name': user.get_full_name(),
            'username': user.username,
            'role': user.get_role_display(),
            'is_active': user.is_active,
        })
    
    return JsonResponse({
        'success': True,
        'results': results
    })



@login_required
@require_superadmin
def api_users_search(request):
    """AJAX - foydalanuvchilarni qidirish (audit logs uchun)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Kamida 2 ta belgi kiriting'
        })
    
    # Qidiruv
    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(middle_name__icontains=query) |
        Q(username__icontains=query)
    ).order_by('first_name', 'last_name')[:20]
    
    results = []
    for user in users:
        results.append({
            'id': user.id,
            'full_name': user.get_full_name(),
            'username': user.username,
            'role': user.get_role_display(),
            'is_active': user.is_active,
        })
    
    return JsonResponse({
        'success': True,
        'results': results
    })


# tickets/views_superadmin.py ga qo'shish uchun

@login_required
@require_superadmin
def superadmin_departments_list(request):
    """Barcha bo'limlar ro'yxati"""
    departments = Department.objects.all().select_related('region').order_by('region__name', 'name')
    
    # Filter by region
    region_id = request.GET.get('region')
    if region_id:
        departments = departments.filter(region_id=region_id)
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        departments = departments.filter(is_active=True)
    elif status == 'inactive':
        departments = departments.filter(is_active=False)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        departments = departments.filter(name__icontains=search)
    
    # Har bir bo'lim uchun statistika
    departments_data = []
    for dept in departments:
        users_count = User.objects.filter(department=dept).count()
        tickets_count = Ticket.objects.filter(region=dept.region).count()
        
        departments_data.append({
            'department': dept,
            'users_count': users_count,
            'tickets_count': tickets_count,
        })
    
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    context = {
        'departments_data': departments_data,
        'all_regions': all_regions,
        'search': search,
        'region_id': region_id,
        'status': status,
    }
    
    return render(request, 'tickets/superadmin/departments_list.html', context)


@login_required
@require_superadmin
def superadmin_department_create(request):
    """Yangi bo'lim yaratish"""
    if request.method == 'POST':
        name = request.POST.get('name')
        region_id = request.POST.get('region')
        is_active = request.POST.get('is_active') == 'on'
        
        if not name or not region_id:
            messages.error(request, _('Barcha majburiy maydonlarni to\'ldiring.'))
            return redirect('tickets:superadmin_department_create')
        
        try:
            region = Region.objects.get(pk=region_id)
            department = Department.objects.create(
                name=name,
                region=region,
                is_active=is_active
            )
            
            messages.success(
                request,
                _('Yangi bo\'lim yaratildi: {} - {}').format(region.name, name)
            )
            
            return redirect('tickets:superadmin_departments_list')
        except Region.DoesNotExist:
            messages.error(request, _('Viloyat topilmadi.'))
        except Exception as e:
            messages.error(request, _('Xatolik: {}').format(str(e)))
    
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    context = {
        'all_regions': all_regions,
    }
    
    return render(request, 'tickets/superadmin/department_create.html', context)


@login_required
@require_superadmin
def superadmin_department_edit(request, dept_id):
    """Bo'limni tahrirlash"""
    department = get_object_or_404(Department, pk=dept_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        region_id = request.POST.get('region')
        is_active = request.POST.get('is_active') == 'on'
        
        if not name or not region_id:
            messages.error(request, _('Barcha majburiy maydonlarni to\'ldiring.'))
            return redirect('tickets:superadmin_department_edit', dept_id=dept_id)
        
        try:
            region = Region.objects.get(pk=region_id)
            department.name = name
            department.region = region
            department.is_active = is_active
            department.save()
            
            messages.success(
                request,
                _('Bo\'lim ma\'lumotlari saqlandi: {} - {}').format(region.name, name)
            )
            
            return redirect('tickets:superadmin_departments_list')
        except Region.DoesNotExist:
            messages.error(request, _('Viloyat topilmadi.'))
        except Exception as e:
            messages.error(request, _('Xatolik: {}').format(str(e)))
    
    all_regions = Region.objects.filter(is_active=True).order_by('name')
    
    # Statistika
    users_count = User.objects.filter(department=department).count()
    users_list = User.objects.filter(department=department)[:10]
    
    context = {
        'department': department,
        'all_regions': all_regions,
        'users_count': users_count,
        'users_list': users_list,
    }
    
    return render(request, 'tickets/superadmin/department_edit.html', context)


@login_required
@require_superadmin
def superadmin_department_toggle_status(request, dept_id):
    """Bo'limni aktivlashtirish/o'chirish"""
    department = get_object_or_404(Department, pk=dept_id)
    
    department.is_active = not department.is_active
    department.save()
    
    status_text = _('aktivlashtirildi') if department.is_active else _('o\'chirildi')
    messages.success(
        request,
        _('Bo\'lim {}: {} - {}').format(status_text, department.region.name, department.name)
    )
    
    return redirect('tickets:superadmin_departments_list')


@login_required
@require_superadmin
def superadmin_department_delete(request, dept_id):
    """Bo'limni o'chirish"""
    department = get_object_or_404(Department, pk=dept_id)
    
    # Foydalanuvchilar bormi tekshirish
    users_count = User.objects.filter(department=department).count()
    
    if users_count > 0:
        messages.error(
            request,
            _('Bu bo\'limda {} ta foydalanuvchi mavjud. Avval ularni boshqa bo\'limga o\'tkazing.').format(users_count)
        )
        return redirect('tickets:superadmin_department_edit', dept_id=dept_id)
    
    if request.method == 'POST':
        dept_name = f"{department.region.name} - {department.name}"
        department.delete()
        
        messages.success(request, _('Bo\'lim o\'chirildi: {}').format(dept_name))
        return redirect('tickets:superadmin_departments_list')
    
    context = {
        'department': department,
        'users_count': users_count,
    }
    
    return render(request, 'tickets/superadmin/department_delete_confirm.html', context)


# tickets/urls.py ga qo'shish kerak:
# path('superadmin/departments/', views_superadmin.superadmin_departments_list, name='superadmin_departments_list'),
# path('superadmin/departments/create/', views_superadmin.superadmin_department_create, name='superadmin_department_create'),
# path('superadmin/departments/<int:dept_id>/edit/', views_superadmin.superadmin_department_edit, name='superadmin_department_edit'),
# path('superadmin/departments/<int:dept_id>/toggle/', views_superadmin.superadmin_department_toggle_status, name='superadmin_department_toggle_status'),
# path('superadmin/departments/<int:dept_id>/delete/', views_superadmin.superadmin_department_delete, name='superadmin_department_delete'),