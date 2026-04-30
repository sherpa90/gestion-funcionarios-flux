from django.urls import path
from .views import (
    AdminDashboardView, SystemLogsView, BlockedUsersView, 
    SystemBackupView, SystemBackupExportView, SystemBackupRestoreView,
    EfemerideListView, EfemerideCreateView, EfemerideUpdateView, EfemerideDeleteView
)

app_name = 'admin_dashboard'

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='dashboard'),
    path('logs/', SystemLogsView.as_view(), name='logs'),
    path('logs/export/', SystemLogsView.as_view(), name='logs_export'),
    path('usuarios-bloqueados/', BlockedUsersView.as_view(), name='blocked_users'),
    path('backup/', SystemBackupView.as_view(), name='system_backup'),
    path('backup/export/', SystemBackupExportView.as_view(), name='system_backup_export'),
    path('backup/restore/', SystemBackupRestoreView.as_view(), name='system_backup_restore'),
    
    # Efemérides
    path('efemerides/', EfemerideListView.as_view(), name='efemeride_list'),
    path('efemerides/nueva/', EfemerideCreateView.as_view(), name='efemeride_create'),
    path('efemerides/<int:pk>/editar/', EfemerideUpdateView.as_view(), name='efemeride_update'),
    path('efemerides/<int:pk>/eliminar/', EfemerideDeleteView.as_view(), name='efemeride_delete'),
]
