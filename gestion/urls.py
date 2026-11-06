from django.urls import path

from . import views

app_name = 'gestion'

urlpatterns = [
    path('', views.GestionIndexView.as_view(), name='index'),
    path('empresas/', views.EmpresaListView.as_view(), name='empresas'),
    path('empresas/nueva/', views.EmpresaCreateView.as_view(), name='empresa_crear'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='empresa_editar'),
    path('empresas/<int:pk>/toggle/', views.EmpresaToggleView.as_view(), name='empresa_toggle'),
    path('sedes/', views.SedeListView.as_view(), name='sedes'),
    path('sedes/nueva/', views.SedeCreateView.as_view(), name='sede_crear'),
    path('sedes/<int:pk>/editar/', views.SedeUpdateView.as_view(), name='sede_editar'),
    path('sedes/<int:pk>/toggle/', views.SedeToggleView.as_view(), name='sede_toggle'),
    path('supervisores/', views.SupervisorListView.as_view(), name='supervisores'),
    path('supervisores/nuevo/', views.SupervisorCreateView.as_view(), name='supervisor_crear'),
    path('supervisores/<int:pk>/editar/', views.SupervisorUpdateView.as_view(), name='supervisor_editar'),
    path('supervisores/<int:pk>/toggle/', views.SupervisorToggleView.as_view(), name='supervisor_toggle'),
]
