import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import CustomUser

user = CustomUser.objects.filter(is_superuser=True).first()
if not user:
    user = CustomUser.objects.first()

client = Client()
client.force_login(user)
response = client.get('/equipos/lista/?funcionario_id=1')
print("Status:", response.status_code)

html = response.content.decode('utf-8')
# Find any suspicious `{` or `<` that looks like raw code
import re
suspicious = []
for i, line in enumerate(html.split('\n')):
    if '{%' in line or '{{' in line or '}}' in line or '%}' in line:
        suspicious.append((i+1, line.strip()))

if suspicious:
    print("Found suspicious template tags in output:")
    for num, line in suspicious:
        print(f"L{num}: {line}")
else:
    print("No obvious raw template tags found in output.")

