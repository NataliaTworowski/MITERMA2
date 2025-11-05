from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('entradas', '0002_entradatipo_servicios'),
    ]

    operations = [
        migrations.AddField(
            model_name='entradatipo',
            name='duracion_tipo',
            field=models.CharField(
                choices=[('dia', 'Por el día'), ('noche', 'Por la noche'), ('dia_completo', 'Día completo')],
                default='dia',
                max_length=20,
                help_text='Define si la entrada es para uso diurno, nocturno o día completo'
            ),
        ),
        migrations.AlterField(
            model_name='entradatipo',
            name='duracion_horas',
            field=models.IntegerField(
                null=True,
                blank=True,
                help_text='Duración en horas para este tipo de entrada'
            ),
        ),
    ]