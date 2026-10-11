import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def run():
    from users.models import CustomUser

    user = CustomUser.objects.filter(is_superuser=True).first()
    if not user:
        user = CustomUser.objects.first()

    if not user:
        print("No user found in DB.")
        return

    client = Client()
    client.force_login(user)
    response = client.get('/equipos/lista/?funcionario_id=1')
    html = response.content.decode('utf-8')

    # Search for potential unparsed django tags, or html tags
    suspicious_lines = []
    for i, line in enumerate(html.split('\n')):
        if '{%' in line or '{{' in line or '&lt;' in line or '<script' in line or '}}' in line or '%}' in line:
            suspicious_lines.append(f"L{i+1}: {line.strip()}")

    if suspicious_lines:
        print("Found suspicious lines in output:")
        for line in suspicious_lines:
            print(line)
    else:
        print("No embedded code found.")

if __name__ == '__main__':
    run()
