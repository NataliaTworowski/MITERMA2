from django.core.management.base import BaseCommand
from django.utils import timezone
from ventas.models import Compra, CodigoQR
from ventas.utils import generar_datos_qr

class Command(BaseCommand):
    help = 'Crea códigos QR para compras que no los tienen'

    def handle(self, *args, **kwargs):
        # Obtener todas las compras que no tienen código QR
        compras_sin_qr = Compra.objects.exclude(codigoqr__isnull=False)
        total = compras_sin_qr.count()
        
        self.stdout.write(f"Encontradas {total} compras sin código QR")
        
        for i, compra in enumerate(compras_sin_qr, 1):
            try:
                # Generar nuevo código QR
                datos_qr = generar_datos_qr(compra)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{i}/{total}] Creado código QR para compra {compra.id}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"[{i}/{total}] Error al crear código QR para compra {compra.id}: {str(e)}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS("¡Proceso completado!"))