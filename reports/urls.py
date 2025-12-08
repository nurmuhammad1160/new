# reports/urls.py

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.reports_dashboard, name='dashboard'),
    
    # Generate report
    path('generate/', views.generate_report, name='generate'),
]