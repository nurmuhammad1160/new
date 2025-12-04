from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Region, Department


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'is_active']
    list_filter = ['region', 'is_active']
    search_fields = ['name']
    ordering = ['region', 'name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 
        'get_full_name', 
        'role', 
        'region', 
        'department', 
        'is_active'
    ]
    list_filter = ['role', 'region', 'is_active', 'date_joined']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        (_('Shaxsiy ma\'lumotlar'), {
            'fields': ('last_name', 'first_name', 'middle_name', 'avatar')
        }),
        (_('Tashkiliy ma\'lumotlar'), {
            'fields': ('region', 'department', 'position', 'phone')
        }),
        (_('Tizim sozlamalari'), {
            'fields': ('role', 'language', 'email')
        }),
        (_('Ruxsatlar'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Muhim sanalar'), {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 
                'password1', 
                'password2', 
                'first_name', 
                'last_name',
                'role',
                'region'
            ),
        }),
    )