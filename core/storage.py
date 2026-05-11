import os
import io
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible

@deconstructible
class EncryptedFileSystemStorage(FileSystemStorage):
    """
    Custom storage backend that encrypts files antes de guardarlos en el disco
    y los desencripta en memoria cuando son leídos (Ley N° 21.719).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ImproperlyConfigured("ENCRYPTION_KEY debe estar configurado en settings.py para usar EncryptedFileSystemStorage")
        self.fernet = Fernet(key)

    def _save(self, name, content):
        """Encriptar el contenido antes de guardarlo en disco"""
        content_bytes = content.read()
        if hasattr(content, 'seek'):
            content.seek(0)
            
        encrypted_bytes = self.fernet.encrypt(content_bytes)
        encrypted_content = ContentFile(encrypted_bytes, name=name)
        
        return super()._save(name, encrypted_content)

    def _open(self, name, mode='rb'):
        """Desencriptar el contenido al abrirlo desde el disco"""
        file_obj = super()._open(name, 'rb')
        encrypted_bytes = file_obj.read()
        file_obj.close()
        
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return ContentFile(decrypted_bytes, name=name)
        except Exception:
            # Si falla la desencriptación, asumimos que el archivo no estaba encriptado
            # (Útil para la fase de transición/migración de archivos antiguos)
            return ContentFile(encrypted_bytes, name=name)
