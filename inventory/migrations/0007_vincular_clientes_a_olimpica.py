from django.db import migrations


def vincular_clientes_a_olimpica(apps, schema_editor):
    Empresa = apps.get_model('inventory', 'Empresa')
    Cliente = apps.get_model('inventory', 'Cliente')

    empresa_olimpica, _ = Empresa.objects.get_or_create(
        nombre='OLIMPICA S.A.',
        defaults={'nit': '890107487-3', 'activo': True}
    )

    # Asignar todas las sedes existentes a Olímpica
    Cliente.objects.filter(empresa__isnull=True).update(empresa=empresa_olimpica)


def revertir_vinculacion(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_empresa_alter_cliente_options_alter_cliente_codigo_and_more'),
    ]

    operations = [
        migrations.RunPython(vincular_clientes_a_olimpica, revertir_vinculacion),
    ]
