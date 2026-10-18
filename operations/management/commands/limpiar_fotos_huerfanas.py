"""
Reconcilia las fotos almacenadas con los registros en la base de datos.

Lista (o elimina) los archivos bajo el prefijo `fotos/` que ya no tienen un
registro `FotoEquipo` asociado. Útil tras fallos a mitad de una subida.

Uso:
    python manage.py limpiar_fotos_huerfanas
    python manage.py limpiar_fotos_huerfanas --borrar
"""
import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from operations.models import FotoEquipo

PREFIX = 'fotos/'


class Command(BaseCommand):
    help = 'Lista o elimina archivos de fotos sin registro en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--borrar',
            action='store_true',
            help='Elimina los archivos huérfanos. Sin esta opción solo se listan.',
        )

    def handle(self, *args, **options):
        borrar = options['borrar']
        referenciados = set(FotoEquipo.objects.values_list('imagen', flat=True))
        huerfanos = [nombre for nombre in self._listar_objetos() if nombre not in referenciados]

        if not huerfanos:
            self.stdout.write(self.style.SUCCESS('No se encontraron fotos huérfanas.'))
            return

        for nombre in huerfanos:
            if borrar:
                try:
                    default_storage.delete(nombre)
                    self.stdout.write(f'Eliminado: {nombre}')
                except Exception as error:
                    self.stderr.write(f'No se pudo eliminar {nombre}: {error}')
            else:
                self.stdout.write(f'Huérfano: {nombre}')

        accion = 'Eliminados' if borrar else 'Encontrados'
        self.stdout.write(self.style.WARNING(f'{accion}: {len(huerfanos)} archivo(s).'))

    def _listar_objetos(self):
        """Lista las claves bajo `fotos/`, sirva R2 (S3) o disco local."""
        bucket = getattr(default_storage, 'bucket', None)
        if bucket is not None:
            return [objeto.key for objeto in bucket.objects.filter(Prefix=PREFIX)]

        raiz = os.path.join(settings.MEDIA_ROOT, PREFIX)
        nombres = []
        for dirpath, _, archivos in os.walk(raiz):
            for archivo in archivos:
                ruta = os.path.join(dirpath, archivo)
                nombres.append(os.path.relpath(ruta, settings.MEDIA_ROOT).replace('\\', '/'))
        return nombres
