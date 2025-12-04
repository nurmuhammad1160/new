from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class Notification(models.Model):
    """Foydalanuvchi bildirishnomalari"""
    
    NOTIFICATION_TYPES = [
        ('new_ticket', _('Yangi murojaat')),
        ('status_changed', _('Holat o\'zgartirildi')),
        ('new_message', _('Yangi xabar')),
        ('rating_request', _('Baholash so\'rovi')),
        ('ticket_assigned', _('Murojaat biriktirildi')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("Foydalanuvchi")
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name=_("Turi")
    )
    title = models.CharField(max_length=200, verbose_name=_("Sarlavha"))
    text = models.TextField(verbose_name=_("Matn"))
    url = models.CharField(max_length=500, blank=True, verbose_name=_("Havola"))
    is_read = models.BooleanField(default=False, verbose_name=_("O'qilgan"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    
    class Meta:
        verbose_name = _("Bildirishnoma")
        verbose_name_plural = _("Bildirishnomalar")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"
    
    def mark_as_read(self):
        """Bildirishnomani o'qilgan deb belgilash"""
        self.is_read = True
        self.save()