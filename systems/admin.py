from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import System, SystemResponsible


class SystemResponsibleInline(admin.TabularInline):
    model = SystemResponsible
    extra = 1
    fields = ['user', 'role_in_system', 'region', 'is_default']
    autocomplete_fields = ['user', 'region']


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    inlines = [SystemResponsibleInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
    )


@admin.register(SystemResponsible)
class SystemResponsibleAdmin(admin.ModelAdmin):
    list_display = [
        'system', 
        'user', 
        'role_in_system', 
        'region', 
        'is_default',
        'created_at'
    ]
    list_filter = ['role_in_system', 'is_default', 'system', 'region']
    search_fields = ['system__name', 'user__first_name', 'user__last_name']
    autocomplete_fields = ['system', 'user', 'region']
    ordering = ['system', 'region']
    
    fieldsets = (
        (_('Asosiy ma\'lumotlar'), {
            'fields': ('system', 'user', 'role_in_system')
        }),
        (_('Hudud'), {
            'fields': ('region', 'is_default'),
            'description': _('Region bo\'sh va is_default=True bo\'lsa - respublika mas\'uli')
        }),
    )