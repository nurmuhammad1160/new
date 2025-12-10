# tickets/forms.py
# ============================================
# TICKET FORMS - TO'LIQ VERSIYA
# ============================================

from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm
from .models import Ticket, TicketMessage
from systems.models import System
from accounts.models import User, Region


# ============================================
# TICKET CREATE FORM
# ============================================
class TicketCreateForm(forms.ModelForm):
    """Yangi murojaat yaratish formasi"""
    
    class Meta:
        model = Ticket
        fields = ['system', 'priority', 'description', 'attachment']
        widgets = {
            'system': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 5,
                'placeholder': _('Muammoni batafsil yozing...')
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'system': _('Tizim'),
            'priority': _('Ustuvorlik'),
            'description': _('Muammo tavsifi'),
            'attachment': _('Fayl (ixtiyoriy)'),
        }


# ============================================
# TICKET MESSAGE FORM
# ============================================
class TicketMessageForm(forms.ModelForm):
    """Chat xabari yuborish formasi"""
    
    class Meta:
        model = TicketMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Xabar yozing...')
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-input'}),
        }
        labels = {
            'message': _('Xabar'),
            'attachment': _('Fayl (ixtiyoriy)'),
        }


# ============================================
# TICKET RATING FORM
# ============================================
class TicketRatingForm(forms.ModelForm):
    """Murojaatni baholash formasi"""
    
    class Meta:
        model = Ticket
        fields = ['rating', 'rating_comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[
                (1, '⭐'),
                (2, '⭐⭐'),
                (3, '⭐⭐⭐'),
                (4, '⭐⭐⭐⭐'),
                (5, '⭐⭐⭐⭐⭐'),
            ]),
            'rating_comment': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Izoh qoldiring (ixtiyoriy)...')
            }),
        }
        labels = {
            'rating': _('Baholash'),
            'rating_comment': _('Izoh'),
        }


# ============================================
# TICKET FILTER FORM - TO'LIQ VERSIYA
# ============================================
class TicketFilterForm(forms.Form):
    """Ticketlarni filtrlash formasi - BARCHA FIELDLAR"""
    
    # ✅ TIZIM
    system = forms.ModelChoiceField(
        queryset=System.objects.filter(is_active=True).order_by('name'),
        required=False,
        label=_('Tizim'),
        empty_label=_('Barcha tizimlar'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ✅ VILOYAT (MUHIM!)
    region = forms.ModelChoiceField(
        queryset=Region.objects.filter(is_active=True).order_by('name'),
        required=False,
        label=_('Viloyat'),
        empty_label=_('Barcha viloyatlar'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ✅ HOLAT
    status = forms.ChoiceField(
        choices=[('', _('Barcha holatlar'))] + list(Ticket.STATUS_CHOICES),
        required=False,
        label=_('Holat'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ✅ USTUVORLIK
    priority = forms.ChoiceField(
        choices=[('', _('Barcha ustuvorliklar'))] + list(Ticket.PRIORITY_CHOICES),
        required=False,
        label=_('Ustuvorlik'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ✅ MAS'UL XODIM
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role__in=['technician', 'admin'],
            is_active=True
        ).order_by('first_name'),
        required=False,
        label=_('Mas\'ul xodim'),
        empty_label=_('Barcha xodimlar'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # ✅ SANADAN
    date_from = forms.DateField(
        required=False,
        label=_('Sanadan'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )
    
    # ✅ SANAGACHA
    date_to = forms.DateField(
        required=False,
        label=_('Sanagacha'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )