"""
Utilidades para control de disponibilidad de entradas por día
"""
from datetime import date, datetime
from typing import Dict, List, Optional
from django.db.models import Sum, Q
from ventas.models import Compra, DetalleCompra
from entradas.models import EntradaTipo
from termas.models import Terma


def calcular_entradas_vendidas_por_dia(terma_id, fecha: date) -> int:
    """
    Calcula el total de entradas vendidas para una terma en una fecha específica
    Solo cuenta las compras pagadas
    
    Args:
        terma_id: int o UUID de la terma
        fecha: fecha a consultar
    """
    try:
        # Obtener el ID numérico si se pasó un UUID
        if isinstance(terma_id, str):
            from uuid import UUID
            try:
                UUID(terma_id)  # Validar que es un UUID
                terma = Terma.objects.get(uuid=terma_id)
                terma_id = terma.id
            except (ValueError, Terma.DoesNotExist):
                return 0
        
        total_vendidas = DetalleCompra.objects.filter(
            compra__terma_id=terma_id,
            compra__fecha_visita=fecha,
            compra__estado_pago='pagado'
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        print(f"[DEBUG] Entradas vendidas para terma {terma_id} en {fecha}: {total_vendidas}")
        return total_vendidas
    except Exception as e:
        print(f"[DEBUG] Error calculando entradas vendidas: {e}")
        return 0


def calcular_entradas_pendientes_por_dia(terma_id, fecha: date) -> int:
    """
    Calcula el total de entradas en estado pendiente para una terma en una fecha específica
    Esto incluye compras que están siendo procesadas
    
    Args:
        terma_id: int o UUID de la terma
        fecha: fecha a consultar
    """
    try:
        # Obtener el ID numérico si se pasó un UUID
        if isinstance(terma_id, str):
            from uuid import UUID
            try:
                UUID(terma_id)  # Validar que es un UUID
                terma = Terma.objects.get(uuid=terma_id)
                terma_id = terma.id
            except (ValueError, Terma.DoesNotExist):
                return 0
        
        total_pendientes = DetalleCompra.objects.filter(
            compra__terma_id=terma_id,
            compra__fecha_visita=fecha,
            compra__estado_pago='pendiente'
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        print(f"[DEBUG] Entradas pendientes para terma {terma_id} en {fecha}: {total_pendientes}")
        return total_pendientes
    except Exception as e:
        print(f"[DEBUG] Error calculando entradas pendientes: {e}")
        return 0


def calcular_disponibilidad_terma(terma_id, fecha: date = None) -> Dict:
    """
    Calcula la disponibilidad actual de una terma para una fecha específica
    
    Args:
        terma_id: int o UUID de la terma
        fecha: fecha a consultar (por defecto hoy)
    
    Returns:
        Dict con:
        - limite_diario: int - límite de entradas por día
        - vendidas: int - entradas ya vendidas (pagadas)
        - pendientes: int - entradas en proceso de pago
        - comprometidas: int - total de entradas comprometidas (vendidas + pendientes)
        - disponibles: int - entradas disponibles para la venta
        - puede_vender: bool - si se pueden vender más entradas
    """
    if fecha is None:
        fecha = date.today()
    
    try:
        # Obtener la terma (aceptar UUID o ID)
        if isinstance(terma_id, str):
            from uuid import UUID
            try:
                UUID(terma_id)  # Validar que es un UUID
                terma = Terma.objects.get(uuid=terma_id)
            except (ValueError, Terma.DoesNotExist):
                return {
                    'error': 'Terma no encontrada',
                    'limite_diario': 0,
                    'vendidas': 0,
                    'pendientes': 0,
                    'comprometidas': 0,
                    'disponibles': 0,
                    'puede_vender': False,
                    'sin_limite': False
                }
        else:
            terma = Terma.objects.get(id=terma_id)
        
        # Usar el ID numérico para las consultas
        terma_id = terma.id
        limite_diario = terma.limite_ventas_diario or 0
        
        # Si no tiene límite configurado, asumimos disponibilidad ilimitada
        if limite_diario <= 0:
            return {
                'limite_diario': 0,
                'vendidas': 0,
                'pendientes': 0,
                'comprometidas': 0,
                'disponibles': float('inf'),
                'puede_vender': True,
                'sin_limite': True
            }
        
        vendidas = calcular_entradas_vendidas_por_dia(terma_id, fecha)
        pendientes = calcular_entradas_pendientes_por_dia(terma_id, fecha)
        comprometidas = vendidas + pendientes
        disponibles = max(0, limite_diario - comprometidas)
        
        print(f"[DEBUG DISPONIBILIDAD] Terma {terma_id}, Fecha {fecha}:")
        print(f"[DEBUG] - Límite diario: {limite_diario}")
        print(f"[DEBUG] - Vendidas: {vendidas}")  
        print(f"[DEBUG] - Pendientes: {pendientes}")
        print(f"[DEBUG] - Comprometidas: {comprometidas}")
        print(f"[DEBUG] - Disponibles: {disponibles}")
        print(f"[DEBUG] - Puede vender: {disponibles > 0}")
        
        return {
            'limite_diario': limite_diario,
            'vendidas': vendidas,
            'pendientes': pendientes,
            'comprometidas': comprometidas,
            'disponibles': disponibles,
            'puede_vender': disponibles > 0,
            'sin_limite': False
        }
        
    except Terma.DoesNotExist:
        return {
            'limite_diario': 0,
            'vendidas': 0,
            'pendientes': 0,
            'comprometidas': 0,
            'disponibles': 0,
            'puede_vender': False,
            'sin_limite': False,
            'error': 'Terma no encontrada'
        }


def validar_cantidad_disponible(terma_id, cantidad_solicitada: int, fecha: date = None) -> Dict:
    """
    Valida si es posible vender una cantidad específica de entradas para una fecha
    
    Args:
        terma_id: int o UUID de la terma
        cantidad_solicitada: cantidad de entradas a vender
        fecha: fecha de la visita (por defecto hoy)
    
    Returns:
        Dict con:
        - es_valida: bool - si se puede proceder con la compra
        - disponibles: int - entradas disponibles
        - mensaje: str - mensaje explicativo
    """
    if fecha is None:
        fecha = date.today()
        
    disponibilidad = calcular_disponibilidad_terma(terma_id, fecha)
    
    if 'error' in disponibilidad:
        return {
            'es_valida': False,
            'disponibles': 0,
            'mensaje': disponibilidad['error']
        }
    
    if disponibilidad['sin_limite']:
        return {
            'es_valida': True,
            'disponibles': float('inf'),
            'mensaje': 'Disponibilidad ilimitada'
        }
    
    disponibles = disponibilidad['disponibles']
    
    if cantidad_solicitada <= disponibles:
        return {
            'es_valida': True,
            'disponibles': disponibles,
            'mensaje': f'Quedarían {disponibles - cantidad_solicitada} entradas disponibles'
        }
    else:
        return {
            'es_valida': False,
            'disponibles': disponibles,
            'mensaje': f'Solo quedan {disponibles} entradas disponibles para el {fecha.strftime("%d/%m/%Y")}'
        }


def obtener_termas_con_disponibilidad(fecha: date = None, excluir_sin_limite: bool = False) -> List[int]:
    """
    Retorna IDs de termas que tienen disponibilidad para una fecha específica
    
    Args:
        fecha: fecha a verificar (default: hoy)
        excluir_sin_limite: si True, excluye termas sin límite configurado
        
    Returns:
        Lista de IDs de termas con disponibilidad
    """
    if fecha is None:
        fecha = date.today()
    
    termas_disponibles = []
    
    # Obtener todas las termas activas
    termas = Terma.objects.filter(estado_suscripcion__in=['activo', 'premium'])
    
    for terma in termas:
        disponibilidad = calcular_disponibilidad_terma(terma.id, fecha)
        
        if disponibilidad['puede_vender']:
            if excluir_sin_limite and disponibilidad['sin_limite']:
                continue
            termas_disponibles.append(terma.id)
    
    return termas_disponibles


def obtener_proximas_fechas_disponibles(terma_id: int, desde: date = None, dias: int = 30) -> List[date]:
    """
    Obtiene las próximas fechas disponibles para una terma
    
    Args:
        terma_id: ID de la terma
        desde: fecha desde la cual buscar (default: hoy)
        dias: cantidad de días hacia adelante a revisar
        
    Returns:
        Lista de fechas con disponibilidad
    """
    if desde is None:
        desde = date.today()
    
    fechas_disponibles = []
    
    for i in range(dias):
        fecha_actual = desde
        if i > 0:
            from datetime import timedelta
            fecha_actual = desde + timedelta(days=i)
        
        disponibilidad = calcular_disponibilidad_terma(terma_id, fecha_actual)
        if disponibilidad['puede_vender']:
            fechas_disponibles.append(fecha_actual)
    
    return fechas_disponibles


def limpiar_compras_pendientes_vencidas(horas_vencimiento: int = 1) -> int:
    """
    Marca como canceladas las compras pendientes que han estado más tiempo sin pagar
    Esto libera cupos para nuevas ventas
    
    Args:
        horas_vencimiento: Horas después de las cuales una compra pendiente se considera vencida
        
    Returns:
        Cantidad de compras canceladas
    """
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    tiempo_vencimiento = timezone.now() - timedelta(hours=horas_vencimiento)
    
    compras_vencidas = Compra.objects.filter(
        estado_pago='pendiente',
        fecha_compra__lt=tiempo_vencimiento
    )
    
    cantidad_canceladas = compras_vencidas.update(
        estado_pago='cancelado_timeout',
        fecha_actualizacion=timezone.now()
    )
    
    return cantidad_canceladas