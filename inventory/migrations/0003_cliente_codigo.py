# Generated manually to add codigo field to Cliente
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_equipoaa_fases_equipoaa_tipo_correa'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='codigo',
            field=models.IntegerField(blank=True, null=True, unique=True, verbose_name='Código de tienda'),
        ),
    ]
