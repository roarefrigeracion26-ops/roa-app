from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.views import View
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from xhtml2pdf import pisa
from django.contrib import messages
import io
import json

SPANISH_MONTHS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

from inventory.models import EquipoAA
from .models import (
    OrdenServicio, EquipoIntervenido, MedicionUCA, MedicionSplit,
    MedicionCondensadoraRack, Actividad, Observacion, TipoMantenimiento, EstadoOrden
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
    MedicionUCAForm, MedicionSplitForm, MedicionCondensadoraRackForm,
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
# NuevaOrdenClienteView: Creación de Preventivo (MP) por Tienda
# ─────────────────────────────────────────────────────────
from inventory.models import Cliente
from .forms import NuevaOrdenClienteForm

class NuevaOrdenClienteView(LoginRequiredMixin, View):
    """Formulario para iniciar un Preventivo (MP) a nivel de toda la Tienda/Cliente."""
    def get(self, request, cliente_id):
        cliente = get_object_or_404(Cliente, pk=cliente_id, activo=True)
        # Bloquear si ya hay preventivo abierto (el técnico no puede tener 2 al tiempo)
        preventivo_abierto = obtener_preventivo_abierto(request.user)
        if preventivo_abierto:
            return render(request, 'operations/bloqueo_preventivo.html', {
                'preventivo_abierto': preventivo_abierto,
                'cliente_bloqueo': cliente, # Usamos cliente en vez de equipo para el contexto
            })
            
        # Sugerir el último radicado + 1
        ultima_orden = OrdenServicio.objects.filter(tipo='MP').order_by('-radicado').first()
        sug_numero = ""
        if ultima_orden:
            import re
            m = re.search(r'\d+', ultima_orden.radicado)
            if m and m.group():
                sug_numero = str(int(m.group()) + 1)

        form = NuevaOrdenClienteForm(initial={
            'cliente_nombre': cliente.nombre,
            'dir_cliente': cliente.dir_cliente,
            'radicado_numero': sug_numero,
            'fecha': timezone.localdate(),
            'mes': SPANISH_MONTHS.get(timezone.localdate().month, ''),
        })
        return render(request, 'operations/nueva_orden.html', {
            'cliente': cliente,
            'es_mp_tienda': True,
            'form': form,
        })

    def post(self, request, cliente_id):
        cliente = get_object_or_404(Cliente, pk=cliente_id, activo=True)
        form = NuevaOrdenClienteForm(request.POST)
        if form.is_valid():
            try:
                tipo = form.cleaned_data['tipo']
                radicado = form.get_radicado()
                orden = iniciar_orden(
                    tecnico=request.user,
                    tipo=tipo,
                    radicado=radicado,
                    cliente_nombre=form.cleaned_data['cliente_nombre'],
                    dir_cliente=form.cleaned_data.get('dir_cliente', ''),
                    fecha=form.cleaned_data['fecha'],
                    mes=form.cleaned_data.get('mes', ''),
                    cliente=cliente,
                    equipo=None # Un MP de tienda no se amarra a un equipo en concreto
                )
                return redirect('operations:formulario_orden', orden_id=orden.pk)
            except ValueError as e:
                return render(request, 'operations/bloqueo_preventivo.html', {
                    'preventivo_abierto': obtener_preventivo_abierto(request.user),
                    'cliente_bloqueo': cliente,
                    'error': str(e),
                })
            except IntegrityError:
                return render(request, 'operations/nueva_orden.html', {
                    'cliente': cliente,
                    'es_mp_tienda': True,
                    'form': form,
                    'error_radicado': f'El radicado {radicado} ya existe. Usa otro número.',
                })
        return render(request, 'operations/nueva_orden.html', {
            'cliente': cliente,
            'es_mp_tienda': True,
            'form': form,
        })


# ─────────────────────────────────────────────────────────
# NuevaOrdenView: GET form para Correctivos (MC)
# ─────────────────────────────────────────────────────────
class NuevaOrdenView(LoginRequiredMixin, View):
    """Formulario para elegir tipo, ingresar radicado y datos del encabezado (Histórico por Equipo)."""
    def get(self, request, equipo_id):
        equipo = get_object_or_404(EquipoAA, pk=equipo_id, activo=True)
        # Sugerir el último radicado + 1 para MC
        ultima_orden = OrdenServicio.objects.filter(tipo='MC').order_by('-radicado').first()
        sug_numero = ""
        if ultima_orden:
            import re
            m = re.search(r'\d+', ultima_orden.radicado)
            if m and m.group():
                sug_numero = str(int(m.group()) + 1)

        form = NuevaOrdenForm(initial={
            'cliente_nombre': equipo.cliente.nombre,
            'dir_cliente': equipo.cliente.dir_cliente,
            'radicado_numero': sug_numero,
            'fecha': timezone.localdate(),
            'mes': SPANISH_MONTHS.get(timezone.localdate().month, ''),
            'tipo': 'MC' # Sugerimos MC por defecto al entrar por equipo
        })
        return render(request, 'operations/nueva_orden.html', {
            'equipo': equipo,
            'es_mp_tienda': False,
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
                    tipo=tipo,
                    radicado=radicado,
                    cliente_nombre=form.cleaned_data['cliente_nombre'],
                    dir_cliente=form.cleaned_data.get('dir_cliente', ''),
                    fecha=form.cleaned_data['fecha'],
                    mes=form.cleaned_data.get('mes', ''),
                    equipo=equipo,
                    cliente=equipo.cliente
                )
                return redirect('operations:formulario_orden', orden_id=orden.pk)
            except ValueError as e:
                return render(request, 'operations/bloqueo_preventivo.html', {
                    'preventivo_abierto': obtener_preventivo_abierto(request.user),
                    'equipo': equipo,
                    'error': str(e),
                })
            except IntegrityError:
                return render(request, 'operations/nueva_orden.html', {
                    'equipo': equipo,
                    'es_mp_tienda': False,
                    'form': form,
                    'error_radicado': f'El radicado {radicado} ya existe. Usa otro número.',
                })
        return render(request, 'operations/nueva_orden.html', {
            'equipo': equipo,
            'es_mp_tienda': False,
            'form': form,
        })


# ─────────────────────────────────────────────────────────
# FormularioOrdenView: formulario completo multi-equipo
# ─────────────────────────────────────────────────────────
def _build_formulario_context(orden, equipo_form=None):
    """Construye el contexto del formulario de intervención."""
    equipos_intervenidos = orden.equipos_intervenidos.prefetch_related(
        'mediciones_uca', 'medicion_split', 'medicion_condensadora_rack', 'observacion'
    ).all()
    actividades = orden.actividades.all()
    
    cliente = orden.cliente or (orden.equipo.cliente if orden.equipo else None)
    if cliente:
        from inventory.models import EquipoAA
        equipos_db = EquipoAA.objects.filter(cliente=cliente, activo=True)
        equipos_json = [{
            'id': eq.id,
            'nombre_equipo': eq.nombre,
            'ubicacion': eq.ubicacion,
            'tipo_equipo': eq.tipo_equipo,
            'marca': eq.marca,
            'modelo': eq.modelo,
            'capacidad': eq.capacidad,
            'refrigerante': eq.refrigerante,
            'voltaje': eq.voltaje,
            'fases': eq.fases,
            'tipo_correa': eq.tipo_correa,
            'activo_fijo': eq.activo_fijo,
        } for eq in equipos_db]
    else:
        equipos_db = []
        equipos_json = []

    equipos_pendientes = []
    for ei in equipos_intervenidos:
        pendiente = False
        tipo = ei.tipo_equipo
        if tipo == 'UCA':
            for uca in ei.mediciones_uca.all():
                if uca.baja_p_despues is None or uca.alta_p_despues is None:
                    pendiente = True
                    break
        elif tipo in ('UMA', 'SPLIT', 'OTRO'):
            ms = getattr(ei, 'medicion_split', None)
            if ms and (ms.temp_sumin_despues is None or ms.temp_retorno_despues is None):
                pendiente = True
        elif tipo == 'PAQUETE':
            for uca in ei.mediciones_uca.all():
                if uca.baja_p_despues is None or uca.alta_p_despues is None:
                    pendiente = True
                    break
            ms = getattr(ei, 'medicion_split', None)
            if ms and (ms.temp_sumin_despues is None or ms.temp_retorno_despues is None):
                pendiente = True
        elif tipo == 'CONDENSADORA_RACK':
            mr = getattr(ei, 'medicion_condensadora_rack', None)
            if mr and (mr.presion_entrada_despues is None or mr.temp_salida_despues is None):
                pendiente = True
        if pendiente:
            equipos_pendientes.append(ei)

    return {
        'orden': orden,
        'equipo': orden.equipo,
        'cliente': orden.cliente,
        'equipos_intervenidos': equipos_intervenidos,
        'equipos_pendientes': equipos_pendientes,
        'actividades': actividades,
        'equipo_form': equipo_form or EquipoIntervenidoForm(),
        'es_preventivo': orden.tipo == TipoMantenimiento.PREVENTIVO,
        'equipos_db': equipos_db,
        'equipos_json': equipos_json,
    }


def parse_decimal(val):
    """Convierte un valor a string decimal con punto. Retorna None si es vacío."""
    if not val:
        return None
    if isinstance(val, str):
        return val.replace(',', '.')
    return str(val)


def parse_int(val):
    """Convierte un valor a entero >= 0. Retorna None si es inválido o negativo."""
    if not val:
        return None
    try:
        v = int(val)
        return v if v >= 0 else None
    except (ValueError, TypeError):
        return None


class FormularioOrdenView(LoginRequiredMixin, View):
    """Formulario completo: actividades + equipos intervenidos + mediciones."""

    def get(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user)
        if orden.estado == EstadoOrden.CERRADO:
            return redirect('operations:orden_cerrada', orden_id=orden.pk)
        return render(request, 'operations/formulario_orden.html', _build_formulario_context(orden))



def _guardar_actividades_orden(request, orden):
    """Extrae las actividades del POST (checkboxes o texto) y las guarda en la orden."""
    if orden.tipo == TipoMantenimiento.PREVENTIVO:
        marcadas = set(request.POST.getlist('actividad_marcada'))
        for act in orden.actividades.all():
            act.marcada = str(act.pk) in marcadas
            act.save(update_fields=['marcada'])
    else:
        texto = request.POST.get('actividades_texto', '')
        orden.actividades.all().delete()
        if texto.strip():
            from operations.models import Actividad
            Actividad.objects.create(orden=orden, texto=texto, marcada=True)

# ─────────────────────────────────────────────────────────
# AgregarEquipoAntesView: agrega un EquipoIntervenido solo con mediciones iniciales
# ─────────────────────────────────────────────────────────
class AgregarEquipoAntesView(LoginRequiredMixin, View):
    """POST: agrega un equipo intervenido con mediciones ANTES. Las mediciones DESPUES se completan después."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)
        
        # Guardado automático de actividades
        _guardar_actividades_orden(request, orden)
        
        equipo_form = EquipoIntervenidoForm(request.POST)

        if equipo_form.is_valid():
            ei = equipo_form.save(commit=False)
            ei.orden = orden
            ei.save()

            # Save UCA (Pressures) — solo ANTES
            circuit_labels = request.POST.getlist('circuito_label')
            for label in circuit_labels:
                prefix = f'circ_{label}_'
                baja_a = parse_decimal(request.POST.get(f'{prefix}baja_antes'))
                alta_a = parse_decimal(request.POST.get(f'{prefix}alta_antes'))
                
                if baja_a or alta_a:
                    MedicionUCA.objects.update_or_create(
                        equipo_intervenido=ei,
                        circuito=label,
                        defaults={
                            'baja_p_antes': baja_a,
                            'alta_p_antes': alta_a,
                        }
                    )

            # Save Split (Temperatures) — solo ANTES
            t_sum_a = parse_decimal(request.POST.get('temp_sumin_antes'))
            t_ret_a = parse_decimal(request.POST.get('temp_retorno_antes'))
            
            if t_sum_a or t_ret_a:
                MedicionSplit.objects.update_or_create(
                    equipo_intervenido=ei,
                    defaults={
                        'temp_sumin_antes': t_sum_a,
                        'temp_retorno_antes': t_ret_a,
                    }
                )

            # Save Condensadora Rack — solo ANTES
            cr_corriente_l1 = parse_decimal(request.POST.get('cr_corriente_l1_antes'))
            cr_corriente_l2 = parse_decimal(request.POST.get('cr_corriente_l2_antes'))
            cr_corriente_l3 = parse_decimal(request.POST.get('cr_corriente_l3_antes'))
            cr_presion = parse_decimal(request.POST.get('cr_presion_entrada_antes'))
            cr_temp = parse_decimal(request.POST.get('cr_temp_salida_antes'))

            if any([cr_corriente_l1, cr_corriente_l2, cr_corriente_l3, cr_presion, cr_temp]):
                MedicionCondensadoraRack.objects.update_or_create(
                    equipo_intervenido=ei,
                    defaults={
                        'corriente_l1_antes': cr_corriente_l1,
                        'corriente_l2_antes': cr_corriente_l2,
                        'corriente_l3_antes': cr_corriente_l3,
                        'presion_entrada_antes': cr_presion,
                        'temp_salida_antes': cr_temp,
                    }
                )

            return redirect('operations:formulario_orden', orden_id=orden.pk)

        return render(request, 'operations/formulario_orden.html', _build_formulario_context(orden, equipo_form=equipo_form))


# ─────────────────────────────────────────────────────────
# CompletarEquipoDespuesView: actualiza mediciones DESPUES de un equipo intervenido
# ─────────────────────────────────────────────────────────
class CompletarEquipoDespuesView(LoginRequiredMixin, View):
    """POST: actualiza las mediciones DESPUES de un equipo ya intervenido."""

    def post(self, request, orden_id, equipo_id):
        try:
            orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user, estado=EstadoOrden.ABIERTO)
            ei = get_object_or_404(EquipoIntervenido, pk=equipo_id, orden=orden)
            _guardar_actividades_orden(request, orden)

            # Update UCA — solo DESPUES
            circuit_labels = request.POST.getlist('circuito_label')
            for label in circuit_labels:
                prefix = f'circ_{label}_'
                baja_d = parse_decimal(request.POST.get(f'{prefix}baja_despues'))
                alta_d = parse_decimal(request.POST.get(f'{prefix}alta_despues'))

                if baja_d or alta_d:
                    MedicionUCA.objects.update_or_create(
                        equipo_intervenido=ei,
                        circuito=label,
                        defaults={
                            'baja_p_despues': baja_d,
                            'alta_p_despues': alta_d,
                        }
                    )

            # Update Split — solo DESPUES
            t_sum_d = parse_decimal(request.POST.get('temp_sumin_despues'))
            t_ret_d = parse_decimal(request.POST.get('temp_retorno_despues'))

            if t_sum_d or t_ret_d:
                MedicionSplit.objects.update_or_create(
                    equipo_intervenido=ei,
                    defaults={
                        'temp_sumin_despues': t_sum_d,
                        'temp_retorno_despues': t_ret_d,
                    }
                )

            # Update Condensadora Rack — solo DESPUES
            cr_corriente_l1 = parse_decimal(request.POST.get('cr_corriente_l1_despues'))
            cr_corriente_l2 = parse_decimal(request.POST.get('cr_corriente_l2_despues'))
            cr_corriente_l3 = parse_decimal(request.POST.get('cr_corriente_l3_despues'))
            cr_presion = parse_decimal(request.POST.get('cr_presion_entrada_despues'))
            cr_temp = parse_decimal(request.POST.get('cr_temp_salida_despues'))
            cr_temp_amb = parse_decimal(request.POST.get('cr_temp_ambiente_despues'))
            cr_total = request.POST.get('cr_total_abanicos')
            cr_operativos = request.POST.get('cr_abanicos_operativos')

            cr_total_i = parse_int(cr_total)
            cr_operativos_i = parse_int(cr_operativos)

            if any([cr_corriente_l1, cr_corriente_l2, cr_corriente_l3, cr_presion, cr_temp, cr_temp_amb,
                    cr_total_i is not None, cr_operativos_i is not None]):
                MedicionCondensadoraRack.objects.update_or_create(
                    equipo_intervenido=ei,
                    defaults={
                        'corriente_l1_despues': cr_corriente_l1,
                        'corriente_l2_despues': cr_corriente_l2,
                        'corriente_l3_despues': cr_corriente_l3,
                        'presion_entrada_despues': cr_presion,
                        'temp_salida_despues': cr_temp,
                        'temp_ambiente_despues': cr_temp_amb,
                        'total_abanicos': cr_total_i,
                        'abanicos_operativos': cr_operativos_i,
                    }
                )

            envio_texto = request.POST.get('observacion', '').strip()
            if envio_texto:
                Observacion.objects.update_or_create(
                    equipo_intervenido=ei,
                    defaults={'texto': envio_texto}
                )

            messages.success(request, 'Mediciones guardadas correctamente.')
        except Exception:
            messages.error(request, 'Error al guardar las mediciones. Revisa los datos e intenta de nuevo.')
        return redirect('operations:formulario_orden', orden_id=orden.pk)


# ─────────────────────────────────────────────────────────
# FinalizarOrdenView: cierra la orden y genera PDF
# ─────────────────────────────────────────────────────────
class FinalizarOrdenView(LoginRequiredMixin, View):
    """POST: cierra la orden, genera y guarda el PDF."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user)
        if orden.estado == EstadoOrden.ABIERTO:
            ctx = _build_formulario_context(orden)
            if ctx['equipos_pendientes']:
                messages.warning(request, 'Completa las Mediciones Finales (Después) de todos los equipos antes de finalizar.')
                return redirect('operations:formulario_orden', orden_id=orden.pk)
            _guardar_actividades_orden(request, orden)
            orden.marcar_cerrado()
        return redirect('operations:orden_cerrada', orden_id=orden.pk)


# ─────────────────────────────────────────────────────────
# CancelarOrdenView: elimina un preventivo abierto para empezar de nuevo
# ─────────────────────────────────────────────────────────
class CancelarOrdenView(LoginRequiredMixin, View):
    """POST: elimina el preventivo MP abierto si se seleccionó la tienda equivocada."""

    def post(self, request, orden_id):
        orden = get_object_or_404(OrdenServicio, pk=orden_id, tecnico=request.user)
        if orden.tipo == TipoMantenimiento.PREVENTIVO and orden.estado == EstadoOrden.ABIERTO:
            orden.delete()
        return redirect('inventory:clientes')


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
        if orden.tecnico != request.user and not request.user.is_supervisor:
            return HttpResponse('No autorizado', status=403)
        equipos_intervenidos = orden.equipos_intervenidos.prefetch_related(
            'mediciones_uca', 'medicion_split', 'medicion_condensadora_rack', 'observacion'
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
