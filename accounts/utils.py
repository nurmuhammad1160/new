# accounts/utils.py - ADMIN PERMISSIONS

from systems.models import SystemResponsible


def get_admin_systems(user):
    """
    Adminning biriktirilgan tizimlarini olish
    
    Returns:
        - QuerySet of Systems (agar admin bo'lsa)
        - None (agar superadmin bo'lsa - cheklovsiz)
    """
    if user.is_superadmin():
        return None  # Hamma narsa ko'rinadi
    
    if user.is_admin():
        # Admin uchun biriktirilgan tizimlar
        system_ids = SystemResponsible.objects.filter(
            user=user,
            role_in_system='admin'
        ).values_list('system_id', flat=True)
        
        from systems.models import System
        return System.objects.filter(id__in=system_ids, is_active=True)
    
    return None


def get_admin_regions(user):
    """
    Adminning biriktirilgan viloyatlarini olish
    
    Returns:
        - [] (empty list) - Respublika admin (barcha viloyatlar)
        - [region_ids] - Viloyat admin (faqat o'z viloyati)
        - None - SuperAdmin (cheklovsiz)
    """
    if user.is_superadmin():
        return None  # Hamma narsa ko'rinadi
    
    if user.is_admin():
        # Respublika adminmi yoki viloyat adminmi?
        responsibles = SystemResponsible.objects.filter(
            user=user,
            role_in_system='admin'
        )
        
        # Agar birorta ham region=NULL bo'lsa -> Respublika admin
        if responsibles.filter(region__isnull=True).exists():
            return []  # Bo'sh list = barcha viloyatlar
        
        # Aks holda viloyat admin -> faqat biriktirilgan viloyatlar
        region_ids = responsibles.filter(
            region__isnull=False
        ).values_list('region_id', flat=True).distinct()
        
        return list(region_ids)
    
    return None


def can_admin_see_ticket(user, ticket):
    """
    Admin bu ticketni ko'ra oladimi?
    
    Args:
        user: User object
        ticket: Ticket object
    
    Returns:
        bool: True/False
    """
    if user.is_superadmin():
        return True  # SuperAdmin hamma narsani ko'radi
    
    if not user.is_admin():
        return False  # Faqat admin va superadmin
    
    # Admin uchun tekshirish
    allowed_systems = get_admin_systems(user)
    if allowed_systems is None:
        return True  # SuperAdmin
    
    # Tizim tekshirish
    if ticket.system not in allowed_systems:
        return False
    
    # Viloyat tekshirish
    allowed_regions = get_admin_regions(user)
    if allowed_regions is None:
        return True  # SuperAdmin
    
    if allowed_regions == []:
        return True  # Respublika admin (barcha viloyatlar)
    
    # Viloyat admin - faqat o'z viloyati
    if ticket.region_id in allowed_regions:
        return True
    
    return False


def filter_tickets_for_admin(queryset, user):
    """
    Admin uchun ticketlarni filtrlash
    
    Args:
        queryset: Ticket.objects.all() yoki boshqa queryset
        user: User object
    
    Returns:
        Filtered queryset
    """
    if user.is_superadmin():
        return queryset  # Hamma narsa
    
    if not user.is_admin():
        return queryset.none()  # Bo'sh
    
    # Admin uchun tizimlar
    allowed_systems = get_admin_systems(user)
    if allowed_systems is not None:
        queryset = queryset.filter(system__in=allowed_systems)
    
    # Admin uchun viloyatlar
    allowed_regions = get_admin_regions(user)
    if allowed_regions is not None and allowed_regions != []:
        queryset = queryset.filter(region_id__in=allowed_regions)
    
    return queryset


def get_admin_context(user):
    """
    Admin dashboard uchun context ma'lumotlari
    
    Returns:
        dict: {
            'is_respublika_admin': bool,
            'is_viloyat_admin': bool,
            'allowed_systems': QuerySet or None,
            'allowed_regions': list or None,
        }
    """
    if user.is_superadmin():
        return {
            'is_respublika_admin': True,
            'is_viloyat_admin': False,
            'allowed_systems': None,
            'allowed_regions': None,
        }
    
    if not user.is_admin():
        return None
    
    allowed_systems = get_admin_systems(user)
    allowed_regions = get_admin_regions(user)
    
    is_respublika = (allowed_regions == [])
    is_viloyat = (allowed_regions is not None and allowed_regions != [])
    
    return {
        'is_respublika_admin': is_respublika,
        'is_viloyat_admin': is_viloyat,
        'allowed_systems': allowed_systems,
        'allowed_regions': allowed_regions,
    }