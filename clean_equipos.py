#!/usr/bin/env python3
"""
Script para limpiar caracteres problemáticos de los equipos.
Ejecutar desde el directorio del proyecto:
    python3 clean_equipos.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from equipos.models import Equipo

def clean_equipos():
    """Limpia caracteres de plantilla de los equipos existentes"""
    
    equipos = Equipo.objects.all()
    cleaned_count = 0
    error_count = 0
    
    for equipo in equipos:
        changed = False
        
        # Limpiar numero_serie
        if equipo.numero_serie:
            original = equipo.numero_serie
            # Eliminar cualquier carácter que parezca sintaxis de plantilla
            cleaned = original.replace('{{', '').replace('}}', '').replace('{%', '').replace('%} ', '').strip()
            if cleaned != original:
                print(f"Equipo #{equipo.numero_inventario}: numero_serie '{original}' -> '{cleaned}'")
                equipo.numero_serie = cleaned
                changed = True
        
        # Limpiar numero_inventario  
        if equipo.numero_inventario:
            original = equipo.numero_inventario
            cleaned = original.replace('{{', '').replace('}}', '').replace('{%', '').replace('%} ', '').strip()
            if cleaned != original:
                print(f"Equipo #{equipo.numero_inventario}: numero_inventario '{original}' -> '{cleaned}'")
                equipo.numero_inventario = cleaned
                changed = True
        
        # Limpiar marca
        if equipo.marca:
            original = equipo.marca
            cleaned = original.replace('{{', '').replace('}}', '').replace('{%', '').replace('%} ', '').strip()
            if cleaned != original:
                print(f"Equipo #{equipo.numero_inventario}: marca '{original}' -> '{cleaned}'")
                equipo.marca = cleaned
                changed = True
        
        # Limpiar modelo
        if equipo.modelo:
            original = equipo.modelo
            cleaned = original.replace('{{', '').replace('}}', '').replace('{%', '').replace('%} ', '').strip()
            if cleaned != original:
                print(f"Equipo #{equipo.numero_inventario}: modelo '{original}' -> '{cleaned}'")
                equipo.modelo = cleaned
                changed = True
        
        if changed:
            try:
                equipo.save()
                cleaned_count += 1
            except Exception as e:
                print(f"ERROR al guardar equipo #{equipo.numero_inventario}: {e}")
                error_count += 1
    
    print(f"\nResumen: {cleaned_count} equipos limpiados, {error_count} errores")

if __name__ == '__main__':
    print("Limpiando equipos de caracteres problemáticos...")
    clean_equipos()
