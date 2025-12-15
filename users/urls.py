from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    BulkUserImportView, download_template
)

urlpatterns = [
    path('', UserListView.as_view(), name='user_list'),
    path('crear/', UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/editar/', UserUpdateView.as_view(), name='user_edit'),
    path('<int:pk>/eliminar/', UserDeleteView.as_view(), name='user_delete'),
    path('importar/', BulkUserImportView.as_view(), name='bulk_import_users'),
    path('plantilla/', download_template, name='download_user_template'),
]
