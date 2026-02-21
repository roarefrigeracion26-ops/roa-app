from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from users.mixins import TecnicoRequiredMixin
from users.models import Rol
from django.views import View
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from inventory.models import Rack
from .models import RegistroActividad, TipoActividad
from .services import (
    tecnico_tiene_tarea_abierta,
    obtener_tarea_abierta,
    iniciar_actividad,
    duracion_minutos,
    es_duracion_sospechosa,
)
from .forms import ParametrosEntradaForm, ParametrosSalidaForm, CierreForm


class ScannerView(TecnicoRequiredMixin, View):
    """Pantalla que activa la cámara para leer el QR del rack."""
    def get(self, request):
        tarea_abierta = obtener_tarea_abierta(request.user)
        racks = Rack.objects.filter(activo=True).order_by('tienda__nombre', 'ubicacion')
        return render(request, 'operations/scanner.html', {
            'tarea_abierta': tarea_abierta,
            'racks': racks,
        })


class FichaTecnicaView(TecnicoRequiredMixin, View):
    """Ficha del rack + botones Preventivo / Correctivo / Emergencia."""
    def get(self, request, rack_id):
        rack = get_object_or_404(Rack, pk=rack_id, activo=True)
        if tecnico_tiene_tarea_abierta(request.user):
            tarea = obtener_tarea_abierta(request.user)
            if tarea.rack_id != rack.id:
                return render(request, 'operations/bloqueo_tarea.html', {
                    'tarea_abierta': tarea,
                    'rack_solicitado': rack,
                })
        return render(request, 'operations/ficha_tecnica.html', {
            'rack': rack,
            'tipos': TipoActividad.choices,
        })


class IniciarActividadView(TecnicoRequiredMixin, View):
    """POST: inicia cronómetro y crea registro; redirige a check-in."""
    def post(self, request, rack_id):
        rack = get_object_or_404(Rack, pk=rack_id, activo=True)
        tipo = request.POST.get('tipo_actividad')
        if not tipo:
            return redirect('operations:ficha', rack_id=rack_id)
        try:
            registro = iniciar_actividad(request.user, rack, tipo)
            return redirect('operations:checkin', registro_id=registro.pk)
        except ValueError as e:
            return render(request, 'operations/ficha_tecnica.html', {
                'rack': rack,
                'tipos': TipoActividad.choices,
                'error': str(e),
            })


class CheckInView(TecnicoRequiredMixin, View):
    """Parámetros de entrada. No se puede ver check-out hasta guardar."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(initial=registro.datos_entrada or None, rack=registro.rack)
        return render(request, 'operations/checkin.html', {
            'registro': registro,
            'form': form,
        })

    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(request.POST, rack=registro.rack)
        if form.is_valid():
            registro.datos_entrada = form.to_json()
            registro.save(update_fields=['datos_entrada'])
            return redirect('operations:checkout', registro_id=registro.pk)
        return render(request, 'operations/checkin.html', {'registro': registro, 'form': form})


class SaltarCheckInView(TecnicoRequiredMixin, View):
    """POST: marca todos los parámetros iniciales como 'No medido' y redirige a cierre."""
    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form = ParametrosEntradaForm(rack=registro.rack)
        # Llenamos el JSON de entrada con "No medido" para cada campo del form
        datos = {}
        for field_name in form.fields:
            datos[field_name] = "No medido"
        registro.datos_entrada = datos
        registro.save(update_fields=['datos_entrada'])
        return redirect('operations:checkout', registro_id=registro.pk)


class CheckOutView(TecnicoRequiredMixin, View):
    """Cierre: mismos parámetros que entrada + observaciones. Al finalizar se graba hora_fin y se bloquea."""
    def get(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form_salida = ParametrosSalidaForm(initial=registro.datos_salida or None, rack=registro.rack)
        form_cierre = CierreForm(initial={'observaciones': registro.observaciones})
        return render(request, 'operations/checkout.html', {
            'registro': registro,
            'form_salida': form_salida,
            'form_cierre': form_cierre,
        })

    def post(self, request, registro_id):
        registro = get_object_or_404(RegistroActividad, pk=registro_id, tecnico=request.user, cerrado=False)
        form_salida = ParametrosSalidaForm(request.POST, rack=registro.rack)
        form_cierre = CierreForm(request.POST)
        if form_salida.is_valid() and form_cierre.is_valid():
            registro.datos_salida = form_salida.to_json()
            registro.observaciones = form_cierre.cleaned_data.get('observaciones', '')
            registro.hora_fin = timezone.now()
            registro.marcar_cerrado()
            minutos = duracion_minutos(registro.hora_inicio, registro.hora_fin)
            alerta_corto = es_duracion_sospechosa(minutos)
            return render(request, 'operations/actividad_cerrada.html', {
                'registro': registro,
                'minutos': minutos,
                'alerta_corto': alerta_corto,
            })
        return render(request, 'operations/checkout.html', {
            'registro': registro,
            'form_salida': form_salida,
            'form_cierre': form_cierre,
        })


# API para el escáner QR (solo técnicos)
@require_GET
@login_required
def api_rack_qr(request, id_qr):
    """Devuelve JSON del rack. Solo técnicos (supervisores no escanean)."""
    if getattr(request.user, 'rol', None) != Rol.TECNICO:
        return JsonResponse({'ok': False, 'error': 'Solo técnicos pueden escanear.'}, status=403)
    rack = get_object_or_404(Rack, id_qr=id_qr, activo=True)
    return JsonResponse({
        'ok': True,
        'id': rack.pk,
        'id_qr': rack.id_qr,
        'tienda': rack.tienda.nombre,
        'marca': rack.marca,
        'ubicacion': rack.ubicacion,
        'compresores_media': rack.compresores_media,
        'compresores_baja': rack.compresores_baja,
    })
