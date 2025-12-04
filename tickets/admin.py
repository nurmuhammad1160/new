from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Ticket, TicketMessage, TicketHistory


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    fields = ['sender', 'message', 'attachment', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    fields = ['action_type', 'changed_by', 'old_value', 'new_value', 'message', 'timestamp']
    readonly_fields = ['action_type', 'changed_by', 'old_value', 'new_value', 'message', 'timestamp']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'get_ticket_number',
        'user',
        'system',
        'region',
        'get_status_badge',
        'get_priority_badge',
        'assigned_to',
        'rating',
        'created_at'
    ]
    list_filter = [
        'status',
        'priority',
        'system',
        'region',
        'created_at'
    ]
    search_fields = [
        'user__first_name',
        'user__last_name',
        'description',
        'system__name'
    ]
    autocomplete_fields = ['user', 'system', 'region', 'assigned_to']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    ordering = ['-created_at']
    inlines = [TicketMessageInline, TicketHistoryInline]
    
    fieldsets = (
        (_('Asosiy ma\'lumotlar'), {
            'fields': ('user', 'system', 'region')
        }),
        (_('Murojaat tafsilotlari'), {
            'fields': ('priority', 'status', 'description', 'attachment')
        }),
        (_('Mas\'ul xodim'), {
            'fields': ('assigned_to',)
        }),
        (_('Baholash'), {
            'fields': ('rating', 'rating_comment')
        }),
        (_('Vaqt ma\'lumotlari'), {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_badge(self, obj):
        """Status rangli ko'rinishda"""
        colors = {
            'new': '#ffc107',
            'in_progress': '#0dcaf0',
            'pending_approval': '#fd7e14',
            'resolved': '#198754',
            'rejected': '#dc3545',
            'reopened': '#6f42c1'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = _('Holat')
    
    def get_priority_badge(self, obj):
        """Priority rangli ko'rinishda"""
        colors = {
            'low': '#198754',
            'medium': '#ffc107',
            'high': '#dc3545'
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            obj.get_priority_display()
        )
    get_priority_badge.short_description = _('Ustuvorlik')


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'sender', 'message_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['message', 'ticket__id', 'sender__first_name', 'sender__last_name']
    autocomplete_fields = ['ticket', 'sender']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def message_preview(self, obj):
        """Xabar qisqartmasi"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = _('Xabar')


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'ticket',
        'action_type',
        'changed_by',
        'old_value',
        'new_value',
        'timestamp'
    ]
    list_filter = ['action_type', 'timestamp']
    search_fields = ['ticket__id', 'changed_by__first_name', 'changed_by__last_name', 'message']
    autocomplete_fields = ['ticket', 'changed_by']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    
    fieldsets = (
        (_('Asosiy ma\'lumotlar'), {
            'fields': ('ticket', 'changed_by', 'action_type')
        }),
        (_('O\'zgarishlar'), {
            'fields': ('old_value', 'new_value', 'message')
        }),
        (_('Vaqt'), {
            'fields': ('timestamp',)
        }),
    )