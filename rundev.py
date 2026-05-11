#!/usr/bin/env python
"""
Servidor de desarrollo Django con HTTPS para localhost.
Necesario porque Chrome 127+ fuerza HTTPS en localhost (HSTS precargado).

Instalación del certificado autofirmado en Chrome (opcional para evitar advertencias):
  1. Abrir https://localhost:8000/
  2. Clic en "Avanzada" → "Ir a localhost (no seguro)"
  3. O importar core/ssl/cert.pem en el almacén de certificados de confianza

Uso:
    python rundev.py [puerto]
    python rundev.py 8000
"""
import os
import sys
import ssl
import socketserver
import pathlib

# Agregar el proyecto al path
BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, demo_app


class SSLWSGIServer(socketserver.TCPServer):
    """Servidor WSGI con soporte SSL/TLS."""
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, ssl_context):
        self.ssl_context = ssl_context
        super().__init__(server_address, RequestHandlerClass)

    def get_request(self):
        """Sobrescribe para envolver el socket con SSL."""
        newsocket, fromaddr = self.socket.accept()
        connstream = self.ssl_context.wrap_socket(newsocket, server_side=True)
        return connstream, fromaddr


class QuietWSGIRequestHandler(WSGIRequestHandler):
    """Handler que reduce el logging verboso."""
    def log_request(self, code='-', size='-'):
        # Solo loggear errores
        if int(str(code).split()[0]) >= 400:
            super().log_request(code, size)

    def log_message(self, format, *args):
        # Reducir ruido en la terminal
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = '127.0.0.1'

    # Configurar SSL
    ssl_dir = BASE_DIR / 'core' / 'ssl'
    cert_path = ssl_dir / 'cert.pem'
    key_path = ssl_dir / 'key.pem'

    if not cert_path.exists() or not key_path.exists():
        print(f"ERROR: Certificados no encontrados en {ssl_dir}")
        print("Ejecutá primero: openssl req -x509 -newkey rsa:4096 ...")
        sys.exit(1)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    # Crear aplicación WSGI
    application = get_wsgi_application()

    # Iniciar servidor HTTPS
    server = SSLWSGIServer((host, port), QuietWSGIRequestHandler, ssl_context)

    print(f"\n✅ Servidor HTTPS de desarrollo corriendo en:")
    print(f"   https://localhost:{port}/")
    print(f"   (Usá 'http://127.0.0.1:{port}/' si querés HTTP)\n")
    print(f"   Presioná Ctrl+C para detener el servidor.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido.")
        server.server_close()


if __name__ == '__main__':
    main()