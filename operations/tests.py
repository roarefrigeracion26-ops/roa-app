import io
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from inventory.models import Cliente, EquipoAA
from operations import images
from operations.models import (
    EstadoOrden, EquipoIntervenido, FotoEquipo, MomentoFoto,
    OrdenServicio, MAX_FOTOS_POR_MOMENTO,
)
from users.models import Tecnico


def imagen_subida(nombre='foto.jpg', tamano=(800, 600), color=(20, 40, 60)):
    """Devuelve un SimpleUploadedFile JPEG válido."""
    buffer = io.BytesIO()
    Image.new('RGB', tamano, color).save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(nombre, buffer.read(), content_type='image/jpeg')


class ImagenUnitTests(TestCase):
    def test_procesar_imagen_reduce_y_recomprime(self):
        original = imagen_subida('grande.jpg', tamano=(2400, 1800))
        resultado = images.procesar_imagen(original)

        img = Image.open(resultado)
        self.assertEqual(img.format, 'JPEG')
        self.assertLessEqual(max(img.size), images.MAX_LADO_PX)
        self.assertLess(resultado.size, original.size)

    def test_validar_archivo_rechaza_no_imagen(self):
        from django.core.exceptions import ValidationError
        archivo = SimpleUploadedFile('nota.txt', b'no soy una imagen', content_type='text/plain')
        with self.assertRaises(ValidationError):
            images.validar_archivo(archivo)

    def test_validar_archivo_acepta_imagen(self):
        images.validar_archivo(imagen_subida())


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(prefix='roa-test-media-'),
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class FotosViewsTests(TestCase):
    def setUp(self):
        self.tecnico = Tecnico.objects.create_user(username='tec', password='clave123')
        self.otro = Tecnico.objects.create_user(username='otro', password='clave123')
        self.cliente = Cliente.objects.create(nombre='Tienda Uno')
        self.equipo = EquipoAA.objects.create(cliente=self.cliente, nombre='UCA 1', tipo_equipo='UCA')
        self.orden = OrdenServicio.objects.create(
            equipo=self.equipo,
            cliente=self.cliente,
            tecnico=self.tecnico,
            tipo='MC',
            radicado='MC0001',
            cliente_nombre='Tienda Uno',
            fecha=date.today(),
            hora_inicio=timezone.now(),
        )
        self.ei = EquipoIntervenido.objects.create(orden=self.orden, nombre_equipo='UCA 1')
        self.client.force_login(self.tecnico)

    def url_subir(self, momento='ANTES'):
        return reverse('operations:subir_fotos', args=[self.orden.pk, self.ei.pk, momento])

    def url_eliminar(self, foto):
        return reverse('operations:eliminar_foto', args=[self.orden.pk, foto.pk])

    def test_sube_hasta_el_maximo(self):
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [imagen_subida(f'{i}.jpg') for i in range(MAX_FOTOS_POR_MOMENTO)]}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei, momento='ANTES').count(), MAX_FOTOS_POR_MOMENTO)

    def test_bloquea_cuando_ya_hay_maximo(self):
        for i in range(MAX_FOTOS_POR_MOMENTO):
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei, momento='ANTES',
                imagen=SimpleUploadedFile(f'{i}.jpg', b'x', content_type='image/jpeg'),
            )
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei, momento='ANTES').count(), MAX_FOTOS_POR_MOMENTO)

    def test_rechaza_archivo_invalido(self):
        archivo = SimpleUploadedFile('nota.txt', b'no imagen', content_type='text/plain')
        self.client.post(self.url_subir(), {'fotos': [archivo]})
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)

    def test_momento_invalido_no_crea(self):
        self.client.post(self.url_subir('NO_EXISTE'), {'fotos': [imagen_subida()]})
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)

    def test_otro_tecnico_no_autorizado(self):
        self.client.force_login(self.otro)
        respuesta = self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        self.assertEqual(respuesta.status_code, 403)

    def test_eliminar_foto_borra_archivo(self):
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        foto = FotoEquipo.objects.get(equipo_intervenido=self.ei)
        nombre = foto.imagen.name
        storage = foto.imagen.storage

        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url_eliminar(foto))

        self.assertFalse(FotoEquipo.objects.filter(pk=foto.pk).exists())
        self.assertFalse(storage.exists(nombre))

    def test_orden_cerrada_no_permite_subir(self):
        self.orden.estado = EstadoOrden.CERRADO
        self.orden.save(update_fields=['estado'])
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)

    def test_formulario_renderiza_bloques_de_fotos(self):
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        respuesta = self.client.get(reverse('operations:formulario_orden', args=[self.orden.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Fotos Antes')
        self.assertContains(respuesta, 'Fotos Después')
        self.assertContains(respuesta, '1/3')

    def test_plantilla_pdf_incluye_registro_fotografico(self):
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        ei = EquipoIntervenido.objects.get(pk=self.ei.pk)
        ei.fotos_antes = list(ei.fotos.filter(momento=MomentoFoto.ANTES))
        ei.fotos_despues = list(ei.fotos.filter(momento=MomentoFoto.DESPUES))

        from django.template.loader import get_template
        html = get_template('operations/reporte_pdf_aa.html').render({
            'orden': self.orden,
            'equipo': self.orden.equipo,
            'equipos_intervenidos': [ei],
            'actividades': [],
            'fecha': self.orden.hora_inicio,
            'es_preventivo': False,
        })
        self.assertIn('REGISTRO FOTOGRÁFICO', html)
        self.assertIn(ei.fotos_antes[0].imagen.url, html)
