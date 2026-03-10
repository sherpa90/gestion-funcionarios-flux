from django.core.exceptions import ValidationError
from django.conf import settings
import re
import os

# ─────────────────────────────────────────────
# A08 — File Upload Validator
# ─────────────────────────────────────────────

# Extensiones permitidas y sus magic bytes correspondientes
_ALLOWED_FILE_TYPES = {
    '.pdf':  [b'%PDF'],
    '.xlsx': [b'PK\x03\x04'],                      # Office Open XML (zip)
    '.xls':  [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE2 compound doc
    '.jpg':  [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.png':  [b'\x89PNG\r\n\x1a\n'],
}

_MAX_UPLOAD_MB = 10
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MB * 1024 * 1024


def validate_file_upload(file):
    """
    Valida un archivo subido verificando:
    1. Extensión permitida
    2. Tamaño máximo
    3. Magic bytes (firma real del archivo, no solo extensión)

    OWASP A08: Software and Data Integrity Failures
    """
    if not file:
        return

    # 1. Extensión
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in _ALLOWED_FILE_TYPES:
        raise ValidationError(
            f'Tipo de archivo no permitido "{ext}". '
            f'Solo se aceptan: {", ".join(_ALLOWED_FILE_TYPES.keys())}'
        )

    # 2. Tamaño
    if file.size > _MAX_UPLOAD_BYTES:
        raise ValidationError(
            f'El archivo es demasiado grande ({file.size // (1024*1024)} MB). '
            f'El máximo permitido es {_MAX_UPLOAD_MB} MB.'
        )

    # 3. Magic bytes — verifica que el contenido coincide con la extensión declarada
    file.seek(0)
    header = file.read(16)
    file.seek(0)

    expected_signatures = _ALLOWED_FILE_TYPES[ext]
    if not any(header.startswith(sig) for sig in expected_signatures):
        raise ValidationError(
            'El contenido del archivo no coincide con su extensión. '
            'Asegúrate de subir un archivo válido.'
        )


# ─────────────────────────────────────────────
# RUN Validator (existing)
# ─────────────────────────────────────────────

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
