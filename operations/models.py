from django.db import models
from django.conf import settings
from inventory.models import EquipoAA


class TipoMantenimiento(models.TextChoices):
    PREVENTIVO = 'MP', 'Mantenimiento Preventivo Tipo A'
    CORRECTIVO = 'MC', 'Mantenimiento Correctivo'


class EstadoOrden(models.TextChoices):
    ABIERTO = 'abierto', 'Abierto'
    CERRADO = 'cerrado', 'Cerrado'


class OrdenServicio(models.Model):
    """
    Documento de intervención (equivale a FT-GM-41).
    Solo los Preventivos (MP) bloquean nuevas órdenes.
    Los correctivos (MC) pueden coexistir.
    """
    equipo = models.ForeignKey(
        EquipoAA, on_delete=models.PROTECT, related_name='ordenes'
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ordenes_servicio'
    )
    tipo = models.CharField(
        max_length=2, choices=TipoMantenimiento.choices,
        verbose_name='Tipo de mantenimiento'
    )
    radicado = models.CharField(
        max_length=20,
        help_text='Ej: MP9167 o MC1234',
        verbose_name='Radicado No.'
    )
    # Datos del encabezado / orden de servicio
    cliente_nombre = models.CharField(max_length=200, verbose_name='Cliente')
    dir_cliente = models.CharField(max_length=300, blank=True, verbose_name='Dir. Cliente')
    num_orden = models.CharField(max_length=50, blank=True, verbose_name='No. Orden de Servicio')
    fecha = models.DateField(verbose_name='Fecha')
    mes = models.CharField(max_length=20, blank=True, verbose_name='Mes')

    hora_inicio = models.DateTimeField()
    hora_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=10, choices=EstadoOrden.choices, default=EstadoOrden.ABIERTO
    )
    pdf_path = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'Orden de Servicio'
        verbose_name_plural = 'Órdenes de Servicio'
        ordering = ['-hora_inicio']

    def __str__(self):
        return f'{self.radicado} — {self.equipo} — {self.tecnico}'

    def duracion_minutos(self):
        if not self.hora_fin:
            return None
        delta = self.hora_fin - self.hora_inicio
        return round(delta.total_seconds() / 60, 1)

    @property
    def cerrado(self):
        return self.estado == EstadoOrden.CERRADO

    def marcar_cerrado(self):
        from django.utils import timezone
        self.estado = EstadoOrden.CERRADO
        if not self.hora_fin:
            self.hora_fin = timezone.now()
        self.save()


class EquipoIntervenido(models.Model):
    """
    Detalle de cada equipo de AA intervenido en una OrdenServicio.
    Una orden puede incluir múltiples equipos.
    """
    orden = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name='equipos_intervenidos'
    )
    nombre_equipo = models.CharField(max_length=200, help_text='Ej: UCA 1, UMA 2')
    ubicacion = models.CharField(max_length=200, blank=True)
    tipo_equipo = models.CharField(max_length=20, blank=True, help_text='SPLIT, CASSETTE, PISO TECHO, etc.')
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    capacidad = models.CharField(max_length=50, blank=True)
    refrigerante = models.CharField(max_length=20, blank=True)
    voltaje = models.CharField(max_length=50, blank=True)
    corriente_l1 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    corriente_l2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    corriente_l3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    amperaje_l1 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    amperaje_l2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    amperaje_l3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    fases = models.CharField(max_length=50, blank=True, help_text='Ej: 3 PH 60HZ')
    tipo_correa = models.CharField(max_length=50, blank=True, help_text='Ej: BX38')
    activo_fijo = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Equipo Intervenido'
        verbose_name_plural = 'Equipos Intervenidos'
        ordering = ['id']

    def __str__(self):
        return f'{self.nombre_equipo} — Orden {self.orden.radicado}'


class MedicionUCA(models.Model):
    """
    Mediciones de presión por circuito para equipos UCA.
    Un equipo puede tener circuito A y/o B según num_circuitos del EquipoAA.
    """
    class Circuito(models.TextChoices):
        A = 'A', 'Circuito A'
        B = 'B', 'Circuito B'

    equipo_intervenido = models.ForeignKey(
        EquipoIntervenido, on_delete=models.CASCADE, related_name='mediciones_uca'
    )
    circuito = models.CharField(max_length=1, choices=Circuito.choices)
    baja_p_antes = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       verbose_name='Baja presión Antes (PSI)')
    baja_p_despues = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                         verbose_name='Baja presión Después (PSI)')
    alta_p_antes = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                       verbose_name='Alta presión Antes (PSI)')
    alta_p_despues = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                         verbose_name='Alta presión Después (PSI)')

    class Meta:
        verbose_name = 'Medición UCA'
        verbose_name_plural = 'Mediciones UCA'
        unique_together = ['equipo_intervenido', 'circuito']

    def __str__(self):
        return f'Circuito {self.circuito} — {self.equipo_intervenido}'


class MedicionSplit(models.Model):
    """Mediciones de temperatura para equipos UMA / SPLIT."""
    equipo_intervenido = models.OneToOneField(
        EquipoIntervenido, on_delete=models.CASCADE, related_name='medicion_split'
    )
    temp_sumin_antes = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                           verbose_name='Temp. Suministro Antes (°C)')
    temp_sumin_despues = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                             verbose_name='Temp. Suministro Después (°C)')
    temp_retorno_antes = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                             verbose_name='Temp. Retorno Antes (°C)')
    temp_retorno_despues = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                                               verbose_name='Temp. Retorno Después (°C)')

    class Meta:
        verbose_name = 'Medición Split/UMA'
        verbose_name_plural = 'Mediciones Split/UMA'

    def __str__(self):
        return f'Temperaturas — {self.equipo_intervenido}'


ACTIVIDADES_PREVENTIVO = [
    'Lavado de evaporadores y condensadores',
    'Revisión y limpieza de drenaje de bandeja evaporador',
    'Revisión y ajuste de correas, ventiladores, poleas y tornillería',
    'Revisión y limpieza de contactos y cajas eléctricas',
    'Revisión y limpieza de filtros de AA',
    'Revisión de fuga de refrigerante y aceite',
    'Revisión, limpieza y engrase de rodamientos',
    'Revisión funcionamiento de resistencia',
    'Revisión de temperaturas de evap. y condensación',
    'Revisión de amperajes y voltajes de equipos',
]


class Actividad(models.Model):
    """Ítem del checklist de actividades realizadas en una orden."""
    orden = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name='actividades'
    )
    texto = models.CharField(max_length=500)
    marcada = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['id']

    def __str__(self):
        return self.texto


class Observacion(models.Model):
    """Observaciones libres por equipo intervenido."""
    equipo_intervenido = models.OneToOneField(
        EquipoIntervenido, on_delete=models.CASCADE, related_name='observacion'
    )
    texto = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Observación'
        verbose_name_plural = 'Observaciones'

    def __str__(self):
        return f'Obs. — {self.equipo_intervenido}'
