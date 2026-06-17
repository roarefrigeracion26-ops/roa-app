# Generated manually - adds a Condensadora Rack equipment for each active client.

from django.db import migrations


def add_condensadora_rack(apps, schema_editor):
    Cliente = apps.get_model('inventory', 'Cliente')
    EquipoAA = apps.get_model('inventory', 'EquipoAA')
    
    for cliente in Cliente.objects.filter(activo=True):
        # Skip if this cliente already has a CONDENSADORA_RACK
        if EquipoAA.objects.filter(
            cliente=cliente,
            tipo_equipo='CONDENSADORA_RACK'
        ).exists():
            continue
        
        EquipoAA.objects.create(
            cliente=cliente,
            nombre=f'Condensadora Rack',
            ubicacion='CUARTO DE MAQUINAS',
            tipo_equipo='CONDENSADORA_RACK',
            activo=True,
        )


def remove_condensadora_rack(apps, schema_editor):
    EquipoAA = apps.get_model('inventory', 'EquipoAA')
    EquipoAA.objects.filter(tipo_equipo='CONDENSADORA_RACK').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0005_medicioncondensadorarack'),
        ('inventory', '0003_cliente_codigo'),
    ]

    operations = [
        migrations.RunPython(add_condensadora_rack, remove_condensadora_rack),
    ]
