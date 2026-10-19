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

    def test_subir_foto_ajax_devuelve_json_y_html(self):
        respuesta = self.client.post(
            self.url_subir(), {'fotos': imagen_subida()}, HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/json')
        data = respuesta.json()
        self.assertTrue(data['ok'])
        self.assertIn('foto-bloque', data['html'])
        self.assertIn(f'foto-bloque-{self.ei.pk}-antes', data['html'])
        self.assertIn('csrfmiddlewaretoken', data['html'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['max'], MAX_FOTOS_POR_MOMENTO)
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei, momento='ANTES').count(), 1)

    def test_subir_foto_ajax_sin_archivos_devuelve_json_error(self):
        respuesta = self.client.post(self.url_subir(), {}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200)
        data = respuesta.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['count'], 0)
        self.assertTrue(data['message'])

    def test_subir_foto_ajax_en_maximo_devuelve_json_error(self):
        for i in range(MAX_FOTOS_POR_MOMENTO):
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei, momento='ANTES',
                imagen=SimpleUploadedFile(f'{i}.jpg', b'x', content_type='image/jpeg'),
            )
        respuesta = self.client.post(
            self.url_subir(), {'fotos': imagen_subida()}, HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(respuesta.status_code, 200)
        data = respuesta.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['count'], MAX_FOTOS_POR_MOMENTO)
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei, momento='ANTES').count(), MAX_FOTOS_POR_MOMENTO)

    def test_subir_foto_ajax_archivo_invalido_devuelve_json_error(self):
        archivo = SimpleUploadedFile('nota.txt', b'no imagen', content_type='text/plain')
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [archivo]}, HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(respuesta.status_code, 200)
        data = respuesta.json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)

    def test_subir_foto_ajax_parcial_incluye_error_en_message(self):
        archivo = SimpleUploadedFile('nota.txt', b'no imagen', content_type='text/plain')
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [imagen_subida(), archivo]},
            HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(respuesta.status_code, 200)
        data = respuesta.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertIn('Se agregaron 1 foto', data['message'])
        self.assertIn('no es una imagen', data['message'])

    def test_subir_foto_sin_header_parcial_emite_error_y_exito(self):
        archivo = SimpleUploadedFile('nota.txt', b'no imagen', content_type='text/plain')
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [imagen_subida(), archivo]}, follow=True,
        )
        self.assertEqual(respuesta.redirect_chain[-1][1], 302)
        mensajes = list(respuesta.context['messages'])
        self.assertTrue(any('Se agregaron 1 foto' in m.message for m in mensajes))
        self.assertTrue(any('no es una imagen' in m.message and m.level_tag == 'error' for m in mensajes))

    def test_subir_foto_sin_header_maximo_usa_warning(self):
        for i in range(MAX_FOTOS_POR_MOMENTO):
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei, momento='ANTES',
                imagen=SimpleUploadedFile(f'{i}.jpg', b'x', content_type='image/jpeg'),
            )
        respuesta = self.client.post(self.url_subir(), {'fotos': [imagen_subida()]}, follow=True)
        mensajes = list(respuesta.context['messages'])
        self.assertTrue(any('Máximo' in m.message and m.level_tag == 'warning' for m in mensajes))

    def test_subir_foto_sin_header_sigue_redirigiendo(self):
        respuesta = self.client.post(self.url_subir(), {'fotos': imagen_subida()})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 1)

    def test_eliminar_foto_ajax_devuelve_json(self):
        self.client.post(self.url_subir(), {'fotos': imagen_subida()})
        foto = FotoEquipo.objects.get(equipo_intervenido=self.ei)
        respuesta = self.client.post(self.url_eliminar(foto), HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/json')
        data = respuesta.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['max'], MAX_FOTOS_POR_MOMENTO)
        self.assertIn(f'foto-bloque-{self.ei.pk}-antes', data['html'])
        self.assertIn('csrfmiddlewaretoken', data['html'])
        self.assertFalse(FotoEquipo.objects.filter(pk=foto.pk).exists())

    def test_eliminar_foto_sin_header_sigue_redirigiendo(self):
        self.client.post(self.url_subir(), {'fotos': imagen_subida()})
        foto = FotoEquipo.objects.get(equipo_intervenido=self.ei)
        respuesta = self.client.post(self.url_eliminar(foto))
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(FotoEquipo.objects.filter(pk=foto.pk).exists())

    def test_formulario_tiene_contenedor_estable_y_forms_de_fotos(self):
        self.client.post(self.url_subir(), {'fotos': imagen_subida()})
        respuesta = self.client.get(reverse('operations:formulario_orden', args=[self.orden.pk]))
        html = respuesta.content.decode()
        self.assertIn('id="equipos-intervenidos"', html)
        self.assertIn('data-foto-bloque', html)
        self.assertIn('foto-delete-form', html)
        self.assertIn('mostrarMensajeBloque', html)

    def test_formulario_renderiza_bloques_de_fotos(self):
        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        respuesta = self.client.get(reverse('operations:formulario_orden', args=[self.orden.pk]))
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn('col-md-6', html)
        self.assertIn('foto-bloque-head--antes', html)
        self.assertIn('foto-bloque-head--despues', html)
        self.assertIn('1/3', html)

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

    def test_genera_pdf_con_fotos(self):
        from django.test import RequestFactory
        from operations.views import PDFOrdenView

        self.client.post(self.url_subir(), {'fotos': [imagen_subida()]})
        request = RequestFactory().get('/')
        request.user = self.tecnico
        respuesta = PDFOrdenView().get(request, orden_id=self.orden.pk)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))

    def test_meta_ordering_estable(self):
        self.assertEqual(FotoEquipo._meta.ordering, ['creada_en', 'id'])

    def test_orden_estable_con_misma_fecha(self):
        from datetime import timedelta
        from django.utils import timezone

        base = timezone.now()
        f1 = FotoEquipo.objects.create(equipo_intervenido=self.ei, momento=MomentoFoto.ANTES)
        f2 = FotoEquipo.objects.create(equipo_intervenido=self.ei, momento=MomentoFoto.ANTES)
        FotoEquipo.objects.filter(pk=f1.pk).update(creada_en=base)
        FotoEquipo.objects.filter(pk=f2.pk).update(creada_en=base)

        ids = list(FotoEquipo.objects.filter(equipo_intervenido=self.ei)
                   .values_list('pk', flat=True))
        self.assertEqual(ids, sorted([f1.pk, f2.pk]))
