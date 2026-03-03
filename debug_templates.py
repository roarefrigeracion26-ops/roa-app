import os
import django
from django.conf import settings
from django.template import Template, Context

# Configure minimal Django settings
if not settings.configured:
    settings.configure(
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(os.getcwd(), 'templates')],
        }]
    )
    django.setup()

def test_render(template_path, context_dict):
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        t = Template(template_content)
        c = Context(context_dict)
        rendered = t.render(c)
        
        print(f"--- RENDERED CONTENT ({template_path}) ---")
        # Print a slice around where the variables should be
        if "Técnico" in rendered:
            idx = rendered.find("Técnico")
            print(rendered[idx:idx+500])
        elif "equipo-card-idx" in rendered:
            idx = rendered.find("equipo-card-idx")
            print(rendered[idx:idx+1000])
        else:
            print(rendered[:2000])
        print("--- END ---")
    except Exception as e:
        print(f"Error rendering {template_path}: {e}")

# Mock data
class MockUser:
    username = "testuser"
    get_full_name = lambda self: "Test User Full Name"

class MockOrden:
    radicado = "MC1234"
    tecnico = MockUser()
    fecha = "2026-03-03"
    cliente_nombre = "Cliente Test"
    get_tipo_display = lambda self: "Mantenimiento Correctivo"
    pk = 1

context = {
    'orden': MockOrden(),
    'minutos': 17.5,
    'equipos_intervenidos': []
}

print("Testing orden_cerrada.html...")
test_render('templates/operations/orden_cerrada.html', context)
