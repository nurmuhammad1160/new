# accounts/context_processors.py - TO'G'RILASH

from tickets.models import Ticket
from systems.models import SystemResponsible

def new_tickets_count(request):
    """Texnik uchun yangi murojaatlar sonini qaytarish - TO'G'RILANGAN"""
    
    if not request.user.is_authenticated:
        return {'new_tickets_count': 0}
    
    if not request.user.is_technician():
        return {'new_tickets_count': 0}
    
    # Yangi murojaatlar soni
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
    
    # ✅ YANGI: Default texnik ekanligini tekshirish
    is_default_tech = SystemResponsible.objects.filter(
        user=request.user,
        role_in_system='technician',
        is_default=True
    ).exists()
    
    # ✅ YANGI: Mas'ul bo'lgan viloyatlarni tekshirish
    if not is_default_tech:
        responsibilities = SystemResponsible.objects.filter(
            user=request.user,
            role_in_system='technician',
            region__isnull=False
        )
        
        responsible_region_ids = list(responsibilities.values_list('region_id', flat=True).distinct())
        
        if responsible_region_ids:
            new_tickets_query = new_tickets_query.filter(region_id__in=responsible_region_ids)
    
    count = new_tickets_query.count()
    
    return {'new_tickets_count': count}