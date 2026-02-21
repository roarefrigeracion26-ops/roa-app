import csv
from datetime import datetime
from io import StringIO

from django.db.models import Avg, F, ExpressionWrapper, DurationField
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from users.mixins import SupervisorRequiredMixin
from inventory.models import Tienda
from operations.models import RegistroActividad


def _get_cerrados_queryset(request):
    """Aplica los mismos filtros que el dashboard (tienda, fecha_inicio, fecha_fin)."""
    tienda_id = request.GET.get('tienda', '').strip()
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

    cerrados = RegistroActividad.objects.filter(
        cerrado=True, hora_fin__isnull=False
    ).select_related('rack', 'rack__tienda', 'tecnico')

    if tienda_id:
        cerrados = cerrados.filter(rack__tienda_id=tienda_id)
    if fecha_inicio:
        cerrados = cerrados.filter(hora_fin__date__gte=fecha_inicio)
    if fecha_fin:
        cerrados = cerrados.filter(hora_fin__date__lte=fecha_fin)
    return cerrados.order_by('-hora_fin')


class DashboardView(SupervisorRequiredMixin, TemplateView):
    """Dashboard de supervisión: escaneadas hoy, MTTR, historial con filtros por tienda y fecha."""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        request = self.request

        # Filtros (GET): tienda y rango de fechas (inicio - fin)
        tienda_id = request.GET.get('tienda', '').strip()
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
        # Si solo hay una fecha, usar ese día como inicio y fin
        if fecha_inicio and not fecha_fin:
            fecha_fin = fecha_inicio
        elif fecha_fin and not fecha_inicio:
            fecha_inicio = fecha_fin
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio

        # Queryset base: intervenciones cerradas
        cerrados = RegistroActividad.objects.filter(
            cerrado=True, hora_fin__isnull=False
        ).select_related('rack', 'rack__tienda', 'tecnico')

        if tienda_id:
            cerrados = cerrados.filter(rack__tienda_id=tienda_id)
        if fecha_inicio:
            cerrados = cerrados.filter(hora_fin__date__gte=fecha_inicio)
        if fecha_fin:
            cerrados = cerrados.filter(hora_fin__date__lte=fecha_fin)

        # Primera tarjeta: "Escaneadas hoy" sin filtro, o "Intervenciones" en el rango
        if fecha_inicio and fecha_fin:
            if fecha_inicio == fecha_fin:
                context['titulo_contador'] = f'Intervenciones ({fecha_inicio.strftime("%d/%m/%Y")})'
            else:
                context['titulo_contador'] = f'Intervenciones ({fecha_inicio.strftime("%d/%m/%Y")} – {fecha_fin.strftime("%d/%m/%Y")})'
            context['escaneadas_hoy'] = cerrados.count()
        else:
            context['titulo_contador'] = 'Escaneadas hoy'
            context['escaneadas_hoy'] = cerrados.filter(hora_fin__date=hoy).count()

        # MTTR sobre el conjunto filtrado
        if cerrados.exists():
            duracion_expr = ExpressionWrapper(
                F('hora_fin') - F('hora_inicio'),
                output_field=DurationField()
            )
            agg = cerrados.annotate(duracion=duracion_expr).aggregate(promedio=Avg('duracion'))
            promedio_td = agg.get('promedio')
            context['mttr_minutos'] = round(promedio_td.total_seconds() / 60, 1) if promedio_td else None
        else:
            context['mttr_minutos'] = None

        # Historial: mismos filtros, últimos 100
        context['historial'] = cerrados.order_by('-hora_fin')[:100]

        # Para el formulario de filtros
        context['tiendas'] = Tienda.objects.all().order_by('nombre')
        context['tienda_seleccionada'] = tienda_id
        context['fecha_inicio_seleccionada'] = fecha_inicio_str
        context['fecha_fin_seleccionada'] = fecha_fin_str
        return context


class ExportReportesView(SupervisorRequiredMixin, View):
    """Exporta el historial de reportes (con los mismos filtros del dashboard) en CSV."""
    def get(self, request):
        cerrados = _get_cerrados_queryset(request)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            'Fecha / Hora fin', 'Técnico', 'Rack', 'Tienda', 'Tipo', 'Duración (min)'
        ])
        for r in cerrados:
            tecnico = (r.tecnico.get_full_name() or r.tecnico.username) if r.tecnico_id else ''
            writer.writerow([
                r.hora_fin.strftime('%d/%m/%Y %H:%M') if r.hora_fin else '',
                tecnico,
                r.rack.id_qr if r.rack_id else '',
                r.rack.tienda.nombre if r.rack_id else '',
                r.get_tipo_actividad_display(),
                r.duracion_minutos() if r.hora_fin else '',
            ])
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reportes_sgmr.csv"'
        return response
