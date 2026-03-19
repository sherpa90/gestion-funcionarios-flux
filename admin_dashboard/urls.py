from django.urls import path
from .views import AdminDashboardView, SystemLogsView, BlockedUsersView, SystemBackupView, SystemBackupExportView, SystemBackupRestoreView

app_name = 'admin_dashboard'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('logs/', SystemLogsView.as_view(), name='logs'),
    path('usuarios-bloqueados/', BlockedUsersView.as_view(), name='blocked_users'),
    path('backup/', SystemBackupView.as_view(), name='system_backup'),
    path('backup/export/', SystemBackupExportView.as_view(), name='system_backup_export'),
    path('backup/restore/', SystemBackupRestoreView.as_view(), name='system_backup_restore'),
]
