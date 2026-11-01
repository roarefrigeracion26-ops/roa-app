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
