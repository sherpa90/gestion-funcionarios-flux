from django import forms
from datetime import datetime
from .models import HorarioFuncionario

class HorarioFuncionarioForm(forms.ModelForm):
    """Formulario para gestionar horarios de funcionarios"""
    class Meta:
        model = HorarioFuncionario
        fields = ["hora_entrada", "tolerancia_minutos", "activo"]
        widgets = {
            "hora_entrada": forms.TimeInput(attrs={
                "type": "time",
                "class": "mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            }),
            "tolerancia_minutos": forms.NumberInput(attrs={
                "min": "0",
                "max": "60",
                "class": "mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            }),
            "activo": forms.CheckboxInput(attrs={
                "class": "h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            }),
        }

class CargaHorariosForm(forms.Form):
    """Formulario para cargar archivos Excel de horarios"""
    archivo_excel = forms.FileField(
        label="Archivo de Horarios",
        help_text="Sube el archivo Excel (.xlsx/.xls) o PDF con los horarios de entrada de funcionarios. El archivo debe tener las columnas: RUT, Hora_Entrada, Tolerancia.",
        widget=forms.FileInput(attrs={
            "class": "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100",
            "accept": ".xlsx,.xls,.pdf"
        })
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get("archivo_excel")
        if archivo:
            # Validar extensión
            if not archivo.name.lower().endswith((".xlsx", ".xls", ".pdf")):
                raise forms.ValidationError("El archivo debe ser Excel (.xlsx/.xls) o PDF")
            # Validar tamaño (max 5MB)
            if archivo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe superar los 5MB")
        return archivo


class CargaRegistrosAsistenciaForm(forms.Form):
    """Formulario para cargar archivos Excel de registros del reloj control"""
    archivo_excel = forms.FileField(
        label="Archivo de Registros",
        help_text="Sube el archivo Excel (.xlsx/.xls) con columnas RUT, Nombre, Horario (DD-MM-YYYY HH:MM) o PDF con formato 'RUT, Nombre Horario'. Para PDFs sin fecha, especifica Mes/Año abajo.",
        widget=forms.FileInput(attrs={
            "class": "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100",
            "accept": ".xlsx,.xls,.pdf"
        })
    )

    # Campos de fecha para PDFs que no incluyen fecha
    mes = forms.ChoiceField(
        label="Mes",
        choices=[
            (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
            (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
            (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
        ],
        initial=datetime.now().month,
        widget=forms.Select(attrs={
            "class": "mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
        })
    )

    anio = forms.IntegerField(
        label="Año",
        initial=datetime.now().year,
        widget=forms.NumberInput(attrs={
            "class": "mt-1 block w-full px-3 py-2 border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500",
            "min": "2020",
            "max": "2030"
        })
    )

    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get("archivo_excel")
        if archivo:
            # Validar extensión
            if not archivo.name.lower().endswith((".xlsx", ".xls", ".pdf")):
                raise forms.ValidationError("El archivo debe ser Excel (.xlsx/.xls) o PDF")
            # Validar tamaño (max 10MB para registros)
            if archivo.size > 10 * 1024 * 1024:
                raise forms.ValidationError("El archivo no debe superar los 10MB")
        return archivo
