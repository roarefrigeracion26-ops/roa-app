from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import FotoEquipo


@receiver(post_delete, sender=FotoEquipo)
def borrar_archivo_foto(sender, instance, **kwargs):
    """Borra el archivo del storage al eliminar la fila, diferido al commit."""
    if not instance.imagen:
        return
    nombre = instance.imagen.name
    storage = instance.imagen.storage

    def _borrar():
        try:
            storage.delete(nombre)
        except Exception:
            pass

    transaction.on_commit(_borrar)
