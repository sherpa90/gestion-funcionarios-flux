#!/usr/bin/env python3
"""
Script para corregir los datos de equipos corruptos.
Este script corrige equipos que tienen texto de plantilla Django almacenado en los campos.
Ejecutar con: python3 fix_equipos_data.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
except Exception as e:
    print(f"Error configurando Django: {e}")
    sys.exit(1)

from equipos.models import Equipo

def clean_template_syntax(text):
    """Limpia sintaxis de plantilla de un texto"""
    if not text:
        return text
    # Eliminar todo lo que parezca sintaxis de plantilla
    import re
    # Eliminar {{ }}, {% %}, | y filtros
    cleaned = re.sub(r'\{\{.*?\}\}', '', text)
    cleaned = re.sub(r'\{%.*?%\}', '', cleaned)
    cleaned = cleaned.replace('|', '').strip()
    return cleaned if cleaned else None

def fix_equipos():
    """Corrige equipos con datos corruptos"""
    
    print("=" * 60)
    print("Corrigiendo datos de equipos en la base de datos...")
    print("=" * 60)
    
    equipos = Equipo.objects.all()
    fixed_count = 0
    
    for equipo in equipos:
        original_data = {
            'numero_serie': equipo.numero_serie,
            'numero_inventario': equipo.numero_inventario,
            'marca': equipo.marca,
            'modelo': equipo.modelo,
        }
        
        changes_made = []
        
        # Corregir cada campo
        for campo in ['numero_serie', 'numero_inventario', 'marca', 'modelo']:
            valor_original = getattr(equipo, campo)
            if valor_original:
                # Verificar si contiene sintaxis de plantilla
                if '{{' in valor_original or '{%' in valor_original or '}}' in valor_original or '%}' in valor_original:
                    valor_limpio = clean_template_syntax(valor_original)
                    if valor_limpio:
                        setattr(equipo, campo, valor_limpio)
                        changes_made.append(f"{campo}: '{valor_original[:50]}...' -> '{valor_limpio}'")
                    else:
                        # Si quedó vacío, usar un valor por defecto
                        if campo == 'numero_serie':
                            setattr(equipo, campo, 'SN-PENDIENTE')
                        elif campo == 'numero_inventario':
                            setattr(equipo, campo, 'INV-PENDIENTE')
                        changes_made.append(f"{campo}: '{valor_original[:50]}...' -> (valor por defecto)")
        
        if changes_made:
            print(f"\nEquipo ID {equipo.id}:")
            for change in changes_made:
                print(f"  - {change}")
            
            try:
                equipo.save()
                fixed_count += 1
                print(f"  ✓ GUARDADO")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"Total: {fixed_count} equipos corregidos")
    print("=" * 60)
    print("\nAhora los datos deberían mostrarse correctamente en la página.")

if __name__ == '__main__':
    fix_equipos()
