from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from inventory.models import Empresa
from users.models import Tecnico


class SupervisorEmpresasTests(TestCase):
    def test_supervisor_puede_tener_empresas_visibles(self):
        empresa = Empresa.objects.create(nombre='Empresa Test')
        supervisor = Tecnico.objects.create_user(
            username='sup_test', password='clave123', rol='supervisor'
        )
        supervisor.empresas_visibles.add(empresa)
        self.assertIn(empresa, supervisor.empresas_visibles.all())


class PermisosEmpresasTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')
        self.empresa_inactiva = Empresa.objects.create(nombre='Empresa Inactiva', activo=False)
        self.supervisor = Tecnico.objects.create_user(
            username='sup_a', password='clave123', rol='supervisor'
        )
        self.supervisor.empresas_visibles.add(self.empresa_a, self.empresa_inactiva)
        self.admin = Tecnico.objects.create_user(
            username='admin_roa', password='clave123', rol='tecnico',
            is_staff=True, is_superuser=True,
        )
        self.tecnico = Tecnico.objects.create_user(
            username='tec_a', password='clave123', rol='tecnico'
        )

    def test_admin_ve_todas_las_empresas_activas(self):
        from users.permissions import empresas_visibles
        self.assertQuerySetEqual(
            empresas_visibles(self.admin).order_by('nombre'),
            [self.empresa_a, self.empresa_b],
        )

    def test_supervisor_ve_solo_sus_empresas_activas(self):
        from users.permissions import empresas_visibles
        self.assertQuerySetEqual(
            empresas_visibles(self.supervisor),
            [self.empresa_a],
        )

    def test_tecnico_no_ve_empresas(self):
        from users.permissions import empresas_visibles
        self.assertFalse(empresas_visibles(self.tecnico).exists())


class RestriccionSupervisorTests(TestCase):
    def setUp(self):
        self.supervisor = Tecnico.objects.create_user(
            username='sup_rest', password='clave123', rol='supervisor'
        )
        self.admin = Tecnico.objects.create_user(
            username='admin_rest', password='clave123', rol='supervisor',
            is_staff=True, is_superuser=True,
        )
        self.tecnico = Tecnico.objects.create_user(
            username='tec_rest', password='clave123', rol='tecnico'
        )

    def test_supervisor_es_redirigido_de_inventario_a_reportes(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('inventory:empresas'), secure=True)
        self.assertRedirects(
            response, reverse('analytics:dashboard'), fetch_redirect_response=False
        )

    def test_supervisor_accede_a_reportes(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('analytics:dashboard'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_staff_puede_acceder_a_inventario(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('inventory:empresas'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_tecnico_no_se_ve_afectado(self):
        self.client.force_login(self.tecnico)
        response = self.client.get(reverse('inventory:empresas'), secure=True)
        self.assertEqual(response.status_code, 200)


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
        self.assertRedirects(respuesta, reverse('inventory:empresas'))

    def test_login_tiene_volver_al_inicio(self):
        respuesta = self.client.get('/ingresar/')
        self.assertContains(respuesta, reverse('landing'))
        self.assertContains(respuesta, 'Volver al inicio')

    def test_login_muestra_errores_de_campo(self):
        respuesta = self.client.post('/ingresar/', {'username': '', 'password': ''})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Este campo es obligatorio.')
        self.assertNotContains(respuesta, '{{')
