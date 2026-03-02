"""
Lógica de negocio para órdenes de servicio SGMAA.
Regla clave: SOLO el Preventivo (MP) bloquea nuevas tareas.
El Correctivo (MC) puede coexistir con otros documentos abiertos.
"""
from django.utils import timezone
from .models import OrdenServicio, TipoMantenimiento, EstadoOrden, ACTIVIDADES_PREVENTIVO, Actividad


def tecnico_tiene_preventivo_abierto(tecnico):
    """True si el técnico tiene un Preventivo (MP) sin cerrar."""
    return OrdenServicio.objects.filter(
        tecnico=tecnico,
        tipo=TipoMantenimiento.PREVENTIVO,
        estado=EstadoOrden.ABIERTO,
    ).exists()


def obtener_preventivo_abierto(tecnico):
    """Devuelve la OrdenServicio preventiva abierta o None."""
    return OrdenServicio.objects.filter(
        tecnico=tecnico,
        tipo=TipoMantenimiento.PREVENTIVO,
        estado=EstadoOrden.ABIERTO,
    ).select_related('equipo', 'equipo__cliente').first()


def iniciar_orden(tecnico, equipo, tipo, radicado, cliente_nombre, dir_cliente,
                  num_orden, fecha, mes):
    """
    Crea una OrdenServicio.
    Lanza ValueError solo si tipo==MP y ya hay un preventivo abierto.
    Correctivos NUNCA bloquean.
    """
    if tipo == TipoMantenimiento.PREVENTIVO and tecnico_tiene_preventivo_abierto(tecnico):
        raise ValueError(
            'Tienes un Preventivo Tipo A abierto. Debes finalizarlo antes de iniciar otro mantenimiento preventivo.'
        )
    orden = OrdenServicio.objects.create(
        equipo=equipo,
        tecnico=tecnico,
        tipo=tipo,
        radicado=radicado,
        cliente_nombre=cliente_nombre,
        dir_cliente=dir_cliente,
        num_orden=num_orden,
        fecha=fecha,
        mes=mes,
        hora_inicio=timezone.now(),
        estado=EstadoOrden.ABIERTO,
    )
    # Para preventivos, crear checklist predefinido
    if tipo == TipoMantenimiento.PREVENTIVO:
        Actividad.objects.bulk_create([
            Actividad(orden=orden, texto=texto, marcada=True)
            for texto in ACTIVIDADES_PREVENTIVO
        ])
    return orden


def duracion_minutos(hora_inicio, hora_fin):
    if not hora_fin:
        return None
    delta = hora_fin - hora_inicio
    return round(delta.total_seconds() / 60, 1)


def es_duracion_sospechosa(minutos, umbral_minutos=10):
    if minutos is None:
        return False
    return minutos < umbral_minutos
