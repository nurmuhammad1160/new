from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import User, Region
from systems.models import System


class Ticket(models.Model):
    """Texnik murojaatlar"""
    
    PRIORITY_CHOICES = [
        ('low', _('Oddiy')),
        ('medium', _("O'rtacha")),
        ('high', _('Yuqori')),
    ]
    
    STATUS_CHOICES = [
        ('new', _('Yangi')),
        ('in_progress', _('Jarayonda')),
        ('pending_approval', _('Hal qilindi (kutilmoqda)')),
        ('resolved', _('Hal qilindi')),
        ('rejected', _('Rad etildi')),
        ('reopened', _('Qayta ochildi')),
    ]
    
    # Asosiy ma'lumotlar
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("Foydalanuvchi")
    )
    system = models.ForeignKey(
        System,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("Tizim")
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_("Viloyat")
    )
    
    # Murojaat tafsilotlari
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_("Ustuvorlik")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name=_("Holat")
    )
    description = models.TextField(verbose_name=_("Muammo ta'rifi"))
    attachment = models.FileField(
        upload_to='tickets/attachments/',
        blank=True,
        null=True,
        verbose_name=_("Fayl biriktirma")
    )
    
    # Mas'ul xodim
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_("Mas'ul xodim")
    )
    
    # Baholash
    rating = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name=_("Baholash")
    )
    rating_comment = models.TextField(
        blank=True,
        verbose_name=_("Baholash izohi")
    )
    
    # Vaqt ma'lumotlari
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("O'zgartirilgan"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Hal qilingan vaqt"))
    
    class Meta:
        verbose_name = _("Murojaat")
        verbose_name_plural = _("Murojaatlar")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.pk:04d} - {self.system.name} - {self.user.get_full_name()}"
    
    @property
    def can_reopen(self):
        """
        Ticketni qayta ochish mumkinmi tekshirish
        Faqat 3 kun ichida mumkin
        """
        if self.status != 'resolved':
            return False
        
        if not self.resolved_at:
            # Agar resolved_at bo'lmasa, har doim ochish mumkin
            return True
        
        # 3 kun o'tganmi?
        days_passed = (timezone.now() - self.resolved_at).days
        return days_passed <= 3
    
    @property
    def days_since_resolved(self):
        """Hal qilinganidan keyin necha kun o'tdi"""
        if not self.resolved_at:
            return None
        return (timezone.now() - self.resolved_at).days
    
    def get_ticket_number(self):
        """Ticket raqami: #2025-0001"""
        year = self.created_at.year
        return f"#{year}-{self.pk:04d}"
    
    def save(self, *args, **kwargs):
        # Agar status "Hal qilindi" ga o'zgarsa, vaqtni yozish
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


class TicketMessage(models.Model):
    """Ticket bo'yicha chat xabarlari"""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_("Murojaat")
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_messages',
        verbose_name=_("Yuboruvchi")
    )
    message = models.TextField(verbose_name=_("Xabar"))
    attachment = models.FileField(
        upload_to='tickets/chat_attachments/',
        blank=True,
        null=True,
        verbose_name=_("Fayl")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yuborilgan vaqt"))
    
    class Meta:
        verbose_name = _("Chat xabari")
        verbose_name_plural = _("Chat xabarlari")
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.ticket.get_ticket_number()} - {self.sender.get_full_name()}"


class TicketHistory(models.Model):
    """Ticket bo'yicha audit log (tarix)"""
    
    ACTION_CHOICES = [
        ('created', _('Yaratildi')),
        ('status_changed', _('Holat o\'zgartirildi')),
        ('assigned', _('Mas\'ul biriktirildi')),
        ('reassigned', _('Mas\'ul o\'zgartirildi')),
        ('comment', _('Izoh qo\'shildi')),
        ('reopened', _('Qayta ochildi')),
        ('rated', _('Baholandi')),
        ('file_attached', _('Fayl biriktirildi')),
    ]
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_("Murojaat")
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_changes',
        verbose_name=_("Kim tomonidan")
    )
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_("Harakat turi")
    )
    old_value = models.CharField(max_length=200, blank=True, verbose_name=_("Eski qiymat"))
    new_value = models.CharField(max_length=200, blank=True, verbose_name=_("Yangi qiymat"))
    message = models.TextField(blank=True, verbose_name=_("Izoh"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Vaqt"))
    
    class Meta:
        verbose_name = _("Murojaat tarixi")
        verbose_name_plural = _("Murojaat tarixlari")
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.ticket.get_ticket_number()} - {self.get_action_type_display()}"