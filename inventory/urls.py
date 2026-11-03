from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'inventory'
urlpatterns = [
    path('empresas/', views.EmpresaListView.as_view(), name='empresas'),
    path('empresa/<int:empresa_id>/sedes/', views.ClienteListView.as_view(), name='sedes_empresa'),
    path(
        'clientes/',
        RedirectView.as_view(pattern_name='inventory:empresas', permanent=False),
        name='clientes',
    ),
    path('cliente/<int:cliente_id>/equipos/', views.EquiposClienteView.as_view(), name='equipos_cliente'),
    # API QR (futuro uso)
    path('api/equipo/<str:id_qr>/', views.api_equipo_qr, name='api_equipo_qr'),
]
