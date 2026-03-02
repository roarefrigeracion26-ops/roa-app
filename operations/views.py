from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa
import io
import json

from inventory.models import EquipoAA
from .models import (
    OrdenServicio, EquipoIntervenido, MedicionUCA, MedicionSplit,
    Actividad, Observacion, TipoMantenimiento, EstadoOrden
)
from .services import (
    tecnico_tiene_preventivo_abierto,
    obtener_preventivo_abierto,
    iniciar_orden,
    duracion_minutos,
    es_duracion_sospechosa,
)
from .forms import (
    NuevaOrdenForm, EquipoIntervenidoForm,
    MedicionUCAForm, MedicionSplitForm,
    ActividadForm, ActividadCorrectivForm, ObservacionForm,
)


# ─────────────────────────────────────────────────────────
# Helper: xhtml2pdf link callback
# ─────────────────────────────────────────────────────────
def link_callback(uri, rel):
    import os
    s_url = settings.STATIC_URL
    m_url = getattr(settings, 'MEDIA_URL', '/media/')
    path = None
    if uri.startswith(s_url):
        relative_path = uri.replace(s_url, '', 1).lstrip('/')
        for d in getattr(settings, 'STATICFILES_DIRS', []):
            trial = os.path.join(d, relative_path)
            if os.path.exists(trial):
                path = trial
                break
        if not path:
            path = os.path.join(settings.STATIC_ROOT, relative_path)
    elif m_url and uri.startswith(m_url):
        relative_path = uri.replace(m_url, '', 1).lstrip('/')
        path = os.path.join(settings.MEDIA_ROOT, relative_path)
    if path and os.path.isfile(path):
        return path
    return uri


# ─────────────────────────────────────────────────────────
# FichaEquipoView: mostrar ficha y botones Preventivo/Correctivo
# ─────────────────────────────────────────────────────────
class FichaEquipoView(LoginRequiredMixin, View):
    """Muestra la ficha del equipo de AA con botones de tipo de mantenimiento."""
    def get(self, request, equipo_id):
        equipo = get_object_or_404(EquipoAA, pk=equipo_id, activo=True)
        preventivo_abierto = obtener_preventivo_abierto(request.user)
        return render(request, 'operations/ficha_equipo.html', {
            'equipo': equipo,
            'preventivo_abierto': preventivo_abierto,
        })


# ─────────────────────────────────────────────────────────
# NuevaOrdenView: GET form (tipo + radicado + encabezado)
# ─────────────────────────────────────────────────────────
class NuevaOrdenView(LoginRequiredMixin, View):
    """Formulario para elegir tipo, ingresar radicado y datos del encabezado."""
    def get(self, request, equipo_id):
        equipo = get_object_or_404(EquipoAA, pk=equipo_id, activo=True)
        # Bloquear si hay preventivo abierto
        preventivo_abierto = obtener_preventivo_abierto(request.user)
        if preventivo_abierto:
            return render(request, 'operations/bloqueo_preventivo.html', {
                'preventivo_abierto': preventivo_abierto,
                'equipo': equipo,
            })
        form = NuevaOrdenForm(initial={
            'cliente_nombre': equipo.cliente.nombre,
            'dir_cliente': equipo.cliente.dir_cliente,
            'fecha': timezone.localdate(),
            'mes': timezone.localdate().strftime('%-m/%Y') if hasattr(timezone.localdate(), 'strftime') else '',
        })
        return render(request, 'operations/nueva_orden.html', {
            'equipo': equipo,
            'form': form,
        })

    def post(self, request, equipo_id):
        equipo = get_object_or_404(EquipoAA, pk=equipo_id, activo=True)
        form = NuevaOrdenForm(request.POST)
        if form.is_valid():
            try:
                tipo = form.cleaned_data['tipo']
                radicado = form.get_radicado()
                orden = iniciar_orden(
                    tecnico=request.user,
                    equipo=equipo,
                    tipo=tipo,
                    radicado=radicado,
                    cliente_nombre=form.cleaned_data['cliente_nombre'],
                    dir_cliente=form.cleaned_data.get('dir_cliente', ''),
                    num_orden=form.cleaned_data.get('num_orden', ''),
                    fecha=form.cleaned_data['fecha'],
                    mes=form.cleaned_data.get('mes', ''),
                )
                return redirect('operations:formulario_orden', orden_id=orden.pk)
            except ValueError as e:
                return render(request, 'operations/bloqueo_preventivo.html', {
                    'preventivo_abierto': obtener_preventivo_abierto(request.user),
                    'equipo': equipo,
                    'error': str(e),
                })
        return render(request, 'operations/nueva_orden.html', {
            'equipo': equipo,
            'form': form,
        })


# ─────────────────────────────────────────────────────────
# FormularioOrdenView: formulario completo multi-equipo
# ─────────────────────────────────────────────────────────
class FormularioOrdenView(LoginRequiredMixin, View):
    """Formulario completo: actividades + equipos intervenidos + mediciones."""

    def _get_context(self, orden):
        equipos_intervenidos = orden.equipos_intervenidos.prefetch_related(
            'mediciones_uca', 'medicion_split', 'observacion'
        ).all()
        actividades = orden.actividades.all()
        return {
            'orden': orden,
            'equipo': orden.equipo,
            'equipos_intervenidos': equipos_intervenidos,
            'actividades': actividades,
            'equipo_form': EquipoIntervenidoForm(),
            'es_preventivo': orden.tipo == TipoMantenimiento.PREVENTIVO,
        }

    def get(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)
        return render(request, 'operations/formulario_orden.html', self._get_context(orden))


