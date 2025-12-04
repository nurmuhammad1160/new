from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django import forms
from .models import System, SystemResponsible
from .forms import SystemForm, SystemResponsibleForm
from accounts.models import User, Region


# ============================================
# DECORATORS
# ============================================

def require_admin(view_func):
    """Admin bo'lishini talab qiluvchi decorator"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin():
            messages.error(request, _('Sizda bu sahifaga kirish huquqi yo\'q.'))
            return redirect('tickets:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================
# SYSTEMS MANAGEMENT
# ============================================

@login_required
@require_admin
def systems_list(request):
    """Tizimlar ro'yxati"""
    systems = System.objects.all().order_by('name')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        systems = systems.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # Filter by status
    status = request.GET.get('status', '')
    if status == 'active':
        systems = systems.filter(is_active=True)
    elif status == 'inactive':
        systems = systems.filter(is_active=False)
    
    # Har bir tizim uchun statistika
    systems_data = []
    for system in systems:
        tickets_count = system.tickets.count()
        responsibles_count = system.responsibles.count()
        systems_data.append({
            'system': system,
            'tickets_count': tickets_count,
            'responsibles_count': responsibles_count,
        })
    
    context = {
        'systems_data': systems_data,
        'search': search,
        'status': status,
    }
    
    return render(request, 'systems/systems_list.html', context)


@login_required
@require_admin
def system_create(request):
    """Yangi tizim yaratish"""
    if request.method == 'POST':
        form = SystemForm(request.POST)
        if form.is_valid():
            system = form.save()
            messages.success(request, _('Tizim muvaffaqiyatli yaratildi: {}').format(system.name))
            return redirect('systems:systems_list')
    else:
        form = SystemForm()
    
    context = {
        'form': form,
        'action': 'create',
    }
    
    return render(request, 'systems/system_form.html', context)


@login_required
@require_admin
def system_edit(request, pk):
    """Tizimni tahrirlash"""
    system = get_object_or_404(System, pk=pk)
    
    if request.method == 'POST':
        form = SystemForm(request.POST, instance=system)
        if form.is_valid():
            system = form.save()
            messages.success(request, _('Tizim muvaffaqiyatli yangilandi: {}').format(system.name))
            return redirect('systems:systems_list')
    else:
        form = SystemForm(instance=system)
    
    context = {
        'form': form,
        'system': system,
        'action': 'edit',
    }
    
    return render(request, 'systems/system_form.html', context)


@login_required
@require_admin
def system_delete(request, pk):
    """Tizimni o'chirish"""
    system = get_object_or_404(System, pk=pk)
    
    if request.method == 'POST':
        system_name = system.name
        
        # Tizimga tegishli ticketlar bormi tekshirish
        tickets_count = system.tickets.count()
        if tickets_count > 0:
            messages.error(
                request, 
                _('Bu tizimda {} ta murojaat mavjud. Avval ularni o\'chiring yoki boshqa tizimga o\'tkazing.').format(tickets_count)
            )
            return redirect('systems:systems_list')
        
        system.delete()
        messages.success(request, _('Tizim o\'chirildi: {}').format(system_name))
        return redirect('systems:systems_list')
    
    context = {
        'system': system,
        'tickets_count': system.tickets.count(),
    }
    
    return render(request, 'systems/system_confirm_delete.html', context)


@login_required
@require_admin
def system_toggle_status(request, pk):
    """Tizim statusini o'zgartirish (active/inactive)"""
    system = get_object_or_404(System, pk=pk)
    
    system.is_active = not system.is_active
    system.save()
    
    status_text = _('faollashtirildi') if system.is_active else _('nofaollashtirildi')
    messages.success(request, _('Tizim {}: {}').format(status_text, system.name))
    
    return redirect('systems:systems_list')


# ============================================
# SYSTEM RESPONSIBLES MANAGEMENT
# ============================================

