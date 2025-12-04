from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Ticket, TicketMessage
from systems.models import System


class TicketCreateForm(forms.ModelForm):
    """Yangi murojaat yaratish formasi"""
    
    class Meta:
        model = Ticket
        fields = ['system', 'priority', 'description', 'attachment']
        widgets = {
            'system': forms.Select(attrs={
                'class': 'form-select',
                'id': 'system-select',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 5,
                'placeholder': _('Muammo haqida batafsil yozing...'),
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].required = False
        # Faqat faol tizimlarni ko'rsatish
        self.fields['system'].queryset = System.objects.filter(is_active=True)


class TicketMessageForm(forms.ModelForm):
    """Ticket chat xabari formasi"""
    
    class Meta:
        model = TicketMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'chat-input',
                'rows': 3,
                'placeholder': _('Xabar yozing...'),
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].required = False


class TicketRatingForm(forms.ModelForm):
    """Ticket baholash formasi"""
    
    class Meta:
        model = Ticket
        fields = ['rating', 'rating_comment']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)],
                attrs={
                    'class': 'rating-input',
                }
            ),
            'rating_comment': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Qo\'shimcha izoh (ixtiyoriy)...'),
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating_comment'].required = False


class TicketStatusForm(forms.ModelForm):
    """Ticket holati o'zgartirish formasi (texnik uchun)"""
    
    class Meta:
        model = Ticket
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
        }


class TicketAssignForm(forms.ModelForm):
    """Ticket mas'ul xodim biriktirish formasi (admin uchun)"""
    
    class Meta:
        model = Ticket
        fields = ['assigned_to']
        widgets = {
            'assigned_to': forms.Select(attrs={
                'class': 'form-select',
            }),
        }


class TicketFilterForm(forms.Form):
    """Ticketlarni filtrlash formasi"""
    
    system = forms.ModelChoiceField(
        queryset=System.objects.filter(is_active=True),
        required=False,
        empty_label=_('Barcha tizimlar'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    status = forms.ChoiceField(
        choices=[('', _('Barcha holatlar'))] + Ticket.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    priority = forms.ChoiceField(
        choices=[('', _('Barcha ustuvorliklar'))] + Ticket.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        })
    )