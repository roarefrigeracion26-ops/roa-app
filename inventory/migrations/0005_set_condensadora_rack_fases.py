from django.db import migrations


def set_fases(apps, schema_editor):
    EquipoAA = apps.get_model('inventory', 'EquipoAA')
    EquipoAA.objects.filter(tipo_equipo='CONDENSADORA_RACK').update(fases='3 PH 60HZ')


def unset_fases(apps, schema_editor):
    EquipoAA = apps.get_model('inventory', 'EquipoAA')
    EquipoAA.objects.filter(tipo_equipo='CONDENSADORA_RACK').update(fases='')


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_alter_equipoaa_tipo_equipo'),
    ]

    operations = [
        migrations.RunPython(set_fases, unset_fases),
    ]
