from django.test import TestCase
from inventory.models import Empresa, Cliente, TipoEquipo, EquipoAA


class EmpresaModelTest(TestCase):
    def test_crear_empresa_basica(self):
        empresa = Empresa.objects.create(nombre="Olímpica S.A.", nit="890107487-3")
        self.assertEqual(str(empresa), "Olímpica S.A.")
        self.assertTrue(empresa.activo)
        self.assertIsNotNone(empresa.creado_en)

    def test_crear_sede_vinculada_a_empresa_con_codigo_alfanumerico(self):
        empresa = Empresa.objects.create(nombre="Éxito")
        sede = Cliente.objects.create(
            empresa=empresa,
            codigo="EXT-NORTE-01",
            nombre="Éxito Calle 80",
            dir_cliente="Calle 80 # 45-12"
        )
        self.assertEqual(sede.empresa, empresa)
        self.assertEqual(sede.codigo, "EXT-NORTE-01")
        self.assertIn("EXT-NORTE-01", str(sede))
        self.assertIn("Éxito Calle 80", str(sede))

    def test_crear_sede_sin_codigo(self):
        empresa = Empresa.objects.create(nombre="Bodytech")
        sede = Cliente.objects.create(
            empresa=empresa,
            codigo="",
            nombre="Sede Recreo",
            dir_cliente="Carrera 41 # 60"
        )
        self.assertEqual(sede.codigo, "")
        self.assertIn("Sede Recreo", str(sede))
        self.assertIn("Bodytech", str(sede))


class EmpresaViewTest(TestCase):
    def setUp(self):
        from users.models import Tecnico
        self.tecnico = Tecnico.objects.create_user(
            username='tecnico_emp', password='password123', rol='tecnico'
        )
        self.empresa1 = Empresa.objects.create(nombre="Empresa Alpha")
        self.empresa2 = Empresa.objects.create(nombre="Empresa Beta", activo=False)
        Cliente.objects.create(empresa=self.empresa1, nombre="Sede 1")
        Cliente.objects.create(empresa=self.empresa1, nombre="Sede 2")

    def test_empresa_list_view_autenticado_muestra_empresas_activas(self):
        from django.test import Client
        from django.urls import reverse
        client = Client()
        client.force_login(self.tecnico)
        url = reverse('inventory:empresas')
        response = client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Alpha")
        self.assertNotContains(response, "Empresa Beta")
        empresas = response.context['empresas']
        empresa_alpha = next(e for e in empresas if e.pk == self.empresa1.pk)
        self.assertEqual(empresa_alpha.total_sedes, 2)

    def test_sedes_empresa_view_filtra_solo_sedes_de_esa_empresa(self):
        from django.test import Client
        from django.urls import reverse
        empresa_otra = Empresa.objects.create(nombre="Empresa Otra")
        Cliente.objects.create(empresa=empresa_otra, nombre="Sede Otra Empresa")

        client = Client()
        client.force_login(self.tecnico)
        url = reverse('inventory:sedes_empresa', kwargs={'empresa_id': self.empresa1.pk})
        response = client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['empresa'], self.empresa1)
        self.assertContains(response, "Sede 1")
        self.assertContains(response, "Sede 2")
        self.assertNotContains(response, "Sede Otra Empresa")


