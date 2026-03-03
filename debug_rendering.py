import os
import django
import traceback
from django.conf import settings
from django.template import engines
from django.test import RequestFactory
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def debug_render():
    factory = RequestFactory()
    request = factory.get('/')
    
    # Mock data for OrdenServicio and User
    class MockUser:
        is_authenticated = True
        is_supervisor = False
        nombre_completo = "Tecnico de Prueba"
        username = "tecnico_test"
        def get_full_name(self): return "Tecnico Test"

    class MockOrden:
        pk = 5
        radicado = "RAD-2024-0005"
        tipo = "PREVENTIVO"
        get_tipo_display = lambda self: "Preventivo MP"
        cliente_nombre = "TIENDA TEST"
        fecha = "2024-05-20"
        dir_cliente = "Calle 123"
        num_orden = "123456"
        mes = "Mayo"
        tecnico = MockUser()
        equipos_intervenidos = type('obj', (object,), {
            'all': lambda: [], 
            'prefetch_related': lambda self, *args: self,
            '__iter__': lambda self: iter([])
        })()
        actividades = type('obj', (object,), {
            'all': lambda: [],
            '__iter__': lambda self: iter([])
        })()
        cliente = type('obj', (object,), {'pk': 1})()
        equipo = type('obj', (object,), {'pk': 1, 'nombre': 'Eq 1'})()

    request.user = MockUser()
    
    context = {
        'orden': MockOrden(),
        'equipo': MockOrden().equipo,
        'cliente': MockOrden().cliente,
        'equipos_intervenidos': [],
        'actividades': [],
        'es_preventivo': True,
        'equipos_db': [],
        'equipos_json': '[]',
        'user': MockUser(),
    }

    print("--- Intentando renderizar formulario_orden.html ---")
    try:
        # Clear template cache by getting a fresh engine if possible
        engine = engines['django']
        template = engine.get_template('operations/formulario_orden.html')
        rendered = template.render(context, request)
        
        output_file = 'debug_output_formulario_final.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rendered)
        
        print(f"Renderizado exitoso. Resultado en {output_file}")
        
        # Check if {{ or }} exists in the output
        if '{{' in rendered or '{%' in rendered:
            print("AVISO: Se encontraron delimitadores {{ o {% en el HTML final!")
        else:
            print("EXITO: No se encontraron delimitadores en el HTML final.")
            
    except Exception as e:
        print(f"Error renderizando: {e}")
        # traceback.print_exc()

if __name__ == "__main__":
    debug_render()
