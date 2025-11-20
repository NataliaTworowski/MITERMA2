"""
Comando management para enviar emails cuando las entradas se finalizan
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ventas.models import RegistroEscaneo, CodigoQR
from entradas.models import EntradaTipo
from termas.email_utils import enviar_email_entrada_finalizada
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envía emails a clientes cuando sus entradas se finalizan'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutos-ventana',
            type=int,
            default=10,
            help='Ventana de tiempo en minutos para buscar entradas recién finalizadas'
        )

    def handle(self, *args, **options):
        minutos_ventana = options['minutos_ventana']
        ahora = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Iniciando verificación de entradas finalizadas - {ahora.strftime("%Y-%m-%d %H:%M:%S")}'
            )
        )
        
        # Buscar registros de escaneo exitosos que no hayan enviado email de finalización
        registros = RegistroEscaneo.objects.filter(
            exitoso=True,
            fecha_escaneo__isnull=False,
            email_finalizacion_enviado=False
        ).select_related(
            'codigo_qr',
            'codigo_qr__compra',
            'codigo_qr__compra__usuario',
            'codigo_qr__compra__terma'
        ).order_by('-fecha_escaneo')
        
        emails_enviados = 0
        entradas_procesadas = 0
        
        for registro in registros:
            try:
                compra = registro.codigo_qr.compra
                cliente = compra.usuario
                
                # Obtener información de la entrada
                detalle = compra.detalles.first()
                if not detalle or not detalle.entrada_tipo:
                    continue
                
                entrada_tipo = detalle.entrada_tipo
                duracion_horas = getattr(entrada_tipo, 'duracion_horas', 0) or 0
                
                if duracion_horas <= 0:
                    continue  # No tiene duración definida
                
                # Calcular el tiempo de finalización
                fecha_uso = registro.codigo_qr.fecha_uso or registro.fecha_escaneo
                tiempo_finalizacion = fecha_uso + timedelta(hours=duracion_horas)
                
                # Verificar si la entrada se finalizó en la ventana de tiempo especificada
                tiempo_limite = ahora - timedelta(minutes=minutos_ventana)
                
                if tiempo_limite <= tiempo_finalizacion <= ahora:
                    # La entrada se finalizó recientemente
                    entradas_procesadas += 1
                    
                    # Enviar email
                    if enviar_email_entrada_finalizada(cliente, compra, registro):
                        emails_enviados += 1
                        
                        # Marcar como enviado
                        registro.email_finalizacion_enviado = True
                        registro.fecha_email_finalizacion = ahora
                        registro.save(update_fields=['email_finalizacion_enviado', 'fecha_email_finalizacion'])
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Email enviado a {cliente.email} - Entrada en {compra.terma.nombre_terma}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Error enviando email a {cliente.email} - Entrada en {compra.terma.nombre_terma}'
                            )
                        )
                
            except Exception as e:
                logger.error(f"Error procesando registro {registro.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(
                        f'Error procesando registro {registro.id}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Proceso completado - {entradas_procesadas} entradas procesadas, {emails_enviados} emails enviados'
            )
        )