# ─────────────────────────────────────────────────────────
# AgregarEquipoView: agrega un EquipoIntervenido y sus mediciones
# ─────────────────────────────────────────────────────────
class AgregarEquipoView(LoginRequiredMixin, View):
    """POST: agrega un equipo intervenido con sus mediciones a la orden."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)
        equipo_form = EquipoIntervenidoForm(request.POST)

        if equipo_form.is_valid():
            ei = equipo_form.save(commit=False)
            ei.orden = orden
            ei.save()

            tipo_eq = request.POST.get('tipo_medicion', 'uca')  # 'uca' o 'split'

            if tipo_eq == 'uca':
                circuit_labels = request.POST.getlist('circuito_label')
                for label in circuit_labels:
                    prefix = f'circ_{label}_'
                    MedicionUCA.objects.create(
                        equipo_intervenido=ei,
                        circuito=label,
                        baja_p_antes=request.POST.get(f'{prefix}baja_antes') or None,
                        baja_p_despues=request.POST.get(f'{prefix}baja_despues') or None,
                        alta_p_antes=request.POST.get(f'{prefix}alta_antes') or None,
                        alta_p_despues=request.POST.get(f'{prefix}alta_despues') or None,
                    )
            else:
                MedicionSplit.objects.create(
                    equipo_intervenido=ei,
                    temp_sumin_antes=request.POST.get('temp_sumin_antes') or None,
                    temp_sumin_despues=request.POST.get('temp_sumin_despues') or None,
                    temp_retorno_antes=request.POST.get('temp_retorno_antes') or None,
                    temp_retorno_despues=request.POST.get('temp_retorno_despues') or None,
                )

            obs_texto = request.POST.get('observacion', '').strip()
            Observacion.objects.create(equipo_intervenido=ei, texto=obs_texto)

        return redirect('operations:formulario_orden', orden_id=orden.pk)


# ─────────────────────────────────────────────────────────
# ActualizarActividadesView: guarda el checklist de actividades
# ─────────────────────────────────────────────────────────
class ActualizarActividadesView(LoginRequiredMixin, View):
    """POST: actualiza el checklist (preventivo) o texto libre (correctivo)."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)

        if orden.tipo == TipoMantenimiento.PREVENTIVO:
            marcadas = set(request.POST.getlist('actividad_marcada'))
            for act in orden.actividades.all():
                act.marcada = str(act.pk) in marcadas
                act.save(update_fields=['marcada'])
        else:
            texto = request.POST.get('actividades_texto', '')
            # Para correctivos guardamos el texto como una única actividad
            orden.actividades.all().delete()
            if texto.strip():
                Actividad.objects.create(orden=orden, texto=texto, marcada=True)

        return redirect('operations:formulario_orden', orden_id=orden.pk)


# ─────────────────────────────────────────────────────────
# FinalizarOrdenView: cierra la orden y genera PDF
# ─────────────────────────────────────────────────────────
class FinalizarOrdenView(LoginRequiredMixin, View):
    """POST: cierra la orden, genera y guarda el PDF."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)
        orden.marcar_cerrado()
        return redirect('operations:orden_cerrada', orden_id=orden.pk)


# ─────────────────────────────────────────────────────────
# OrdenCerradaView: confirmación de cierre
# ─────────────────────────────────────────────────────────
class OrdenCerradaView(LoginRequiredMixin, View):
    def get(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user)
        minutos = duracion_minutos(orden.hora_inicio, orden.hora_fin)
        return render(request, 'operations/orden_cerrada.html', {
            'orden': orden,
            'minutos': minutos,
            'alerta_corto': es_duracion_sospechosa(minutos),
        })


# ─────────────────────────────────────────────────────────
# PDFOrdenView: genera el PDF FT-GM-41
# ─────────────────────────────────────────────────────────
class PDFOrdenView(LoginRequiredMixin, View):
    """Genera y sirve el PDF de la orden en formato FT-GM-41."""

    def get(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id)
        equipos_intervenidos = orden.equipos_intervenidos.prefetch_related(
            'mediciones_uca', 'medicion_split', 'observacion'
        ).all()
        actividades = orden.actividades.all()

        context = {
            'orden': orden,
            'equipo': orden.equipo,
            'equipos_intervenidos': equipos_intervenidos,
            'actividades': actividades,
            'fecha': orden.hora_fin or orden.hora_inicio,
            'es_preventivo': orden.tipo == TipoMantenimiento.PREVENTIVO,
        }

        template = get_template('operations/reporte_pdf_aa.html')
        html = template.render(context)

        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result, link_callback=link_callback)

        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            filename = f"FT-GM-41_{orden.radicado}_{context['fecha'].strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response

        return HttpResponse('Error al generar PDF', status=500)
