from django.urls import path
from .views import LicenciaCreateView, LicenciaListView

urlpatterns = [
    path('subir/', LicenciaCreateView.as_view(), name='subir_licencia'),
    path('mis-licencias/', LicenciaListView.as_view(), name='licencia_list'),
]
