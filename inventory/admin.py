from django.contrib import admin
from .models import Cliente, EquipoAA


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'dir_cliente', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'dir_cliente')


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
