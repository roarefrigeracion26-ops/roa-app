from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0011_alter_ordenservicio_radicado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ordenservicio',
            name='dir_cliente',
            field=models.CharField(blank=True, max_length=500, verbose_name='Dir. Cliente'),
        ),
    ]
