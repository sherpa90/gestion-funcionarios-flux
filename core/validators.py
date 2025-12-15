from django.core.exceptions import ValidationError
import re

def validate_run(value):
    """
    Valida un RUN chileno usando el algoritmo Módulo 11.
    Formato esperado: 12345678-K o 12345678K (sin puntos, con guion opcional).
    """
    # Limpiar puntos y guion
    run_clean = value.replace('.', '').replace('-', '').upper()
    
    if not re.match(r'^\d{7,8}[0-9K]$', run_clean):
        raise ValidationError('Formato de RUN inválido. Use formato 12345678-K.')

    cuerpo = run_clean[:-1]
    dv = run_clean[-1]

    # Algoritmo Módulo 11
    suma = 0
    multiplo = 2
    
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
            
    resto = suma % 11
    dv_calculado = 11 - resto
    
    if dv_calculado == 11:
        dv_calculado = '0'
    elif dv_calculado == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(dv_calculado)
        
    if dv != dv_calculado:
        raise ValidationError('RUN inválido (Dígito verificador incorrecto).')
