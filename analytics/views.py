import csv
from datetime import datetime
from io import StringIO

from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from users.mixins import SupervisorRequiredMixin
from inventory.models import Tienda, Rack
from operations.models import RegistroActividad


def _get_cerrados_queryset(request):
    """Aplica los mismos filtros que el dashboard (tienda, equipo, fecha)."""
    tienda_id = request.GET.get('tienda', '').strip()
    rack_id = request.GET.get('rack', '').strip()
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

    cerrados = RegistroActividad.objects.all().select_related('rack', 'rack__tienda', 'tecnico')

    if tienda_id:
        cerrados = cerrados.filter(rack__tienda_id=tienda_id)
    if rack_id:
        cerrados = cerrados.filter(rack_id=rack_id)
    if fecha_inicio:
        cerrados = cerrados.filter(hora_inicio__date__gte=fecha_inicio)
    if fecha_fin:
        cerrados = cerrados.filter(hora_inicio__date__lte=fecha_fin)
    return cerrados.order_by('-hora_inicio')


class DashboardView(SupervisorRequiredMixin, TemplateView):
    """Dashboard premium: Visitas totales, MTTR, filtros por equipo y rediseño visual."""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        request = self.request

        # Filtros (GET)
        tienda_id = request.GET.get('tienda', '').strip()
        rack_id = request.GET.get('rack', '').strip()
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

        # Queryset base para el contador (Todas las visitas iniciadas)
        visitas = RegistroActividad.objects.all().select_related('rack', 'rack__tienda')
        actividades_qs = visitas.select_related('tecnico')

        # Filtro para MTTR (Solo cerradas)
        cerrados_para_mttr = RegistroActividad.objects.filter(
            cerrado=True, hora_fin__isnull=False
        )

        # Aplicar filtros
        if tienda_id:
            visitas = visitas.filter(rack__tienda_id=tienda_id)
            actividades_qs = actividades_qs.filter(rack__tienda_id=tienda_id)
            cerrados_para_mttr = cerrados_para_mttr.filter(rack__tienda_id=tienda_id)
        if rack_id:
            visitas = visitas.filter(rack_id=rack_id)
            actividades_qs = actividades_qs.filter(rack_id=rack_id)
            cerrados_para_mttr = cerrados_para_mttr.filter(rack_id=rack_id)
        if fecha_inicio:
            visitas = visitas.filter(hora_inicio__date__gte=fecha_inicio)
            actividades_qs = actividades_qs.filter(hora_inicio__date__gte=fecha_inicio)
            cerrados_para_mttr = cerrados_para_mttr.filter(hora_fin__date__gte=fecha_inicio)
        if fecha_fin:
            visitas = visitas.filter(hora_inicio__date__lte=fecha_fin)
            actividades_qs = actividades_qs.filter(hora_inicio__date__lte=fecha_fin)
            cerrados_para_mttr = cerrados_para_mttr.filter(hora_fin__date__lte=fecha_fin)

        # Título y conteo
        if fecha_inicio and fecha_fin:
            if fecha_inicio == fecha_fin:
                context['titulo_contador'] = f'Visitas ({fecha_inicio.strftime("%d/%m/%Y")})'
            else:
                context['titulo_contador'] = f'Visitas ({fecha_inicio.strftime("%d/%m/%Y")} – {fecha_fin.strftime("%d/%m/%Y")})'
            context['visitas_conteo'] = visitas.count()
        else:
            titulo = 'Visitas Totales'
            if rack_id:
                try:
                    rack_obj = Rack.objects.get(pk=rack_id)
                    titulo = f'Visitas: {rack_obj.id_qr}'
                except Rack.DoesNotExist:
                    pass
            elif tienda_id:
                try:
                    tienda_obj = Tienda.objects.get(pk=tienda_id)
                    titulo = f'Visitas: {tienda_obj.nombre}'
                except Tienda.DoesNotExist:
                    pass
            context['titulo_contador'] = titulo
            context['visitas_conteo'] = visitas.count()

        # MTTR
        if cerrados_para_mttr.exists():
            duracion_expr = ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=DurationField()
            )
            agg = cerrados_para_mttr.annotate(duracion=duracion_expr).aggregate(promedio=Avg('duracion'))
            promedio_td = agg.get('promedio')
            context['mttr_minutos'] = round(promedio_td.total_seconds() / 60, 1) if promedio_td else None
        else:
            context['mttr_minutos'] = None

        context['historial'] = actividades_qs.order_by('-hora_inicio')[:100]

        # Contexto para selectores
        tiendas = list(Tienda.objects.all().order_by('nombre'))
        for t in tiendas: t.pk_str = str(t.pk)
        context['tiendas'] = tiendas

        racks_qs = Rack.objects.all()
        if tienda_id: racks_qs = racks_qs.filter(tienda_id=tienda_id)
        racks = list(racks_qs.order_by('id_qr'))
        for r in racks: r.pk_str = str(r.pk)
        context['racks'] = racks
        
        context['tienda_seleccionada'] = tienda_id
        context['rack_seleccionado'] = rack_id
        context['fecha_inicio_seleccionada'] = fecha_inicio_str
        context['fecha_fin_seleccionada'] = fecha_fin_str
        return context


class ExportReportesView(SupervisorRequiredMixin, View):
    """Exporta el historial de reportes en CSV."""
    def get(self, request):
        cerrados = _get_cerrados_queryset(request)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Fecha / Hora inicio', 'Técnico', 'Rack', 'Tienda', 'Tipo', 'Estado', 'Duración (min)'])
        for r in cerrados:
            tecnico = (r.tecnico.get_full_name() or r.tecnico.username) if r.tecnico_id else ''
            writer.writerow([
                r.hora_inicio.strftime('%d/%m/%Y %H:%M') if r.hora_inicio else '',
                tecnico,
                r.rack.id_qr if r.rack_id else '',
                r.rack.tienda.nombre if r.rack_id else '',
                r.get_tipo_actividad_display(),
                'Cerrado' if r.cerrado else 'Abierto',
                r.duracion_minutos() if r.hora_fin else '—',
            ])
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="visitas_sgmr.csv"'
        return response