@login_required
@require_admin
def system_responsibles(request, system_id):
    """Tizim mas'ullari ro'yxati"""
    system = get_object_or_404(System, pk=system_id)
    
    # Viloyatlar bo'yicha guruhlash
    responsibles = SystemResponsible.objects.filter(system=system).select_related(
        'user', 'region'
    ).order_by('region__name', 'role_in_system')
    
    # Default (respublika) mas'ullar
    default_responsibles = responsibles.filter(is_default=True, region__isnull=True)
    
    # Viloyat mas'ullari
    regional_responsibles = responsibles.filter(region__isnull=False)
    
    # Viloyatlar bo'yicha guruhlash
    regions_data = {}
    for resp in regional_responsibles:
        region_name = resp.region.name if resp.region else _('Respublika')
        if region_name not in regions_data:
            regions_data[region_name] = {
                'admins': [],
                'technicians': [],
            }
        
        if resp.role_in_system == 'admin':
            regions_data[region_name]['admins'].append(resp)
        else:
            regions_data[region_name]['technicians'].append(resp)
    
    context = {
        'system': system,
        'default_responsibles': default_responsibles,
        'regions_data': regions_data,
    }
    
    return render(request, 'systems/system_responsibles.html', context)


@login_required
@require_admin
def responsible_create(request, system_id):
    """Yangi mas'ul qo'shish"""
    system = get_object_or_404(System, pk=system_id)
    
    if request.method == 'POST':
        form = SystemResponsibleForm(request.POST)
        if form.is_valid():
            responsible = form.save(commit=False)
            responsible.system = system
            
            # Validation: region va is_default bir vaqtda bo'lishi mumkin emas
            if responsible.region and responsible.is_default:
                messages.error(request, _('Viloyat mas\'uli "default" bo\'lishi mumkin emas.'))
                return redirect('systems:responsible_create', system_id=system_id)
            
            responsible.save()
            messages.success(
                request, 
                _('Mas\'ul qo\'shildi: {} - {}').format(
                    responsible.user.get_full_name(),
                    responsible.get_role_in_system_display()
                )
            )
            return redirect('systems:system_responsibles', system_id=system_id)
    else:
        form = SystemResponsibleForm()
        form.fields['system'].initial = system
        form.fields['system'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'system': system,
        'action': 'create',
    }
    
    return render(request, 'systems/responsible_form.html', context)


@login_required
@require_admin
def responsible_edit(request, pk):
    """Mas'ulni tahrirlash"""
    responsible = get_object_or_404(SystemResponsible, pk=pk)
    system = responsible.system
    
    if request.method == 'POST':
        form = SystemResponsibleForm(request.POST, instance=responsible)
        if form.is_valid():
            responsible = form.save(commit=False)
            
            # Validation
            if responsible.region and responsible.is_default:
                messages.error(request, _('Viloyat mas\'uli "default" bo\'lishi mumkin emas.'))
                return redirect('systems:responsible_edit', pk=pk)
            
            responsible.save()
            messages.success(request, _('Mas\'ul ma\'lumotlari yangilandi.'))
            return redirect('systems:system_responsibles', system_id=system.id)
    else:
        form = SystemResponsibleForm(instance=responsible)
        form.fields['system'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'responsible': responsible,
        'system': system,
        'action': 'edit',
    }
    
    return render(request, 'systems/responsible_form.html', context)


@login_required
@require_admin
def responsible_delete(request, pk):
    """Mas'ulni o'chirish"""
    responsible = get_object_or_404(SystemResponsible, pk=pk)
    system = responsible.system
    
    if request.method == 'POST':
        responsible_name = responsible.user.get_full_name()
        responsible.delete()
        messages.success(request, _('Mas\'ul o\'chirildi: {}').format(responsible_name))
        return redirect('systems:system_responsibles', system_id=system.id)
    
    context = {
        'responsible': responsible,
        'system': system,
    }
    
    return render(request, 'systems/responsible_confirm_delete.html', context)


# ============================================
# QUICK ACTIONS (AJAX)
# ============================================

@login_required
@require_admin
@require_POST
def system_quick_toggle(request, pk):
    """AJAX - tizim statusini tezkor o'zgartirish"""
    system = get_object_or_404(System, pk=pk)
    system.is_active = not system.is_active
    system.save()
    
    return JsonResponse({
        'success': True,
        'is_active': system.is_active,
        'message': _('Status o\'zgartirildi')
    })


@login_required
@require_admin
def systems_search_ajax(request):
    """AJAX - tizimlarni qidirish"""
    search = request.GET.get('q', '')
    
    systems = System.objects.filter(
        Q(name__icontains=search) | 
        Q(description__icontains=search)
    )[:20]
    
    results = []
    for system in systems:
        results.append({
            'id': system.id,
            'name': system.name,
            'description': system.description,
            'is_active': system.is_active,
            'tickets_count': system.tickets.count(),
        })
    
    return JsonResponse({
        'success': True,
        'results': results
    })