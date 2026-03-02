from django.urls import path
from . import views

app_name = 'inventory'
urlpatterns = [
    path('clientes/', views.ClienteListView.as_view(), name='clientes'),
    path('cliente/<int:cliente_id>/equipos/', views.EquiposClienteView.as_view(), name='equipos_cliente'),
    # API QR (futuro uso)
    path('api/equipo/<str:id_qr>/', views.api_equipo_qr, name='api_equipo_qr'),
]
