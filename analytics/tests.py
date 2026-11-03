from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Cliente, Empresa, EquipoAA
from operations.models import EstadoOrden, OrdenServicio
from users.models import Tecnico


class ReportesScopingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre='Empresa A')
        cls.empresa_b = Empresa.objects.create(nombre='Empresa B')
        cls.sede_a = Cliente.objects.create(empresa=cls.empresa_a, nombre='Sede A')
        cls.sede_b = Cliente.objects.create(empresa=cls.empresa_b, nombre='Sede B')
        cls.equipo_a = EquipoAA.objects.create(
            cliente=cls.sede_a, nombre='UCA A', tipo_equipo='UCA'
        )
        cls.equipo_b = EquipoAA.objects.create(
            cliente=cls.sede_b, nombre='UCA B', tipo_equipo='UCA'
        )

        cls.supervisor = Tecnico.objects.create_user(
            username='sup_reportes', password='clave123', rol='supervisor'
        )
        cls.supervisor.empresas_visibles.add(cls.empresa_a)
        cls.admin = Tecnico.objects.create_user(
            username='admin_reportes', password='clave123', rol='tecnico',
            is_staff=True, is_superuser=True,
        )
        cls.tecnico = Tecnico.objects.create_user(
            username='tec_reportes', password='clave123', rol='tecnico'
        )

        ahora = timezone.now()
        cls.orden_mp_a = OrdenServicio.objects.create(
            cliente=cls.sede_a, tecnico=cls.tecnico, tipo='MP', radicado='MP-A1',
            cliente_nombre='Empresa A', fecha=date.today(), hora_inicio=ahora,
        )
        cls.orden_mc_a = OrdenServicio.objects.create(
            equipo=cls.equipo_a, tecnico=cls.tecnico, tipo='MC', radicado='MC-A1',
            cliente_nombre='Empresa A', fecha=date.today(), hora_inicio=ahora,
            hora_fin=ahora + timedelta(minutes=30), estado=EstadoOrden.CERRADO,
        )
        cls.orden_mp_b = OrdenServicio.objects.create(
            cliente=cls.sede_b, tecnico=cls.tecnico, tipo='MP', radicado='MP-B1',
            cliente_nombre='Empresa B', fecha=date.today(), hora_inicio=ahora,
        )
        cls.orden_mc_b = OrdenServicio.objects.create(
            equipo=cls.equipo_b, tecnico=cls.tecnico, tipo='MC', radicado='MC-B1',
            cliente_nombre='Empresa B', fecha=date.today(), hora_inicio=ahora,
            hora_fin=ahora + timedelta(minutes=120), estado=EstadoOrden.CERRADO,
        )

    def _radicados(self, response):
        return [orden.radicado for orden in response.context['historial']]

    def test_supervisor_solo_ve_ordenes_de_su_empresa(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('analytics:dashboard'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self._radicados(response), ['MP-A1', 'MC-A1'])
        self.assertEqual(response.context['total_ordenes'], 2)

    def test_admin_ve_todas_las_empresas(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('analytics:dashboard'), secure=True)
        self.assertCountEqual(
            self._radicados(response), ['MP-A1', 'MC-A1', 'MP-B1', 'MC-B1']
        )

    def test_filtro_empresa_en_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('analytics:dashboard'),
            {'empresa': self.empresa_b.pk},
            secure=True,
        )
        self.assertCountEqual(self._radicados(response), ['MP-B1', 'MC-B1'])

    def test_filtro_sede_dentro_de_empresa(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('analytics:dashboard'),
            {'empresa': self.empresa_a.pk, 'cliente': self.sede_a.pk},
            secure=True,
        )
        self.assertCountEqual(self._radicados(response), ['MP-A1', 'MC-A1'])

    def test_supervisor_no_puede_filtrar_empresa_ajena(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(
            reverse('analytics:dashboard'),
            {'empresa': self.empresa_b.pk},
            secure=True,
        )
        self.assertEqual(self._radicados(response), [])

    def test_export_supervisor_solo_incluye_su_empresa(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('analytics:exportar'), secure=True)
        contenido = response.content.decode()
        self.assertIn('MP-A1', contenido)
        self.assertIn('MC-A1', contenido)
        self.assertNotIn('MP-B1', contenido)
        self.assertNotIn('MC-B1', contenido)

    def test_mttr_solo_correctivos_de_la_empresa_visible(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('analytics:dashboard'), secure=True)
        self.assertEqual(response.context['mttr_minutos'], 30.0)

    def test_supervisor_no_ve_enlace_pdf(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('analytics:dashboard'), secure=True)
        pdf_url = reverse('operations:pdf_orden', args=[self.orden_mc_a.pk])
        self.assertNotContains(response, pdf_url)
