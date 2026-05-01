import os
from datetime import datetime, time
import re

# Mocking parts of the environment if needed, but let's try to use the real functions
# We need to copy the functions from views.py or import them if possible.
# Since importing from views.py might be hard without a full django setup, I'll copy the relevant parts.

def parse_date(value):
    if not value: return None
    if hasattr(value, 'date'): return value.date()
    value_str = str(value).strip()
    formatos_fecha = ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d"]
    for formato in formatos_fecha:
        try: return datetime.strptime(value_str, formato).date()
        except ValueError: continue
    return None

def parse_time(value):
    if not value: return None
    if hasattr(value, 'time'): return value.time()
    value_str = str(value).strip()
    formatos_hora = ["%H:%M:%S", "%H:%M"]
    for formato in formatos_hora:
        try: return datetime.strptime(value_str, formato).time()
        except ValueError: continue
    match = re.search(r'(\d{1,2}):(\d{2})', value_str)
    if match:
        try: return time(int(match.group(1)), int(match.group(2)))
        except: pass
    return None

def test_excel_format_parsing(horario_raw):
    horario_str = str(horario_raw).strip()
    print(f"Testing: '{horario_str}' (type: {type(horario_raw)})")
    
    # Format 1: DD-MM-YYYY HH:MM
    fecha_hora_match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})$', horario_str)
    if fecha_hora_match:
        dia, mes_num, anio_num = fecha_hora_match.groups()[:3]
        hora_str, minuto_str = fecha_hora_match.groups()[3:]
        fecha = datetime(int(anio_num), int(mes_num), int(dia)).date()
        hora = time(int(hora_str), int(minuto_str))
        print(f"  Match Format 1: Fecha={fecha}, Hora={hora}")
        return fecha, hora
    
    # Format 2: parse_date + parse_time
    fecha = parse_date(horario_str)
    hora = parse_time(horario_str)
    print(f"  Match Format 2: Fecha={fecha}, Hora={hora}")
    return fecha, hora

print("--- Testing common formats ---")
test_excel_format_parsing("06-11-2025 07:15")
test_excel_format_parsing("06-11-2025 7:15")
test_excel_format_parsing("2025-11-06 07:15:00") # ISO format from datetime object
test_excel_format_parsing(datetime(2025, 11, 6, 7, 15))
