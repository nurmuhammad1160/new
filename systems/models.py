from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User, Region


class System(models.Model):
    """Tizimlar (Qalqon, 112, E-Material, va boshqalar)"""
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Tizim nomi"))
    description = models.TextField(blank=True, verbose_name=_("Ta'rif"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faol"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    
    class Meta:
        verbose_name = _("Tizim")
        verbose_name_plural = _("Tizimlar")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SystemResponsible(models.Model):
    """Tizimlar bo'yicha mas'ul xodimlar"""
    
    ROLE_CHOICES = [
        ('admin', _('Admin')),
        ('technician', _('Texnik xodim')),
    ]
    
    system = models.ForeignKey(
        System,
        on_delete=models.CASCADE,
        related_name='responsibles',
        verbose_name=_("Tizim")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='system_responsibilities',
        verbose_name=_("Xodim")
    )
    role_in_system = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name=_("Rol")
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='system_responsibles',
        verbose_name=_("Viloyat"),
        help_text=_("Agar bo'sh bo'lsa - respublika miqyosida mas'ul")
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Asosiy mas'ul"),
        help_text=_("Region bo'sh va is_default=True bo'lsa - respublika mas'uli")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    
    class Meta:
        verbose_name = _("Tizim mas'uli")
        verbose_name_plural = _("Tizim mas'ullari")
        unique_together = [['system', 'user', 'region']]
        ordering = ['system', 'region']
    
    def __str__(self):
        region_name = self.region.name if self.region else _("Respublika")
        return f"{self.system.name} - {region_name} - {self.user.get_full_name()}"