# reports/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _
from systems.models import System
from accounts.models import Region, User
from tickets.models import Ticket


class ReportFilterForm(forms.Form):
    """Hisobotlar uchun filter form"""
    
    # Sana oralig'i
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
            'placeholder': _('Boshlanish sanasi')
        }),
        label=_('Dan')
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
            'placeholder': _('Tugash sanasi')
        }),
        label=_('Gacha')
    )
    
    # Tizim
    system = forms.ModelChoiceField(
        queryset=System.objects.filter(is_active=True),
        required=False,
        empty_label=_('Barcha tizimlar'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Tizim')
    )
    
    # Viloyat
    region = forms.ModelChoiceField(
        queryset=Region.objects.filter(is_active=True),
        required=False,
        empty_label=_('Barcha viloyatlar'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Viloyat')
    )
    
    # Holat
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('Barcha holatlar'))] + Ticket.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Holat')
    )
    
    # Ustuvorlik
    priority = forms.ChoiceField(
        required=False,
        choices=[('', _('Barcha ustuvorliklar'))] + Ticket.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Ustuvorlik')
    )
    
    # Mas'ul texnik/admin
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role__in=['technician', 'admin', 'superadmin']
        ).order_by('first_name', 'last_name'),
        required=False,
        empty_label=_('Barcha xodimlar'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Mas\'ul xodim')
    )
    
    # Baholash
    rating = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('Barcha baholar')),
            ('5', '⭐⭐⭐⭐⭐ (5)'),
            ('4', '⭐⭐⭐⭐ (4)'),
            ('3', '⭐⭐⭐ (3)'),
            ('2', '⭐⭐ (2)'),
            ('1', '⭐ (1)'),
            ('none', _('Baholanmagan')),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Baholash')
    )
    
    # Hisobot turi
    report_type = forms.ChoiceField(
        required=False,
        choices=[
            ('tickets', _('Murojaatlar ro\'yxati')),
            ('statistics', _('Statistika')),
            ('technician_performance', _('Texniklar samaradorligi')),
            ('system_analysis', _('Tizimlar tahlili')),
            ('regional_analysis', _('Viloyatlar tahlili')),
        ],
        initial='tickets',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Hisobot turi')
    )
    
    # Export format
    export_format = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('Ko\'rish (web)')),
            ('pdf', 'PDF'),
            ('excel', 'Excel (XLSX)'),
            ('csv', 'CSV'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Export format')
    )