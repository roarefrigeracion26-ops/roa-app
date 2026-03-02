from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from users.models import Rol
from .models import Cliente, EquipoAA


class ClienteListView(LoginRequiredMixin, View):
    """Lista de clientes activos para seleccionar un equipo."""
    def get(self, request):
        from operations.services import obtener_preventivo_abierto
        clientes = Cliente.objects.filter(activo=True).order_by('nombre')
        preventivo_abierto = obtener_preventivo_abierto(request.user)
        return render(request, 'inventory/clientes.html', {
            'clientes': clientes,
            'preventivo_abierto': preventivo_abierto,
        })


class EquiposClienteView(LoginRequiredMixin, View):
    """Lista de equipos activos de un cliente."""
    def get(self, request, cliente_id):
        from operations.services import obtener_preventivo_abierto
        cliente = get_object_or_404(Cliente, pk=cliente_id, activo=True)
        equipos = EquipoAA.objects.filter(cliente=cliente, activo=True).order_by('nombre')
        preventivo_abierto = obtener_preventivo_abierto(request.user)
        return render(request, 'inventory/equipos_cliente.html', {
            'cliente': cliente,
            'equipos': equipos,
            'preventivo_abierto': preventivo_abierto,
        })


@login_required
def api_equipo_qr(request, id_qr):
    """API JSON para resolver un QR de equipo (uso futuro)."""
    if getattr(request.user, 'rol', None) != Rol.TECNICO:
        return JsonResponse({'ok': False, 'error': 'Solo técnicos pueden escanear.'}, status=403)
    equipo = get_object_or_404(EquipoAA, id_qr=id_qr, activo=True)
    return JsonResponse({
        'ok': True,
        'id': equipo.pk,
        'id_qr': equipo.id_qr,
        'nombre': equipo.nombre,
        'cliente': equipo.cliente.nombre,
        'tipo_equipo': equipo.tipo_equipo,
        'num_circuitos': equipo.num_circuitos,
        'marca': equipo.marca,
        'ubicacion': equipo.ubicacion,
    })
