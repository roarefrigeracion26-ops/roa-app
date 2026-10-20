from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from users.models import Tecnico


class LandingAssetsTests(SimpleTestCase):
    def test_assets_de_la_landing_existen(self):
        nombres = [
            'landing/hero.jpg',
            'landing/ofrecemos.jpg',
            'landing/clientes/exito.jpg',
            'landing/clientes/lasa.jpg',
            'landing/clientes/olimpica.jpg',
            'landing/clientes/bodytech.jpg',
            'landing/clientes/sao.jpg',
            'landing/iconos/montaje.png',
            'landing/iconos/mantenimiento.png',
            'landing/iconos/electricas.png',
        ]
        for nombre in nombres:
            with self.subTest(nombre=nombre):
                self.assertIsNotNone(finders.find(nombre), f'Falta {nombre}')


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class LandingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tecnico = Tecnico.objects.create_user(username='tec', password='clave123')

    def test_raiz_publica_muestra_hero(self):
        respuesta = self.client.get('/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Aire acondicionado y refrigeración para empresas')

    def test_raiz_ya_no_es_el_login(self):
        respuesta = self.client.get('/')
        self.assertNotContains(respuesta, 'id_username')

    def test_login_vive_en_ingresar(self):
        respuesta = self.client.get('/ingresar/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'id_username')

    def test_raiz_enlaza_al_login(self):
        respuesta = self.client.get('/')
        self.assertContains(respuesta, reverse('users:login'))

    def test_autenticado_ve_ir_al_sistema(self):
        self.client.force_login(self.tecnico)
        respuesta = self.client.get('/')
        self.assertContains(respuesta, 'Ir al sistema')
        self.assertNotContains(respuesta, 'Ingresar al sistema')

    def test_login_post_redirige_por_rol(self):
        respuesta = self.client.post('/ingresar/', {'username': 'tec', 'password': 'clave123'})
        self.assertRedirects(respuesta, reverse('inventory:clientes'))

    def test_login_tiene_volver_al_inicio(self):
        respuesta = self.client.get('/ingresar/')
        self.assertContains(respuesta, reverse('landing'))
        self.assertContains(respuesta, 'Volver al inicio')

    def test_login_muestra_errores_de_campo(self):
        respuesta = self.client.post('/ingresar/', {'username': '', 'password': ''})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Este campo es obligatorio.')
        self.assertNotContains(respuesta, '{{')
