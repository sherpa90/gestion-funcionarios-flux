from django import forms
from .models import Efemeride

class EfemerideForm(forms.ModelForm):
    class Meta:
        model = Efemeride
        fields = ['titulo', 'fecha', 'responsable', 'descripcion']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm font-bold text-gray-700 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none'}),
            'titulo': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm font-bold text-gray-700 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none', 'placeholder': 'Ej: Día del Libro'}),
            'responsable': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm font-bold text-gray-700 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none', 'placeholder': 'Ej: Equipo CRA'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full px-4 py-3 bg-gray-50 border-none rounded-xl text-sm font-bold text-gray-700 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none', 'rows': 3, 'placeholder': 'Descripción opcional...'}),
        }
