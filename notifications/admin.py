from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'notification_type',
        'title',
        'get_read_status',
        'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'title', 'text']
    autocomplete_fields = ['user']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Qabul qiluvchi'), {
            'fields': ('user',)
        }),
        (_('Bildirishnoma tafsilotlari'), {
            'fields': ('notification_type', 'title', 'text', 'url')
        }),
        (_('Holat'), {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    def get_read_status(self, obj):
        """O'qilgan/o'qilmagan holat"""
        if obj.is_read:
            return format_html(
                '<span style="color: #198754;">✓ O\'qilgan</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">● Yangi</span>'
            )
    get_read_status.short_description = _('Holat')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Tanlangan bildirishnomalarni o'qilgan deb belgilash"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} ta bildirishnoma o\'qilgan deb belgilandi.')
    mark_as_read.short_description = _('O\'qilgan deb belgilash')
    
    def mark_as_unread(self, request, queryset):
        """Tanlangan bildirishnomalarni o'qilmagan deb belgilash"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} ta bildirishnoma o\'qilmagan deb belgilandi.')
    mark_as_unread.short_description = _('O\'qilmagan deb belgilash')