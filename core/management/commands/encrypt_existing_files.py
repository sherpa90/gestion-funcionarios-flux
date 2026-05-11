from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from licencias.models import LicenciaMedica
from liquidaciones.models import Liquidacion
import os

class Command(BaseCommand):
    help = 'Encripta archivos sensibles antiguos que fueron subidos antes de implementar la Ley 21.719'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== INICIANDO CRIPTOGRAFÍA EN REPOSO ==="))
        
        modelos = [
            ('Licencias Médicas', LicenciaMedica),
            ('Liquidaciones de Sueldo', Liquidacion)
        ]
        
        total_encriptados = 0
        total_ya_encriptados = 0
        total_errores = 0

        for nombre_modelo, modelo in modelos:
            self.stdout.write(f"\nProcesando {nombre_modelo}...")
            registros = modelo.objects.exclude(archivo='')
            
            for obj in registros:
                try:
                    if not obj.archivo or not obj.archivo.storage.exists(obj.archivo.name):
                        continue
                        
                    # Obtenemos los bytes desde el disco crudo saltándonos la capa de Django 
                    # para saber si ya está encriptado
                    path_fisico = obj.archivo.path
                    with open(path_fisico, 'rb') as f:
                        raw_bytes = f.read()
                        
                    # Fernet tokens siempre empiezan con gAAAAA
                    if raw_bytes.startswith(b'gAAAAA'):
                        total_ya_encriptados += 1
                        continue
                        
                    # Si no está encriptado, lo leemos, y lo guardamos con nuestro custom storage
                    # que lo encriptará automáticamente
                    nombre_archivo = os.path.basename(obj.archivo.name)
                    
                    # Guardar a través de Django invocará EncryptedFileSystemStorage._save()
                    obj.archivo.save(nombre_archivo, ContentFile(raw_bytes))
                    self.stdout.write(self.style.SUCCESS(f"  + Encriptado: {nombre_archivo}"))
                    total_encriptados += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  x Error en {obj.id}: {str(e)}"))
                    total_errores += 1

        self.stdout.write(self.style.SUCCESS(f"\n=== MIGRACIÓN FINALIZADA ==="))
        self.stdout.write(f"Nuevos encriptados: {total_encriptados}")
        self.stdout.write(f"Ya estaban protegidos: {total_ya_encriptados}")
        self.stdout.write(f"Errores encontrados: {total_errores}")
