import os
import django
import sys

sys.path.append(os.path.abspath('.'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings") 
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from inventory.models import EquipoAA

User = get_user_model()
u = User.objects.first()
eq = EquipoAA.objects.first()

c = Client(enforce_csrf_checks=False, HTTP_HOST='127.0.0.1')
c.force_login(u)

post_data = {
    'tipo': 'MP',
    'radicado_numero': '1234',
    'cliente_nombre': 'Cliente Test',
    'dir_cliente': 'Dir',
    'num_orden': 'Num',
    'fecha': '2025-08-01',
    'mes': '08/2025'
}

response = c.post(f'/operations/equipo/{eq.id}/nueva-orden/', post_data)

print("Status Code:", response.status_code)
if response.status_code == 200:
    html = response.content.decode('utf-8')
    if "alert-danger" in html or "error" in html.lower():
        print("HTML CONTAINS ERRORS!")
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if "alert-danger" in line:
                print(lines[i])
                if i+1 < len(lines): print(lines[i+1])
    else:
        print("No apparent errors in HTML")
elif response.status_code == 302:
    print("Redirected to:", response.url)
else:
    print("Unexpected status code")
