from django.test import TestCase
from django.urls import reverse

from inventory.models import Cliente, Empresa
from users.models import Rol, Tecnico


class GestionAccessTests(TestCase):
    def setUp(self):
        self.admin = Tecnico.objects.create_user(
            username='admin_gestion', password='clave123',
            is_staff=True, is_superuser=True,
        )
        self.supervisor = Tecnico.objects.create_user(
            username='sup_gestion', password='clave123', rol=Rol.SUPERVISOR,
        )
        self.tecnico = Tecnico.objects.create_user(
            username='tec_gestion', password='clave123', rol=Rol.TECNICO,
        )

    def test_tecnico_es_redirigido(self):
        self.client.force_login(self.tecnico)
        response = self.client.get(reverse('gestion:index'), secure=True)
        self.assertRedirects(
            response, reverse('inventory:empresas'), fetch_redirect_response=False
        )

    def test_supervisor_es_redirigido(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('gestion:index'), secure=True)
        self.assertRedirects(
            response, reverse('analytics:dashboard'), fetch_redirect_response=False
        )

    def test_admin_accede_a_index_y_listados(self):
        self.client.force_login(self.admin)
        for url in [
            reverse('gestion:index'),
            reverse('gestion:empresas'),
            reverse('gestion:sedes'),
            reverse('gestion:supervisores'),
            reverse('gestion:empresa_crear'),
            reverse('gestion:sede_crear'),
            reverse('gestion:supervisor_crear'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, secure=True).status_code, 200)


class GestionEmpresaTests(TestCase):
    def setUp(self):
        self.admin = Tecnico.objects.create_user(
            username='admin_emp', password='clave123',
            is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)

    def test_crear_empresa(self):
        response = self.client.post(reverse('gestion:empresa_crear'), {
            'nombre': 'Empresa Nueva',
            'nit': '900123456-1',
            'activo': 'on',
        }, secure=True)
        self.assertRedirects(response, reverse('gestion:empresas'), fetch_redirect_response=False)
        self.assertTrue(Empresa.objects.filter(nombre='Empresa Nueva').exists())

    def test_editar_empresa(self):
        empresa = Empresa.objects.create(nombre='Empresa Vieja')
        response = self.client.post(
            reverse('gestion:empresa_editar', args=[empresa.pk]),
            {'nombre': 'Empresa Editada', 'nit': '123', 'activo': 'on'},
            secure=True,
        )
        self.assertRedirects(response, reverse('gestion:empresas'), fetch_redirect_response=False)
        empresa.refresh_from_db()
        self.assertEqual(empresa.nombre, 'Empresa Editada')

    def test_activar_y_desactivar_empresa(self):
        empresa = Empresa.objects.create(nombre='Empresa Toggle')
        self.client.post(
            reverse('gestion:empresa_toggle', args=[empresa.pk]), secure=True
        )
        empresa.refresh_from_db()
        self.assertFalse(empresa.activo)


class GestionSedeTests(TestCase):
    def setUp(self):
        self.admin = Tecnico.objects.create_user(
            username='admin_sede', password='clave123',
            is_staff=True, is_superuser=True,
        )
        self.empresa = Empresa.objects.create(nombre='Empresa Sede')
        self.client.force_login(self.admin)

    def test_crear_sede(self):
        response = self.client.post(reverse('gestion:sede_crear'), {
            'empresa': self.empresa.pk,
            'codigo': 'SEDE-01',
            'nombre': 'Sede Nueva',
            'dir_cliente': 'Calle 1 # 2-3',
            'activo': 'on',
        }, secure=True)
        self.assertRedirects(response, reverse('gestion:sedes'), fetch_redirect_response=False)
        self.assertTrue(
            Cliente.objects.filter(empresa=self.empresa, nombre='Sede Nueva').exists()
        )

    def test_listado_filtra_por_empresa(self):
        otra = Empresa.objects.create(nombre='Otra Empresa')
        Cliente.objects.create(empresa=self.empresa, nombre='Sede Propia')
        Cliente.objects.create(empresa=otra, nombre='Sede Ajena')
        response = self.client.get(
            reverse('gestion:sedes'), {'empresa': self.empresa.pk}, secure=True
        )
        self.assertContains(response, 'Sede Propia')
        self.assertNotContains(response, 'Sede Ajena')


class GestionSupervisorTests(TestCase):
    def setUp(self):
        self.admin = Tecnico.objects.create_user(
            username='admin_sup', password='clave123',
            is_staff=True, is_superuser=True,
        )
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')
        self.client.force_login(self.admin)

    def test_crear_supervisor_con_empresas(self):
        response = self.client.post(reverse('gestion:supervisor_crear'), {
            'username': 'nuevo_sup',
            'first_name': 'Nuevo',
            'last_name': 'Supervisor',
            'email': 'nuevo@example.com',
            'activo': 'on',
            'empresas_visibles': [self.empresa_a.pk, self.empresa_b.pk],
            'password1': 'ClaveSegura123',
            'password2': 'ClaveSegura123',
        }, secure=True)
        self.assertRedirects(response, reverse('gestion:supervisores'), fetch_redirect_response=False)
        supervisor = Tecnico.objects.get(username='nuevo_sup')
        self.assertEqual(supervisor.rol, Rol.SUPERVISOR)
        self.assertCountEqual(
            supervisor.empresas_visibles.all(), [self.empresa_a, self.empresa_b]
        )

    def test_editar_asignacion_de_empresas(self):
        supervisor = Tecnico.objects.create_user(
            username='sup_edit', password='clave123', rol=Rol.SUPERVISOR,
        )
        supervisor.empresas_visibles.add(self.empresa_a)
        response = self.client.post(
            reverse('gestion:supervisor_editar', args=[supervisor.pk]),
            {
                'username': 'sup_edit',
                'first_name': '',
                'last_name': '',
                'email': '',
                'activo': 'on',
                'empresas_visibles': [self.empresa_b.pk],
            },
            secure=True,
        )
        self.assertRedirects(response, reverse('gestion:supervisores'), fetch_redirect_response=False)
        self.assertCountEqual(supervisor.empresas_visibles.all(), [self.empresa_b])
