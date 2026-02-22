from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    BulkUserImportView, download_template, ResetUserPasswordView, ChangeOwnPasswordView,
    AdminChangePasswordView, EmailDirectoryView
)

urlpatterns = [
    path('', UserListView.as_view(), name='user_list'),
    path('directorio/', EmailDirectoryView.as_view(), name='email_directory'),
    path('crear/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/editar/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/eliminar/', UserDeleteView.as_view(), name='user_delete'),
    path('importar/', BulkUserImportView.as_view(), name='bulk_import_users'),
    path('plantilla/', download_template, name='download_user_template'),
    path('<int:user_id>/reset-password/', ResetUserPasswordView.as_view(), name='reset_user_password'),
    path('<int:user_id>/cambiar-password/', AdminChangePasswordView.as_view(), name='admin_change_password'),
    path('cambiar-password/', ChangeOwnPasswordView.as_view(), name='change_password'),
]
