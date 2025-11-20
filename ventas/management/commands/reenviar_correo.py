from django.core.management.base import BaseCommand
from ventas.models import Compra
from ventas.utils import enviar_entrada_por_correo

class Command(BaseCommand):
    help = 'Reenvía el correo con la entrada para una compra específica'

    def add_arguments(self, parser):
        parser.add_argument('compra_id', type=int, help='ID de la compra para reenviar el correo')

    def handle(self, *args, **kwargs):
        compra_id = kwargs['compra_id']
        
        try:
            compra = Compra.objects.get(id=compra_id, estado_pago='pagado')
            
            self.stdout.write(f"Reenviando correo para compra {compra_id}...")
            
            # Reenviar el correo
            enviar_entrada_por_correo(compra)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Correo reenviado exitosamente para compra {compra_id} a {compra.usuario.email}"
                )
            )
            
        except Compra.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"No se encontró una compra pagada con ID {compra_id}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error al reenviar correo: {str(e)}"
                )
            )