from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


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
