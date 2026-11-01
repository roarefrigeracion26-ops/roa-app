from django.contrib import admin
from django.utils.html import format_html
from .models import Empresa, Cliente, EquipoAA


class ClienteInline(admin.TabularInline):
    model = Cliente
    extra = 1
    fields = ('codigo', 'nombre', 'dir_cliente', 'activo')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'logo_preview', 'nombre', 'nit', 'total_sedes_count', 'activo', 'creado_en')
    list_filter = ('activo',)
    search_fields = ('nombre', 'nit')
    inlines = [ClienteInline]

    @admin.display(description='Logo')
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 38px; max-width: 65px; object-fit: contain; border-radius: 4px;" />',
                obj.logo.url
            )
        return '—'

    @admin.display(description='Total Sedes')
    def total_sedes_count(self, obj):
        return obj.sedes.count() if obj.pk else 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'codigo', 'nombre', 'dir_cliente', 'activo')
    list_filter = ('empresa', 'activo')
    search_fields = ('nombre', 'codigo', 'dir_cliente', 'empresa__nombre')
    autocomplete_fields = ['empresa']



@admin.register(EquipoAA)
class EquipoAAAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'cliente', 'tipo_equipo', 'num_circuitos', 'marca', 'modelo', 'activo')
    list_filter = ('tipo_equipo', 'cliente', 'activo', 'refrigerante')
    search_fields = ('nombre', 'id_qr', 'marca', 'modelo', 'activo_fijo', 'cliente__nombre')
    autocomplete_fields = ['cliente']
    fieldsets = (
        ('Identificación', {'fields': ('id_qr', 'cliente', 'nombre', 'ubicacion', 'activo')}),
        ('Tipo y Circuitos', {'fields': ('tipo_equipo', 'num_circuitos')}),
        ('Datos Técnicos', {'fields': ('marca', 'modelo', 'capacidad', 'refrigerante', 'voltaje', 'activo_fijo')}),
    )
