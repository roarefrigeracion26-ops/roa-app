import csv
from datetime import datetime
from io import StringIO

from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from users.mixins import SupervisorRequiredMixin
from inventory.models import Cliente, EquipoAA
from operations.models import OrdenServicio, TipoMantenimiento, EstadoOrden


def _get_ordenes_queryset(request):
    """Aplica filtros del dashboard a las órdenes."""
    cliente_id = request.GET.get('cliente', '').strip()
    equipo_id = request.GET.get('equipo', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
    fecha_fin_str = request.GET.get('fecha_fin', '').strip()
    fecha_inicio = None
    fecha_fin = None
    try:
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    except ValueError:
        pass
    if fecha_inicio and not fecha_fin:
        fecha_fin = fecha_inicio
    elif fecha_fin and not fecha_inicio:
        fecha_inicio = fecha_fin
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        fecha_inicio, fecha_fin = fecha_fin, fecha_inicio

    qs = OrdenServicio.objects.all().select_related('equipo', 'equipo__cliente', 'tecnico')

    if cliente_id:
        qs = qs.filter(equipo__cliente_id=cliente_id)
    if equipo_id:
        qs = qs.filter(equipo_id=equipo_id)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if fecha_inicio:
        qs = qs.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__lte=fecha_fin)
    return qs.order_by('-hora_inicio')


class DashboardView(SupervisorRequiredMixin, TemplateView):
    """Dashboard SGMAA: historial de órdenes, MTTR correctivos, filtros."""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        cliente_id = request.GET.get('cliente', '').strip()
        equipo_id = request.GET.get('equipo', '').strip()
        tipo = request.GET.get('tipo', '').strip()
        fecha_inicio_str = request.GET.get('fecha_inicio', '').strip()
        fecha_fin_str = request.GET.get('fecha_fin', '').strip()

        ordenes = _get_ordenes_queryset(request)
        context['historial'] = ordenes[:100]
        context['total_ordenes'] = ordenes.count()

        # MTTR solo sobre correctivos cerrados
        correctivos_cerrados = OrdenServicio.objects.filter(
            tipo=TipoMantenimiento.CORRECTIVO,
            estado=EstadoOrden.CERRADO,
            hora_fin__isnull=False,
        )
        if cliente_id:
            correctivos_cerrados = correctivos_cerrados.filter(equipo__cliente_id=cliente_id)
        if equipo_id:
            correctivos_cerrados = correctivos_cerrados.filter(equipo_id=equipo_id)
        if correctivos_cerrados.exists():
            dur_expr = ExpressionWrapper(F('hora_fin') - F('hora_inicio'), output_field=DurationField())
            agg = correctivos_cerrados.annotate(dur=dur_expr).aggregate(promedio=Avg('dur'))
            td = agg.get('promedio')
            context['mttr_minutos'] = round(td.total_seconds() / 60, 1) if td else None
        else:
            context['mttr_minutos'] = None

        # Selectores
        clientes = list(Cliente.objects.filter(activo=True).order_by('nombre'))
        context['clientes'] = clientes
        equipos_qs = EquipoAA.objects.filter(activo=True)
        if cliente_id:
            equipos_qs = equipos_qs.filter(cliente_id=cliente_id)
        context['equipos'] = list(equipos_qs.order_by('nombre'))
        context['tipos'] = TipoMantenimiento.choices

        context['cliente_seleccionado'] = cliente_id
        context['equipo_seleccionado'] = equipo_id
        context['tipo_seleccionado'] = tipo
        context['fecha_inicio_seleccionada'] = fecha_inicio_str
        context['fecha_fin_seleccionada'] = fecha_fin_str
        return context


class ExportReportesView(SupervisorRequiredMixin, View):
    """Exporta el historial de órdenes en CSV."""
    def get(self, request):
        ordenes = _get_ordenes_queryset(request)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Radicado', 'Tipo', 'Fecha', 'Técnico', 'Cliente', 'Equipo', 'Estado', 'Duración (min)'])
        for o in ordenes:
            tecnico = (o.tecnico.get_full_name() or o.tecnico.username) if o.tecnico_id else ''
            writer.writerow([
                o.radicado,
                o.get_tipo_display(),
                o.fecha.strftime('%d/%m/%Y') if o.fecha else '',
                tecnico,
                o.cliente_nombre,
                o.equipo.nombre if o.equipo_id else '',
                o.get_estado_display(),
                o.duracion_minutos() if o.hora_fin else '—',
            ])
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="ordenes_sgmaa.csv"'
        return response
