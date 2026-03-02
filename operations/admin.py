from django.contrib import admin
from .models import OrdenServicio, EquipoIntervenido, MedicionUCA, MedicionSplit, Actividad, Observacion


class EquipoIntervenidoInline(admin.TabularInline):
    model = EquipoIntervenido
    extra = 0
    show_change_link = True


class ActividadInline(admin.TabularInline):
    model = Actividad
    extra = 0


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('id', 'radicado', 'tipo', 'equipo', 'tecnico', 'fecha', 'hora_inicio', 'hora_fin', 'estado')
    list_filter = ('tipo', 'estado', 'fecha')
    search_fields = ('radicado', 'equipo__nombre', 'tecnico__username', 'cliente_nombre')
    readonly_fields = ('hora_inicio', 'hora_fin', 'pdf_path')
    inlines = [EquipoIntervenidoInline, ActividadInline]
    date_hierarchy = 'fecha'


@admin.register(EquipoIntervenido)
class EquipoIntervenidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_equipo', 'tipo_equipo', 'marca', 'modelo', 'orden')
    search_fields = ('nombre_equipo', 'marca', 'activo_fijo', 'orden__radicado')
    list_filter = ('tipo_equipo',)


@admin.register(MedicionUCA)
class MedicionUCAAdmin(admin.ModelAdmin):
    list_display = ('id', 'equipo_intervenido', 'circuito', 'baja_p_antes', 'alta_p_antes')


@admin.register(MedicionSplit)
class MedicionSplitAdmin(admin.ModelAdmin):
    list_display = ('id', 'equipo_intervenido', 'temp_sumin_antes', 'temp_retorno_antes')


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden', 'marcada', 'texto')
    list_filter = ('marcada',)
