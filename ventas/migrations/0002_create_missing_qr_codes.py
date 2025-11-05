from django.db import migrations
from django.utils import timezone

def crear_codigos_qr_faltantes(apps, schema_editor):
    Compra = apps.get_model('ventas', 'Compra')
    CodigoQR = apps.get_model('ventas', 'CodigoQR')
    
    # Obtener todas las compras que no tienen código QR
    for compra in Compra.objects.all():
        # Verificar si ya tiene un código QR
        if not CodigoQR.objects.filter(compra=compra).exists():
            # Crear un código QR temporal
            CodigoQR.objects.create(
                compra=compra,
                codigo=f"TEMP-{compra.id}-{timezone.now().timestamp()}",
                fecha_generacion=timezone.now()
            )

class Migration(migrations.Migration):
    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_codigos_qr_faltantes),
    ]