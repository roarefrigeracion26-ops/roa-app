from django.db import models


class Empresa(models.Model):
    """Empresa cliente a la que ROA presta servicios (ej. Olímpica S.A., Éxito, etc.)."""
    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(
        upload_to='empresas/logos/', blank=True, null=True,
        verbose_name='Logo de la empresa',
        help_text='Logo corporativo para mostrar en las tarjetas de selección.'
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """Sede, tienda o sucursal donde están instalados los equipos de AA."""
    empresa = models.ForeignKey(
        Empresa, on_delete=models.PROTECT, related_name='sedes',
        null=True, blank=True
    )
    codigo = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Código de sede/tienda',
        help_text='Opcional. Ej: 1059 para Olímpica o alfanumérico.'
    )
    nombre = models.CharField(max_length=200)
    dir_cliente = models.CharField(max_length=300, blank=True, verbose_name='Dirección')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sede / Tienda'
        verbose_name_plural = 'Sedes / Tiendas'
        ordering = ['empresa', 'nombre']

    def __str__(self):
        prefijo = f'[{self.codigo}] ' if self.codigo else ''
        empresa_nom = f' — {self.empresa.nombre}' if self.empresa else ''
        return f'{prefijo}{self.nombre}{empresa_nom}'



class TipoEquipo(models.TextChoices):
    UCA = 'UCA', 'UCA — Unidad Condensadora'
    UMA = 'UMA', 'UMA — Unidad Manejadora'
    SPLIT = 'SPLIT', 'Split'
    CASSETTE = 'CASSETTE', 'Cassette'
    PISO_TECHO = 'PISO_TECHO', 'Piso Techo'
    PAQUETE = 'PAQUETE', 'Paquete'
    CONDENSADORA_RACK = 'CONDENSADORA_RACK', 'Condensadora Rack Refrigeración'
    OTRO = 'OTRO', 'Otro'


class EquipoAA(models.Model):
    """
    Activo de Aire Acondicionado. El QR (cuando se habilite) contiene id_qr.
    tipo_equipo determina qué mediciones se registran:
      - UCA → mediciones de presión por circuito (hasta num_circuitos)
      - UMA / SPLIT → mediciones de temperatura suministro/retorno
    """
    id_qr = models.CharField(
        max_length=100, unique=True, db_index=True, blank=True, null=True,
        help_text='ID único en el código QR (opcional por ahora)'
    )
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='equipos'
    )
    nombre = models.CharField(max_length=200, help_text='Ej: UCA 1, UMA 2, SPLIT 1')
    ubicacion = models.CharField(max_length=200, blank=True, help_text='Ej: AZOTEA, CUARTO RETORNO')
    tipo_equipo = models.CharField(
        max_length=20, choices=TipoEquipo.choices, default=TipoEquipo.UCA
    )
    num_circuitos = models.PositiveSmallIntegerField(
        default=1,
        help_text='Número de circuitos (1 o 2). Aplica a UCA para determinar circuitos A y B.'
    )
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    capacidad = models.CharField(max_length=50, blank=True, help_text='Ej: 25TR')
    refrigerante = models.CharField(
        max_length=20, blank=True, help_text='R410A, R22, R32, R407C, etc.'
    )
    voltaje = models.CharField(max_length=50, blank=True, help_text='Ej: 220 V')
    fases = models.CharField(max_length=50, blank=True, help_text='Ej: 3 PH 60HZ')
    tipo_correa = models.CharField(max_length=50, blank=True, help_text='Ej: BX38')
    activo_fijo = models.CharField(max_length=50, blank=True, help_text='Número de activo fijo')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Equipo de AA'
        verbose_name_plural = 'Equipos de AA'
        ordering = ['cliente', 'nombre']

    def __str__(self):
        return f'{self.nombre} — {self.cliente.nombre}'

    @property
    def es_uca(self):
        return self.tipo_equipo == TipoEquipo.UCA

    @property
    def circuitos(self):
        """Lista de etiquetas de circuito según num_circuitos."""
        labels = ['A', 'B']
        return labels[:self.num_circuitos]
