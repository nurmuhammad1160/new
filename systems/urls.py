from django.urls import path
from . import views

app_name = 'systems'

urlpatterns = [
    # Systems CRUD
    path('', views.systems_list, name='systems_list'),
    path('create/', views.system_create, name='system_create'),
    path('<int:pk>/edit/', views.system_edit, name='system_edit'),
    path('<int:pk>/delete/', views.system_delete, name='system_delete'),
    path('<int:pk>/toggle/', views.system_toggle_status, name='system_toggle_status'),
    
    # System Responsibles
    path('<int:system_id>/responsibles/', views.system_responsibles, name='system_responsibles'),
    path('<int:system_id>/responsibles/create/', views.responsible_create, name='responsible_create'),
    path('responsibles/<int:pk>/edit/', views.responsible_edit, name='responsible_edit'),
    path('responsibles/<int:pk>/delete/', views.responsible_delete, name='responsible_delete'),
    
    # AJAX endpoints
    path('<int:pk>/quick-toggle/', views.system_quick_toggle, name='system_quick_toggle'),
    path('search-ajax/', views.systems_search_ajax, name='systems_search_ajax'),
]