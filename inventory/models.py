from django.db import models


class Cliente(models.Model):
    """Cliente / sucursal donde están instalados los equipos de AA."""
    nombre = models.CharField(max_length=200)
    dir_cliente = models.CharField(max_length=300, blank=True, verbose_name='Dirección')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class TipoEquipo(models.TextChoices):
    UCA = 'UCA', 'UCA — Unidad Condensadora'
    UMA = 'UMA', 'UMA — Unidad Manejadora'
    SPLIT = 'SPLIT', 'Split'
    CASSETTE = 'CASSETTE', 'Cassette'
    PISO_TECHO = 'PISO_TECHO', 'Piso Techo'
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
