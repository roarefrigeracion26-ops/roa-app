import os
import django
from django.conf import settings
from django.template import Template, Context, engines

# Minimal Django setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            'APP_DIRS': True,
        }],
    )
    django.setup()

def check_file(path):
    print(f"\n--- Checking {path} ---")
    if not os.path.exists(path):
        print("FILE NOT FOUND!")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for split tags manually
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if '{{' in line and '}}' not in line:
            print(f"SPLIT TAG START at line {i+1}: {line.strip()}")
        if '}}' in line and '{{' not in line:
             # This is weak but might catch some
             pass

    # Try rendering
    try:
        engine = engines['django']
        # We need to mock the objects used in the template
        class MockObj:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
            def __str__(self): return "MockObj"

        mock_user = MockObj(username="testuser", get_full_name=lambda: "Test User")
        mock_orden = MockObj(
            radicado="MC1234",
            tecnico=mock_user,
            fecha="2026-03-03",
            cliente_nombre="Cliente Test",
            get_tipo_display="Mantenimiento Correctivo",
            pk=1,
            equipo=MockObj(nombre="UCA 1")
        )
        
        context = {
            'orden': mock_orden,
            'minutos': 17.5,
            'equipos_intervenidos': [],
            'es_preventivo': False,
        }

        # Need to handle 'extends base.html'
        # Let's just render a string version of the problematic part
        # to see if it renders correctly in this environment.
        
        test_snippet = """
        Técnico: {{ orden.tecnico.get_full_name|default:orden.tecnico.username }}
        Cliente: {{ orden.cliente_nombre }}
        """
        t = Template(test_snippet)
        print("Snippet Render Result:")
        print(t.render(Context(context)).strip())
        
        # Now try the actual file but mock the 'extends' if possible, 
        # or just grep for the rendered output in a full render
        template = engine.get_template('operations/orden_cerrada.html')
        rendered = template.render(context)
        print("Full File Render (Técnico line):")
        for line in rendered.splitlines():
            if "Técnico:" in line:
                print(line.strip())
            if "Cliente:" in line:
                print(line.strip())

    except Exception as e:
        print(f"Error: {e}")

check_file('templates/operations/orden_cerrada.html')
check_file('templates/operations/formulario_orden.html')
