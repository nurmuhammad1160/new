from django import forms
from django.utils.translation import gettext_lazy as _
from .models import System, SystemResponsible
from accounts.models import User, Region


class SystemForm(forms.ModelForm):
    """Tizim qo'shish/tahrirlash formasi"""
    
    class Meta:
        model = System
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Tizim nomi'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Tizim haqida qisqacha...'),
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False


class SystemResponsibleForm(forms.ModelForm):
    """Tizim mas'uli belgilash formasi"""
    
    class Meta:
        model = SystemResponsible
        fields = ['system', 'user', 'role_in_system', 'region', 'is_default']
        widgets = {
            'system': forms.Select(attrs={
                'class': 'form-select',
            }),
            'user': forms.Select(attrs={
                'class': 'form-select',
            }),
            'role_in_system': forms.Select(attrs={
                'class': 'form-select',
            }),
            'region': forms.Select(attrs={
                'class': 'form-select',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['region'].required = False
        # Faqat texnik va adminlarni ko'rsatish
        self.fields['user'].queryset = User.objects.filter(
            role__in=['technician', 'admin', 'superadmin'],
            is_active=True
        )