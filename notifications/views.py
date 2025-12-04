from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from .models import Notification


@login_required
def notifications_list(request):
    """Bildirishnomalar ro'yxati"""
    notifications = request.user.notifications.all().order_by('-created_at')[:50]
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'notifications/list.html', context)


@login_required
def mark_as_read(request, pk):
    """Bildirishnomani o'qilgan deb belgilash"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    # Agar URL bo'lsa - o'sha sahifaga yo'naltirish
    if notification.url:
        return redirect(notification.url)
    
    return redirect('notifications:list')


@login_required
def mark_all_as_read(request):
    """Barcha bildirishnomalarni o'qilgan deb belgilash"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications:list')


@login_required
def get_unread_count(request):
    """O'qilmagan bildirishnomalar sonini olish (AJAX)"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def get_recent_notifications(request):
    """Oxirgi bildirishnomalarni olish (AJAX)"""
    notifications = request.user.notifications.filter(
        is_read=False
    ).order_by('-created_at')[:5]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'title': notif.title,
            'text': notif.text,
            'url': notif.url,
            'created_at': notif.created_at.strftime('%d.%m.%Y %H:%M'),
        })
    
    return JsonResponse({'notifications': data})