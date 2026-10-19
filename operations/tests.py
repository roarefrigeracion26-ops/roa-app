import io
import os
import re
import tempfile
import threading
from datetime import date
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
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


def imagen_gif_subida(nombre='animacion.gif'):
    """Devuelve un SimpleUploadedFile GIF válido pero no permitido."""
    buffer = io.BytesIO()
    Image.new('P', (10, 10)).save(buffer, format='GIF')
    buffer.seek(0)
    return SimpleUploadedFile(nombre, buffer.read(), content_type='image/gif')


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

    def test_validar_archivo_rechaza_gif(self):
        with self.assertRaisesMessage(
            ValidationError, 'Formato no soportado. Usa JPG, PNG o WebP.',
        ):
            images.validar_archivo(imagen_gif_subida())


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

    def test_limite_no_se_excede_con_multiples_archivos(self):
        self._crear_foto(self.ei, MomentoFoto.ANTES)
        archivos = [imagen_subida(f'{i}.jpg') for i in range(5)]
        self.client.post(self.url_subir(), {'fotos': archivos})
        self.assertLessEqual(
            FotoEquipo.objects.filter(
                equipo_intervenido=self.ei, momento=MomentoFoto.ANTES,
            ).count(),
            MAX_FOTOS_POR_MOMENTO,
        )

    def test_clean_rechaza_crear_cuando_la_etapa_esta_llena(self):
        for i in range(MAX_FOTOS_POR_MOMENTO):
            self._crear_foto(self.ei, MomentoFoto.ANTES)
        foto = FotoEquipo(
            equipo_intervenido=self.ei, momento=MomentoFoto.ANTES,
            imagen=imagen_subida('nueva.jpg'),
        )
        with self.assertRaisesMessage(ValidationError, 'Máximo'):
            foto.full_clean()

    def test_clean_rechaza_mover_foto_a_etapa_llena(self):
        for i in range(MAX_FOTOS_POR_MOMENTO):
            self._crear_foto(self.ei, MomentoFoto.DESPUES)
        foto = self._crear_foto(self.ei, MomentoFoto.ANTES)

        foto.momento = MomentoFoto.DESPUES
        with self.assertRaisesMessage(ValidationError, 'Máximo'):
            foto.full_clean()

    def test_clean_permite_mover_foto_si_hay_espacio(self):
        for i in range(MAX_FOTOS_POR_MOMENTO - 1):
            self._crear_foto(self.ei, MomentoFoto.DESPUES)
        foto = self._crear_foto(self.ei, MomentoFoto.ANTES)

        foto.momento = MomentoFoto.DESPUES
        foto.full_clean()
        self.assertEqual(foto.momento, MomentoFoto.DESPUES)

    def test_rechaza_archivo_invalido(self):
        archivo = SimpleUploadedFile('nota.txt', b'no imagen', content_type='text/plain')
        self.client.post(self.url_subir(), {'fotos': [archivo]})
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)

    def test_rechaza_imagen_gif(self):
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [imagen_gif_subida()]},
            HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(FotoEquipo.objects.filter(equipo_intervenido=self.ei).count(), 0)
        self.assertFalse(respuesta.json()['ok'])
        self.assertIn('Formato no soportado', respuesta.json()['message'])

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

    def test_registra_warning_si_el_storage_falla_al_borrar(self):
        foto = self._crear_foto(self.ei, MomentoFoto.ANTES)
        storage = foto.imagen.storage

        with patch.object(storage, 'delete', side_effect=OSError('disco caido')):
            with self.assertLogs('operations.signals', level='WARNING') as registro:
                with self.captureOnCommitCallbacks(execute=True):
                    foto.delete()

        self.assertFalse(FotoEquipo.objects.filter(pk=foto.pk).exists())
        self.assertTrue(any('disco caido' in linea for linea in registro.output))

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

    def _request(self):
        from django.test import RequestFactory
        request = RequestFactory().get('/')
        request.user = self.tecnico
        return request

    def _crear_foto(self, ei, momento):
        return FotoEquipo.objects.create(
            equipo_intervenido=ei,
            momento=momento,
            imagen=imagen_subida(f'{momento}.jpg'),
        )

    def test_pdf_falla_si_una_foto_no_carga(self):
        from operations.views import PDFOrdenView

        self._crear_foto(self.ei, MomentoFoto.ANTES)

        with patch('operations.views.urlopen', side_effect=OSError('boom')) as descarga, \
                patch('xhtml2pdf.files.NetworkFileUri.get_data', return_value=None), \
                patch('django.core.files.storage.FileSystemStorage.url',
                      return_value='https://r2.example/foto.jpg'), \
                patch('django.contrib.staticfiles.storage.StaticFilesStorage.url',
                      return_value='static/image/roa-logo.jpeg'), \
                self.assertLogs('operations.views', level='ERROR') as registro:
            respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)

        self.assertEqual(respuesta.status_code, 500)
        html = respuesta.content.decode()
        self.assertIn('Reintentar', html)
        self.assertIn('No se pudo generar el PDF', html)
        self.assertTrue(descarga.called)
        self.assertEqual(descarga.call_args.kwargs['timeout'], 20)
        self.assertTrue(any('no se pudo descargar' in linea for linea in registro.output))

    def test_pdf_descarga_fotos_remotas_y_limpia_temporales(self):
        from operations.views import PDFOrdenView

        self._crear_foto(self.ei, MomentoFoto.ANTES)

        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), (10, 20, 30)).save(buffer, format='JPEG')
        contenido = buffer.getvalue()

        class Respuesta:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return contenido

        creados = []
        original = tempfile.NamedTemporaryFile

        def named_temporary_file(*args, **kwargs):
            archivo = original(*args, **kwargs)
            creados.append(archivo.name)
            return archivo

        with patch('operations.views.urlopen', return_value=Respuesta()) as descarga, \
                patch('operations.views.tempfile.NamedTemporaryFile',
                      side_effect=named_temporary_file), \
                patch('django.core.files.storage.FileSystemStorage.url',
                      return_value='https://r2.example/foto.jpg'), \
                patch('django.contrib.staticfiles.storage.StaticFilesStorage.url',
                      return_value='static/image/roa-logo.jpeg'):
            respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))
        self.assertEqual(descarga.call_args.kwargs['timeout'], 20)
        self.assertTrue(creados)
        for ruta in creados:
            self.assertFalse(os.path.exists(ruta))

    def test_pdf_dos_fotos_misma_url_remota_no_falla(self):
        from operations.views import PDFOrdenView

        self._crear_foto(self.ei, MomentoFoto.ANTES)
        self._crear_foto(self.ei, MomentoFoto.ANTES)

        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), (10, 20, 30)).save(buffer, format='JPEG')
        contenido = buffer.getvalue()

        class Respuesta:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return contenido

        with patch('operations.views.urlopen', return_value=Respuesta()) as descarga, \
                patch('django.core.files.storage.FileSystemStorage.url',
                      return_value='https://r2.example/misma.jpg'), \
                patch('django.contrib.staticfiles.storage.StaticFilesStorage.url',
                      return_value='static/image/roa-logo.jpeg'):
            respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))

    def test_pdf_incrusta_todas_las_fotos(self):
        from pypdf import PdfReader
        from operations.views import PDFOrdenView

        def contar_imagenes(respuesta):
            lector = PdfReader(io.BytesIO(respuesta.content))
            return sum(len(pagina.images) for pagina in lector.pages)

        # Referencia: la plantilla PDF incluye el logo estatico de ROA, por lo
        # que incluso un PDF sin fotos incrusta imagenes. Se mide el total con
        # cero fotos y se comprueba que el incremento sea igual al numero de
        # fotos; no se fija un total absoluto porque depende de elementos
        # estaticos (logo) ajenos a las fotos.
        sin_fotos = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
        self.assertEqual(sin_fotos.status_code, 200)
        total_sin_fotos = contar_imagenes(sin_fotos)

        # Colores distintos: xhtml2pdf deduplica imagenes con bytes identicos
        # en un mismo XObject, lo que ocultaria fotos logicamente distintas.
        colores = [(200, 10, 10), (10, 200, 10), (10, 10, 200)]
        for indice, color in enumerate(colores):
            momento = MomentoFoto.ANTES if indice < 2 else MomentoFoto.DESPUES
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei,
                momento=momento,
                imagen=imagen_subida(f'incrusta-{indice}.jpg', color=color),
            )

        respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))

        total = contar_imagenes(respuesta)
        self.assertEqual(total - total_sin_fotos, len(colores))

    def test_pdf_sin_fotos_no_falla_ni_incluye_registro(self):
        from pypdf import PdfReader
        from operations.views import PDFOrdenView

        respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF-'))

        lector = PdfReader(io.BytesIO(respuesta.content))
        self.assertGreaterEqual(len(lector.pages), 1)
        # Sin fotos solo debe quedar el logo estatico del encabezado.
        total = sum(len(pagina.images) for pagina in lector.pages)
        self.assertGreaterEqual(total, 1)
        texto = '\n'.join(pagina.extract_text() or '' for pagina in lector.pages)
        self.assertNotIn('REGISTRO FOTOGR', texto)

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


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(prefix='roa-test-media-admin-'),
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class AdminFotosTests(TestCase):
    def setUp(self):
        self.admin = Tecnico.objects.create_superuser(
            username='admin', email='admin@example.com', password='clave123',
        )
        self.tecnico = Tecnico.objects.create_user(username='tec', password='clave123')
        self.cliente = Cliente.objects.create(nombre='Tienda Uno')
        self.equipo = EquipoAA.objects.create(
            cliente=self.cliente, nombre='UCA 1', tipo_equipo='UCA',
        )
        self.orden = OrdenServicio.objects.create(
            equipo=self.equipo, cliente=self.cliente, tecnico=self.tecnico,
            tipo='MC', radicado='MC0001', cliente_nombre='Tienda Uno',
            fecha=date.today(), hora_inicio=timezone.now(),
        )
        self.ei = EquipoIntervenido.objects.create(orden=self.orden, nombre_equipo='UCA 1')
        request = RequestFactory().get('/admin/')
        request.user = self.admin
        self.request = request
        self.site = AdminSite()

    def _crear_foto(self, momento=MomentoFoto.ANTES):
        return FotoEquipo.objects.create(
            equipo_intervenido=self.ei, momento=momento,
            imagen=imagen_subida(f'{momento}.jpg'),
        )

    def test_admin_standalone_no_permite_agregar(self):
        from operations.admin import FotoEquipoAdmin

        admin_fotos = FotoEquipoAdmin(FotoEquipo, self.site)
        self.assertFalse(admin_fotos.has_add_permission(self.request))

    def test_inline_no_permite_agregar(self):
        from operations.admin import FotoEquipoInline

        inline = FotoEquipoInline(FotoEquipo, self.site)
        self.assertFalse(inline.has_add_permission(self.request, None))
        self.assertFalse(inline.has_add_permission(self.request, obj=self.ei))

    def test_admin_y_inline_marcan_imagen_readonly_al_editar(self):
        from operations.admin import FotoEquipoAdmin, FotoEquipoInline

        foto = self._crear_foto()
        admin_fotos = FotoEquipoAdmin(FotoEquipo, self.site)
        inline = FotoEquipoInline(FotoEquipo, self.site)

        campos_admin = admin_fotos.get_readonly_fields(self.request, foto)
        campos_inline = inline.get_readonly_fields(self.request, foto)
        self.assertIn('imagen', campos_admin)
        self.assertIn('creada_en', campos_admin)
        self.assertIn('imagen', campos_inline)
        self.assertIn('creada_en', campos_inline)

    def test_borrar_desde_admin_elimina_el_archivo(self):
        self.client.force_login(self.admin)
        foto = self._crear_foto()
        nombre = foto.imagen.name
        storage = foto.imagen.storage
        url = reverse('admin:operations_fotoequipo_delete', args=[foto.pk])

        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(url, {'post': 'yes'})

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(FotoEquipo.objects.filter(pk=foto.pk).exists())
        self.assertFalse(storage.exists(nombre))


