import re

def normalize_rut(rut):
    """
    Normaliza un RUT chileno al formato chileno con puntos: 12.345.678-K.
    Maneja formatos de entrada con o sin puntos, con o sin guión.
    """
    if not rut:
        return rut

    # Convertir a string y mayúsculas
    rut = str(rut).upper()

    # Remover puntos existentes
    rut = rut.replace('.', '').replace(' ', '')

    # Si no tiene guión, agregarlo antes del último carácter
    if '-' not in rut:
        if len(rut) >= 2:
            rut = rut[:-1] + '-' + rut[-1]
        else:
            # RUT muy corto, agregar guión al final
            rut = rut + '-'

    # Asegurar que el dígito verificador sea válido
    parts = rut.split('-')
    if len(parts) == 2:
        cuerpo, dv = parts
        # Si dv no es dígito o K, intentar corregir
        if dv not in '0123456789K':
            # Usar el último dígito del cuerpo como dv si es posible
            if len(cuerpo) > 0:
                dv = cuerpo[-1]
                cuerpo = cuerpo[:-1]
                rut = cuerpo + '-' + dv

    # Formatear con puntos (formato chileno)
    cuerpo, dv = rut.split('-')
    # Insertar puntos de derecha a izquierda: 3 dígitos, 3 dígitos, resto
    cuerpo_reversed = cuerpo[::-1]
    formatted = []
    for i, char in enumerate(cuerpo_reversed):
        formatted.append(char)
        if (i + 1) % 3 == 0 and i + 1 < len(cuerpo_reversed):
            formatted.append('.')

    cuerpo_formatted = ''.join(formatted[::-1])
    rut_formatted = f"{cuerpo_formatted}-{dv}"

    return rut_formatted


def clean_rut_for_matching(rut):
    """
    Limpia un RUT para comparación, removiendo puntos pero manteniendo guión.
    Usado para matching de liquidaciones.
    """
    if not rut:
        return rut

    rut = str(rut).upper().replace('.', '').replace(' ', '')

    # Asegurar que tenga guión en la posición correcta
    if '-' not in rut:
        if len(rut) >= 2:
            rut = rut[:-1] + '-' + rut[-1]

    return rut