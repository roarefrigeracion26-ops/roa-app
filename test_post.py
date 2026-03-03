from django.test import RequestFactory
from operations.views import NuevaOrdenView
from inventory.models import EquipoAA
from django.contrib.auth import get_user_model
import traceback

User = get_user_model()
u = User.objects.first()
eq = EquipoAA.objects.first()

rf = RequestFactory()
post_data = {
    'tipo': 'MP',
    'radicado_numero': '1234',
    'cliente_nombre': 'Test Cliente',
    'fecha': '2025-08-01',
}
request = rf.post(f'/operations/equipo/{eq.id}/nueva-orden/', post_data)
request.user = u

view = NuevaOrdenView.as_view()
try:
    response = view(request, equipo_id=eq.id)
    print("Response status:", response.status_code)
    try:
        if response.context_data and 'form' in response.context_data:
            print("Form errors:", response.context_data['form'].errors)
    except:
        pass
except Exception as e:
    print("EXCEPTION OCCURRED:")
    traceback.print_exc()