@skipUnless(connection.vendor == 'postgresql', 'select_for_update requiere PostgreSQL')
@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(prefix='roa-test-media-concurrente-'),
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class LimiteConcurrenteTests(TransactionTestCase):
    def setUp(self):
        self.tecnico = Tecnico.objects.create_user(username='tec', password='clave123')
        self.cliente = Cliente.objects.create(nombre='Tienda Uno')
        self.equipo = EquipoAA.objects.create(
            cliente=self.cliente, nombre='UCA 1', tipo_equipo='UCA',
        )
        self.orden = OrdenServicio.objects.create(
            equipo=self.equipo, cliente=self.cliente, tecnico=self.tecnico,
            tipo='MC', radicado='MC0001', cliente_nombre='Tienda Uno',
            fecha=date.today(), hora_inicio=timezone.now(),
        )
        self.ei = EquipoIntervenido.objects.create(orden=self.orden, nombre_equipo='UCA 1')
        FotoEquipo.objects.create(
            equipo_intervenido=self.ei, momento=MomentoFoto.ANTES,
            imagen=imagen_subida('existente.jpg'),
        )

    def test_dos_subidas_concurrentes_no_pasan_de_3(self):
        url = reverse('operations:subir_fotos', args=[self.orden.pk, self.ei.pk, 'ANTES'])
        barrera = threading.Barrier(2)
        errores = []

        def subir(inicio):
            try:
                cliente = Client()
                cliente.force_login(self.tecnico)
                barrera.wait(timeout=10)
                respuesta = cliente.post(url, {
                    'fotos': [imagen_subida(f'hilo-{inicio}-{i}.jpg') for i in range(3)],
                })
                if respuesta.status_code != 302:
                    errores.append(respuesta.status_code)
            except Exception as error:
                errores.append(error)
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=subir, args=(i,)) for i in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=30)

        self.assertFalse(any(hilo.is_alive() for hilo in hilos))
        self.assertEqual(errores, [])
        self.assertLessEqual(
            FotoEquipo.objects.filter(
                equipo_intervenido=self.ei, momento=MomentoFoto.ANTES,
            ).count(),
            MAX_FOTOS_POR_MOMENTO,
        )


