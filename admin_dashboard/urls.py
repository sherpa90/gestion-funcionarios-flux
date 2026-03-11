from django.urls import path
from .views import AdminDashboardView, SystemLogsView, BlockedUsersView

app_name = 'admin_dashboard'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('logs/', SystemLogsView.as_view(), name='logs'),
    path('usuarios-bloqueados/', BlockedUsersView.as_view(), name='blocked_users'),
]
