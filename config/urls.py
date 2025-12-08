from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ✅ TIL O'ZGARTIRISH - BUNI QO'SHING!
    path('i18n/', include('django.conf.urls.i18n')),
    
    # Apps
    path('accounts/', include('accounts.urls')),
    path('tickets/', include('tickets.urls')),
    path('notifications/', include('notifications.urls')),
    path('systems/', include('systems.urls')),
    path('reports/', include('reports.urls')),
    
    # Root redirect to login
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]

# Media va static fayllar (development uchun)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin panel sozlamalari
admin.site.site_header = "IIV Texnik Yordam Tizimi"
admin.site.site_title = "IIV Admin"
admin.site.index_title = "Boshqaruv paneli"