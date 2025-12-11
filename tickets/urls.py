from django.urls import path
from . import views
from . import views_superadmin

app_name = 'tickets'

urlpatterns = [
    # ============================================
    # USER VIEWS
    # ============================================
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_ticket, name='create_ticket'),
    path('<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('<int:pk>/send-message/', views.send_message, name='send_message'),
    path('<int:pk>/rate/', views.rate_ticket, name='rate_ticket'),
    path('<int:pk>/reopen/', views.reopen_ticket, name='reopen_ticket'),
    path('system-responsibles/', views.system_responsibles_view, name='system_responsibles'),
    path('system/<int:system_id>/responsibles/', views.system_responsibles_modal_view, name='system_responsibles_modal'),
    
    # ============================================
    # TECHNICIAN VIEWS
    # ============================================
    path('technician/', views.technician_tickets, name='technician_tickets'),
    path('<int:pk>/change-status/', views.change_ticket_status, name='change_ticket_status'),
    
    # ============================================
    # ADMIN VIEWS
    # ============================================
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('<int:pk>/assign/', views.assign_ticket, name='assign_ticket'),
    path('users/', views.users_list, name='users_list'),
    path('users/<int:user_id>/change-role/', views.change_user_role, name='change_user_role'),
    
    # ============================================
    # SUPERADMIN VIEWS
    # ============================================
    
    # Dashboard
    path('superadmin/', views_superadmin.superadmin_dashboard, name='superadmin_dashboard'),
    
    # User Management
    path('superadmin/users/', views_superadmin.superadmin_users_list, name='superadmin_users_list'),
    path('superadmin/users/<int:user_id>/', views_superadmin.superadmin_user_detail, name='superadmin_user_detail'),
    path('superadmin/users/<int:user_id>/change-role/', views_superadmin.superadmin_change_role, name='superadmin_change_role'),
    path('superadmin/users/<int:user_id>/toggle-status/', views_superadmin.superadmin_toggle_user_status, name='superadmin_toggle_status'),
    path('superadmin/users/create/', views_superadmin.superadmin_create_user, name='superadmin_create_user'),
    path('superadmin/users/<int:user_id>/delete/', views_superadmin.superadmin_delete_user, name='superadmin_delete_user'),
    
    # Password Management
    path('superadmin/users/<int:user_id>/reset-password/', views_superadmin.superadmin_reset_password, name='superadmin_reset_password'),
    path('superadmin/users/<int:user_id>/generate-temp-password/', views_superadmin.superadmin_generate_temp_password, name='superadmin_generate_temp_password'),
    
    # System Settings
    path('superadmin/settings/', views_superadmin.superadmin_system_settings, name='superadmin_settings'),
    
    # Audit Logs
    path('superadmin/audit-logs/', views_superadmin.superadmin_audit_logs, name='superadmin_audit_logs'),
    
    # AJAX
    path('superadmin/users/search-ajax/', views_superadmin.superadmin_users_search_ajax, name='superadmin_users_search_ajax'),
    path('api/users/search/', views_superadmin.api_users_search, name='api_users_search'),

    # Department Management
    path('superadmin/departments/', views_superadmin.superadmin_departments_list, name='superadmin_departments_list'),
    path('superadmin/departments/create/', views_superadmin.superadmin_department_create, name='superadmin_department_create'),
    path('superadmin/departments/<int:dept_id>/edit/', views_superadmin.superadmin_department_edit, name='superadmin_department_edit'),
    path('superadmin/departments/<int:dept_id>/toggle/', views_superadmin.superadmin_department_toggle_status, name='superadmin_department_toggle_status'),
    path('superadmin/departments/<int:dept_id>/delete/', views_superadmin.superadmin_department_delete, name='superadmin_department_delete'),

    # Superadmin API endpoints
    path('api/unassigned-tickets/', views_superadmin.api_unassigned_tickets, name='api_unassigned_tickets'),
    path('api/reopened-tickets/', views_superadmin.api_reopened_tickets, name='api_reopened_tickets'),
]