class ContrasteGoldTests(TestCase):
    GOLD_AA = '#8B6914'
    GOLD_ANTERIOR = '#B8860B'

    @staticmethod
    def _lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    @classmethod
    def _ratio_blanco(cls, hexcolor):
        r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
        luminancia = (
            0.2126 * cls._lin(r) + 0.7152 * cls._lin(g) + 0.0722 * cls._lin(b)
        )
        return 1.05 / (luminancia + 0.05)

    def test_gold_cumple_contraste_aa_sobre_blanco(self):
        ratio = self._ratio_blanco(self.GOLD_AA)
        self.assertGreaterEqual(
            ratio, 4.5, f'{self.GOLD_AA} alcanza {ratio:.2f}:1 sobre blanco'
        )

    def _contenido_template(self, nombre):
        ruta = settings.BASE_DIR / 'templates' / 'operations' / nombre
        return ruta.read_text(encoding='utf-8')

    @staticmethod
    def _regla_css(contenido, selector):
        patron = re.escape(selector) + r'\s*\{([^}]*)\}'
        coincidencias = re.findall(patron, contenido)
        if len(coincidencias) != 1:
            raise AssertionError(
                f'Se esperaba una regla CSS para {selector}, se hallaron '
                f'{len(coincidencias)}'
            )
        return coincidencias[0]

    @staticmethod
    def _valor_declaracion(regla, propiedad):
        patron = rf'(?:^|;)\s*{re.escape(propiedad)}\s*:\s*([^;]+)'
        coincidencia = re.search(patron, regla)
        if not coincidencia:
            raise AssertionError(f'Falta {propiedad} en la regla: {regla!r}')
        return coincidencia.group(1).strip().lower()

    def test_templates_de_fotos_no_usan_gold_anterior(self):
        for nombre in ('formulario_orden.html', 'reporte_pdf_aa.html'):
            with self.subTest(template=nombre):
                self.assertNotIn(self.GOLD_ANTERIOR, self._contenido_template(nombre))

    def test_formulario_usa_gold_aa_en_cabecera_y_tab(self):
        contenido = self._contenido_template('formulario_orden.html')

        cabecera = self._regla_css(contenido, '.foto-bloque-head')
        self.assertEqual(self._valor_declaracion(cabecera, 'color'), '#fff')

        despues = self._regla_css(contenido, '.foto-bloque-head--despues')
        self.assertEqual(
            self._valor_declaracion(despues, 'background'), '#8b6914'
        )

        split = self._regla_css(contenido, '.tab-tipo.active-split')
        self.assertEqual(self._valor_declaracion(split, 'background'), '#8b6914')
        self.assertNotIn('var(--roa-gold)', split)

    def test_pdf_usa_gold_aa_en_barra_y_etiquetas(self):
        contenido = self._contenido_template('reporte_pdf_aa.html')

        barra = self._regla_css(contenido, '.section-bar')
        self.assertEqual(self._valor_declaracion(barra, 'color'), '#fff')

        self.assertRegex(
            contenido,
            r'<div class="section-bar"[^>]*background:\s*#8B6914[^>]*>'
            r'\s*REGISTRO FOTOGRÁFICO',
            'La barra REGISTRO FOTOGRÁFICO debe declarar background:#8B6914',
        )

        for etiqueta in ('ANTES', 'DESPUÉS'):
            with self.subTest(etiqueta=etiqueta):
                self.assertRegex(
                    contenido,
                    rf'<div style="[^"]*color:\s*#8B6914;[^"]*">\s*'
                    rf'{etiqueta}\s*</div>',
                    f'La etiqueta {etiqueta} debe usar #8B6914',
                )
