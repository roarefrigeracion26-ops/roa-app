from django.urls import path
from . import views

app_name = 'operations'
urlpatterns = [
    path('equipo/<int:equipo_id>/', views.FichaEquipoView.as_view(), name='ficha_equipo'),
    path('cliente/<int:cliente_id>/orden/nueva/', views.NuevaOrdenClienteView.as_view(), name='nueva_orden_cliente'),
    path('orden/nueva/<int:equipo_id>/', views.NuevaOrdenView.as_view(), name='nueva_orden'),
    path('orden/<int:orden_id>/formulario/', views.FormularioOrdenView.as_view(), name='formulario_orden'),
    path('orden/<int:orden_id>/equipo/agregar/', views.AgregarEquipoView.as_view(), name='agregar_equipo'),
    path('orden/<int:orden_id>/actividades/', views.ActualizarActividadesView.as_view(), name='actualizar_actividades'),
    path('orden/<int:orden_id>/finalizar/', views.FinalizarOrdenView.as_view(), name='finalizar_orden'),
    path('orden/<int:orden_id>/cerrada/', views.OrdenCerradaView.as_view(), name='orden_cerrada'),
    path('orden/<int:orden_id>/pdf/', views.PDFOrdenView.as_view(), name='pdf_orden'),
]
