"""
Comando para limpiar compras pendientes vencidas y liberar cupos
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ventas.disponibilidad_utils import limpiar_compras_pendientes_vencidas
from ventas.models import Compra


class Command(BaseCommand):
    help = 'Limpia compras pendientes vencidas para liberar disponibilidad'

    def add_arguments(self, parser):
        parser.add_argument(
            '--horas',
            type=int,
            default=1,
            help='Horas de vencimiento para compras pendientes (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        horas_vencimiento = options['horas']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"🧹 Iniciando limpieza de compras pendientes vencidas (>{horas_vencimiento}h)"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 MODO DRY-RUN: Solo mostrando resultados, no se harán cambios")
            )
        
        # Buscar compras pendientes vencidas
        tiempo_vencimiento = timezone.now() - timedelta(hours=horas_vencimiento)
        
        compras_vencidas = Compra.objects.filter(
            estado_pago='pendiente',
            fecha_compra__lt=tiempo_vencimiento
        ).select_related('usuario', 'terma')
        
        total_encontradas = compras_vencidas.count()
        
        if total_encontradas == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No se encontraron compras pendientes vencidas")
            )
            return
        
        self.stdout.write(f"📋 Compras pendientes vencidas encontradas: {total_encontradas}")
        
        # Mostrar detalles
        for compra in compras_vencidas[:10]:  # Mostrar máximo 10 para no saturar
            edad = timezone.now() - compra.fecha_compra
            self.stdout.write(
                f"   🔸 ID {compra.id} - {compra.usuario.email} - "
                f"{compra.terma.nombre_terma} - {edad.total_seconds()/3600:.1f}h antiguedad"
            )
        
        if total_encontradas > 10:
            self.stdout.write(f"   ... y {total_encontradas - 10} más")
        
        if not dry_run:
            # Ejecutar limpieza
            cantidad_canceladas = limpiar_compras_pendientes_vencidas()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Limpieza completada:\n"
                    f"   📊 Compras canceladas: {cantidad_canceladas}\n"
                    f"   🔄 Disponibilidad liberada exitosamente"
                )
            )
            
            # Mostrar estadísticas adicionales
            compras_pendientes_restantes = Compra.objects.filter(
                estado_pago='pendiente'
            ).count()
            
            self.stdout.write(
                f"   📈 Compras pendientes restantes: {compras_pendientes_restantes}"
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 En modo DRY-RUN se habrían cancelado {total_encontradas} compras"
                )
            )