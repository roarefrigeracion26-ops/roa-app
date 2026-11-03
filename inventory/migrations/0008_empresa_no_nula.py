from django.db import migrations, models
import django.db.models.deletion


def asignar_empresa_faltante(apps, schema_editor):
    Empresa = apps.get_model('inventory', 'Empresa')
    Cliente = apps.get_model('inventory', 'Cliente')

    if Cliente.objects.filter(empresa__isnull=True).exists():
        empresa, _ = Empresa.objects.get_or_create(
            nombre='OLIMPICA S.A.',
            defaults={'nit': '890107487-3', 'activo': True},
        )
        Cliente.objects.filter(empresa__isnull=True).update(empresa=empresa)


def revertir_asignacion(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_vincular_clientes_a_olimpica'),
    ]

    operations = [
        migrations.RunPython(asignar_empresa_faltante, revertir_asignacion),
        migrations.AlterField(
            model_name='cliente',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='sedes',
                to='inventory.empresa',
            ),
        ),
    ]
