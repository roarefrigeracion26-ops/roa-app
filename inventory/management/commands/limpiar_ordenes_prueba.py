from django.core.management.base import BaseCommand
from operations.models import (
    OrdenServicio, EquipoIntervenido, MedicionUCA, MedicionSplit,
    MedicionCondensadoraRack, Actividad, Observacion,
)
from inventory.models import Cliente, EquipoAA


class Command(BaseCommand):
    help = 'Borra todas las ordenes de servicio y su detalle, conservando clientes y equipos'

    def handle(self, *args, **options):
        # Count before
        total_ordenes = OrdenServicio.objects.count()
        total_intervenidos = EquipoIntervenido.objects.count()
        total_actividades = Actividad.objects.count()
        total_observaciones = Observacion.objects.count()
        total_med_uca = MedicionUCA.objects.count()
        total_med_split = MedicionSplit.objects.count()
        total_med_rack = MedicionCondensadoraRack.objects.count()
        total_clientes = Cliente.objects.count()
        total_equipos = EquipoAA.objects.count()

        self.stdout.write('=== Datos a ELIMINAR ===')
        self.stdout.write(f'  Ordenes de Servicio:  {total_ordenes}')
        self.stdout.write(f'  Equipos Intervenidos: {total_intervenidos}')
        self.stdout.write(f'  Mediciones UCA:       {total_med_uca}')
        self.stdout.write(f'  Mediciones Split:     {total_med_split}')
        self.stdout.write(f'  Mediciones Cond.Rack: {total_med_rack}')
        self.stdout.write(f'  Actividades:          {total_actividades}')
        self.stdout.write(f'  Observaciones:        {total_observaciones}')
        self.stdout.write('')
        self.stdout.write('=== Datos a CONSERVAR ===')
        self.stdout.write(f'  Clientes:             {total_clientes}')
        self.stdout.write(f'  Equipos AA:           {total_equipos}')
        self.stdout.write('')

        if total_ordenes == 0:
            self.stdout.write(self.style.WARNING('No hay ordenes para borrar.'))
            return

        # Delete in correct order (cascade should handle, but explicit is safer)
        MedicionCondensadoraRack.objects.all().delete()
        MedicionSplit.objects.all().delete()
        MedicionUCA.objects.all().delete()
        Observacion.objects.all().delete()
        EquipoIntervenido.objects.all().delete()
        Actividad.objects.all().delete()
        OrdenServicio.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f'Se eliminaron {total_ordenes} ordenes de servicio y todo su detalle.'))
        self.stdout.write(self.style.SUCCESS(f'Clientes y Equipos conservados intactos.'))
