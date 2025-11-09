from django.core.management.base import BaseCommand
from django.db.models import Q
from ventas.models import Compra, DistribucionPago
from ventas.utils import procesar_pago_completo, simular_pago_terma
from django.utils import timezone


class Command(BaseCommand):
    help = 'Gestiona las distribuciones de pago del sistema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--procesar-pendientes',
            action='store_true',
            help='Procesar distribuciones de compras pagadas que no tienen distribución'
        )
        
        parser.add_argument(
            '--simular-pagos',
            action='store_true',
            help='Simular pagos a termas para distribuciones procesadas'
        )
        
        parser.add_argument(
            '--compra-id',
            type=int,
            help='Procesar una compra específica por ID'
        )
        
        parser.add_argument(
            '--estadisticas',
            action='store_true',
            help='Mostrar estadísticas del sistema de distribución'
        )
        
        parser.add_argument(
            '--recalcular',
            action='store_true',
            help='Recalcular distribuciones pendientes'
        )
    
    def handle(self, *args, **options):
        if options['estadisticas']:
            self.mostrar_estadisticas()
        
        elif options['compra_id']:
            self.procesar_compra_especifica(options['compra_id'])
        
        elif options['procesar_pendientes']:
            self.procesar_compras_pendientes()
        
        elif options['simular_pagos']:
            self.simular_pagos_pendientes()
        
        elif options['recalcular']:
            self.recalcular_distribuciones()
        
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Debes especificar una acción. Usa --help para ver las opciones.'
                )
            )
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas del sistema de distribución"""
        from django.db.models import Sum, Count, Avg
        
        self.stdout.write(self.style.SUCCESS('\n=== ESTADÍSTICAS DEL SISTEMA DE DISTRIBUCIÓN ===\n'))
        
        # Estadísticas de compras
        total_compras = Compra.objects.count()
        compras_pagadas = Compra.objects.filter(estado_pago='pagado').count()
        compras_con_distribucion = Compra.objects.filter(distribucion_pago__isnull=False).count()
        
        self.stdout.write(f"📊 Compras totales: {total_compras}")
        self.stdout.write(f"💰 Compras pagadas: {compras_pagadas}")
        self.stdout.write(f"📈 Compras con distribución: {compras_con_distribucion}")
        
        # Estadísticas de distribuciones
        distribuciones = DistribucionPago.objects.all()
        if distribuciones.exists():
            stats = distribuciones.aggregate(
                total=Count('id'),
                monto_total=Sum('monto_total'),
                comisiones_total=Sum('monto_comision_plataforma'),
                termas_total=Sum('monto_para_terma'),
                promedio_comision=Avg('porcentaje_comision')
            )
            
            self.stdout.write(f"\n📋 Distribuciones creadas: {stats['total']}")
            self.stdout.write(f"💵 Monto total distribuido: ${stats['monto_total']:.2f}")
            self.stdout.write(f"🏛️  Total comisiones plataforma: ${stats['comisiones_total']:.2f}")
            self.stdout.write(f"🏨 Total pagado a termas: ${stats['termas_total']:.2f}")
            self.stdout.write(f"📊 Promedio comisión: {stats['promedio_comision']:.2f}%")
            
            # Por estado
            self.stdout.write(f"\n📈 DISTRIBUCIONES POR ESTADO:")
            for estado, _ in DistribucionPago.ESTADO_DISTRIBUCION:
                count = distribuciones.filter(estado=estado).count()
                if count > 0:
                    self.stdout.write(f"   {estado}: {count}")
        
        # Compras pagadas sin distribución
        compras_sin_distribucion = Compra.objects.filter(
            estado_pago='pagado',
            distribucion_pago__isnull=True
        ).count()
        
        if compras_sin_distribucion > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Hay {compras_sin_distribucion} compras pagadas sin distribución!"
                )
            )
    
    def procesar_compra_especifica(self, compra_id):
        """Procesa una compra específica"""
        try:
            compra = Compra.objects.get(id=compra_id)
            
            if compra.estado_pago != 'pagado':
                self.stdout.write(
                    self.style.ERROR(
                        f"La compra {compra_id} no está en estado 'pagado' (actual: {compra.estado_pago})"
                    )
                )
                return
            
            # Verificar si ya tiene distribución
            if hasattr(compra, 'distribucion_pago'):
                self.stdout.write(
                    self.style.WARNING(
                        f"La compra {compra_id} ya tiene una distribución (ID: {compra.distribucion_pago.id})"
                    )
                )
                return
            
            self.stdout.write(f"Procesando compra {compra_id}...")
            distribucion = procesar_pago_completo(compra)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Compra {compra_id} procesada exitosamente!\n"
                    f"   Distribución ID: {distribucion.id}\n"
                    f"   Total: ${distribucion.monto_total}\n"
                    f"   Comisión: ${distribucion.monto_comision_plataforma}\n"
                    f"   Para terma: ${distribucion.monto_para_terma}"
                )
            )
            
        except Compra.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"No se encontró la compra {compra_id}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error al procesar compra {compra_id}: {str(e)}")
            )
    
    def procesar_compras_pendientes(self):
        """Procesa todas las compras pagadas que no tienen distribución"""
        compras_pendientes = Compra.objects.filter(
            estado_pago='pagado',
            distribucion_pago__isnull=True
        )
        
        total = compras_pendientes.count()
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No hay compras pendientes de procesar")
            )
            return
        
        self.stdout.write(f"Procesando {total} compras pendientes...")
        
        exitosas = 0
        errores = 0
        
        for compra in compras_pendientes:
            try:
                distribucion = procesar_pago_completo(compra)
                exitosas += 1
                self.stdout.write(f"✅ Compra {compra.id} -> Distribución {distribucion.id}")
                
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Error en compra {compra.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Procesamiento completado:\n"
                f"   Exitosas: {exitosas}\n"
                f"   Errores: {errores}\n"
                f"   Total: {total}"
            )
        )
    
    def simular_pagos_pendientes(self):
        """Simula pagos para distribuciones que están procesadas"""
        distribuciones_pendientes = DistribucionPago.objects.filter(
            estado='procesado'
        )
        
        total = distribuciones_pendientes.count()
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No hay distribuciones pendientes de pago")
            )
            return
        
        self.stdout.write(f"Simulando pagos para {total} distribuciones...")
        
        exitosas = 0
        errores = 0
        
        for distribucion in distribuciones_pendientes:
            try:
                pago = simular_pago_terma(distribucion)
                if pago:
                    exitosas += 1
                    self.stdout.write(
                        f"✅ Distribución {distribucion.id} -> Pago {pago.id} "
                        f"(${distribucion.monto_para_terma} a {distribucion.terma.nombre_terma})"
                    )
                else:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error en distribución {distribucion.id}")
                    )
                
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Error en distribución {distribucion.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Simulación de pagos completada:\n"
                f"   Exitosas: {exitosas}\n"
                f"   Errores: {errores}\n"
                f"   Total: {total}"
            )
        )
    
    def recalcular_distribuciones(self):
        """Recalcula distribuciones pendientes"""
        distribuciones_pendientes = DistribucionPago.objects.filter(
            estado='pendiente'
        )
        
        total = distribuciones_pendientes.count()
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS("✅ No hay distribuciones pendientes de recalcular")
            )
            return
        
        self.stdout.write(f"Recalculando {total} distribuciones...")
        
        for distribucion in distribuciones_pendientes:
            try:
                distribucion.calcular_distribucion()
                self.stdout.write(f"✅ Distribución {distribucion.id} recalculada")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error en distribución {distribucion.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"📊 Recálculo completado para {total} distribuciones")
        )