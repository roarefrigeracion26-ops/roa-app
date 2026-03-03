import os
import django
import traceback
from django.conf import settings
from django.template import engines

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def debug_render():
    # Mock data
    class MockObj:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def __str__(self): return "MockObj"

    orden = MockObj(
        pk=5, radicado="RAD-2024-0005", get_tipo_display="Preventivo",
        cliente_nombre="TIENDA TEST", fecha="2024-05-20", dir_cliente="Calle 123",
        num_orden="123456", mes="Mayo"
    )
    
    context = {
        'orden': orden,
        'es_preventivo': True,
        'equipos_intervenidos': [],
        'actividades': [],
        'equipos_db': [],
        'equipos_json': '[]',
        'user': MockObj(is_authenticated=True, nombre_completo="Test User")
    }

    # IMPORTANT: We use a custom template string that includes our template
    # to bypass the URL tag issues if needed, or we just try to render it.
    # Actually, the best way to bypass {% url %} is to mock the url tag if possible,
    # but since this is just a quick check, let's just use a simple template.

    print("--- Intentando renderizar formulario_orden.html (CUIDADO: fallará si hay {% url %}) ---")
    try:
        engine = engines['django']
        # We'll try to read the file and remove the {% url %} tags for testing if it still fails
        with open('templates/operations/formulario_orden.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple regex-less removal of url tags for quick verification of variables
        import re
        content_no_urls = re.sub(r'{% url [^%]+ %}', '#URL#', content)
        
        from django.template import Template, Context
        template = Template(content_no_urls)
        # Note: Template class needs a Context but engines handle it differently.
        # We'll use the engine to be safe but the above manual way is better for bypassing tags.
        
        # Actually, let's just check the file content directly for the offending literal variables
        # that the user reported.
        print("Buscando variables literales en el archivo...")
        matches = re.findall(r'\{\{\s*[^}]+\s*\}\}', content)
        print(f"Encontradas {len(matches)} etiquetas de variables.")
        for m in matches[:5]: print(f"  Ejemplo: {m}")

        # If the file strictly has one tag per line or similar, we are good.
        # The main issue was split tags like {{ \n variable \n }}.
        if '\n' in content and re.search(r'\{\{[^}]*\n[^}]*\}\}', content):
            print("AVISO: Se encontraron etiquetas partidas en múltiples líneas!")
        else:
            print("EXITO: No se encontraron etiquetas partidas.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_render()
