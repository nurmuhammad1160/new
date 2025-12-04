from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Region(models.Model):
    """Viloyatlar"""
    name = models.CharField(max_length=100, verbose_name=_("Viloyat nomi"))
    code = models.CharField(max_length=10, unique=True, verbose_name=_("Kod"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    
    class Meta:
        verbose_name = _("Viloyat")
        verbose_name_plural = _("Viloyatlar")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Department(models.Model):
    """Hududiy bo'limlar"""
    name = models.CharField(max_length=200, verbose_name=_("Bo'lim nomi"))
    region = models.ForeignKey(
        Region, 
        on_delete=models.CASCADE, 
        related_name='departments',
        verbose_name=_("Viloyat")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    
    class Meta:
        verbose_name = _("Bo'lim")
        verbose_name_plural = _("Bo'limlar")
        ordering = ['region', 'name']
    
    def __str__(self):
        return f"{self.region.name} - {self.name}"


class User(AbstractUser):
    """Custom User Model"""
    
    ROLE_CHOICES = [
        ('user', _('Oddiy foydalanuvchi')),
        ('technician', _('Texnik xodim')),
        ('admin', _('Admin')),
        ('superadmin', _('Bosh admin')),
    ]
    
    LANGUAGE_CHOICES = [
        ('uz', _("O'zbekcha (Lotin)")),
        ('uz-cy', _("Ўзбекча (Кирилл)")),
        ('ru', _('Русский')),
    ]
    
    # Asosiy ma'lumotlar
    last_name = models.CharField(max_length=150, verbose_name=_("Familiya"))
    first_name = models.CharField(max_length=150, verbose_name=_("Ism"))
    middle_name = models.CharField(max_length=150, blank=True, verbose_name=_("Sharif"))
    
    # Tashkiliy ma'lumotlar
    region = models.ForeignKey(
        Region, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Viloyat")
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Hududiy bo'lim")
    )
    position = models.CharField(max_length=200, blank=True, verbose_name=_("Lavozim"))
    
    # Aloqa ma'lumotlari
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefon"))
    
    # Tizim sozlamalari
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='user',
        verbose_name=_("Rol")
    )
    language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='uz',
        verbose_name=_("Til")
    )
    
    # Profil rasmi
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True,
        verbose_name=_("Avatar")
    )
    
    # Holat
    is_active = models.BooleanField(default=True, verbose_name=_("Aktiv"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("O'zgartirilgan"))
    
    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
    
    def get_full_name(self):
        """To'liq ism"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)
    
    def is_user(self):
        return self.role == 'user'
    
    def is_technician(self):
        return self.role == 'technician'
    
    def is_admin(self):
        return self.role in ['admin', 'superadmin']
    
    def is_superadmin(self):
        return self.role == 'superadmin'