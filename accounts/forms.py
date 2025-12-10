from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import User, Region, Department


class UserRegistrationForm(UserCreationForm):
    """Foydalanuvchi ro'yxatdan o'tish formasi"""
    
    class Meta:
        model = User
        fields = [
            'username',
            'last_name',
            'first_name',
            'middle_name',
            'region',
            'department',
            'position',
            'phone',
            'avatar',
            'password1',
            'password2',
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Login'),
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Familiya'),
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ism'),
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Sharif'),
            }),
            'region': forms.Select(attrs={
                'class': 'form-select',
            }),
            'department': forms.Select(attrs={
                'class': 'form-select',
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Lavozim'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+998 __ ___ __ __',
            }),
            'language': forms.Select(attrs={
                'class': 'form-select',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': _('Parol'),
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': _('Parolni tasdiqlang'),
        })
        
        # Middle_name ixtiyoriy
        self.fields['middle_name'].required = False
        self.fields['avatar'].required = False
        self.fields['department'].required = False

        self.fields['department'].queryset = Department.objects.filter(is_active=True)


class UserLoginForm(AuthenticationForm):
    """Foydalanuvchi kirish formasi"""
    
    username = forms.CharField(
        label=_('Login'),
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Login'),
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label=_('Parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('Parol'),
        })
    )


class UserProfileForm(forms.ModelForm):
    """Profil tahrirlash formasi"""
    
    class Meta:
        model = User
        fields = [
            'last_name',
            'first_name',
            'middle_name',
            'region',
            'department',
            'position',
            'phone',
            'language',
            'avatar',
        ]
        widgets = {
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'region': forms.Select(attrs={
                'class': 'form-select',
            }),
            'department': forms.Select(attrs={
                'class': 'form-select',
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
            }),
            'language': forms.Select(attrs={
                'class': 'form-select',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['middle_name'].required = False
        self.fields['department'].required = False


class PasswordChangeForm(forms.Form):
    """Parol o'zgartirish formasi"""
    
    old_password = forms.CharField(
        label=_('Joriy parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('Joriy parol'),
        })
    )
    new_password1 = forms.CharField(
        label=_('Yangi parol'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('Yangi parol'),
        })
    )
    new_password2 = forms.CharField(
        label=_('Yangi parolni tasdiqlang'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('Yangi parolni tasdiqlang'),
        })
    )