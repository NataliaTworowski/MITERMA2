"""
API endpoints para verificación de disponibilidad de termas
"""
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import date, datetime
import json
from ventas.disponibilidad_utils import (
    calcular_disponibilidad_terma,
    validar_cantidad_disponible,
    obtener_termas_con_disponibilidad,
    limpiar_compras_pendientes_vencidas
)


@method_decorator(csrf_exempt, name='dispatch')
class VerificarDisponibilidadView(View):
    """
    Vista para verificar disponibilidad de una terma en una fecha específica
    """
    
    def get(self, request, *args, **kwargs):
        terma_id = request.GET.get('terma_id')
        fecha_str = request.GET.get('fecha')
        cantidad = request.GET.get('cantidad', 1)
        
        if not terma_id:
            return JsonResponse({
                'error': 'terma_id es requerido'
            }, status=400)
        
        try:
            terma_id = int(terma_id)
            cantidad = int(cantidad)
            
            # Parsear fecha si se proporciona
            if fecha_str:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                fecha = date.today()
            
            # Obtener disponibilidad
            disponibilidad = calcular_disponibilidad_terma(terma_id, fecha)
            
            # Validar cantidad específica
            validacion = validar_cantidad_disponible(terma_id, cantidad, fecha)
            
            return JsonResponse({
                'terma_id': terma_id,
                'fecha': fecha.strftime('%Y-%m-%d'),
                'cantidad_solicitada': cantidad,
                'disponibilidad': disponibilidad,
                'validacion': validacion,
                'puede_proceder': validacion['es_valida'],
                'timestamp': datetime.now().isoformat()
            })
            
        except ValueError as e:
            return JsonResponse({
                'error': f'Parámetros inválidos: {str(e)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error interno: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TermasDisponiblesView(View):
    """
    Vista para obtener lista de termas con disponibilidad
    """
    
    def get(self, request, *args, **kwargs):
        fecha_str = request.GET.get('fecha')
        excluir_sin_limite = request.GET.get('excluir_sin_limite', 'false').lower() == 'true'
        
        try:
            # Parsear fecha si se proporciona
            if fecha_str:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                fecha = date.today()
            
            # Obtener termas con disponibilidad
            termas_ids = obtener_termas_con_disponibilidad(fecha, excluir_sin_limite)
            
            # Obtener información detallada
            from termas.models import Terma
            termas = Terma.objects.filter(id__in=termas_ids).values(
                'id', 'nombre_terma', 'limite_ventas_diario'
            )
            
            # Agregar información de disponibilidad a cada terma
            termas_con_info = []
            for terma in termas:
                disponibilidad = calcular_disponibilidad_terma(terma['id'], fecha)
                terma['disponibilidad'] = disponibilidad
                termas_con_info.append(terma)
            
            return JsonResponse({
                'fecha': fecha.strftime('%Y-%m-%d'),
                'total_termas': len(termas_con_info),
                'termas': termas_con_info,
                'excluir_sin_limite': excluir_sin_limite,
                'timestamp': datetime.now().isoformat()
            })
            
        except ValueError as e:
            return JsonResponse({
                'error': f'Fecha inválida: {str(e)}'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error interno: {str(e)}'
            }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def limpiar_compras_vencidas_api(request):
    """
    Vista para limpiar compras pendientes vencidas (solo para admin)
    """
    # Verificar permisos (solo admin)
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Autenticación requerida'
        }, status=401)
    
    if not hasattr(request.user, 'rol') or request.user.rol.nombre not in ['administrador_general', 'admin_terma']:
        return JsonResponse({
            'error': 'Permisos insuficientes'
        }, status=403)
    
    try:
        data = json.loads(request.body) if request.body else {}
        horas = data.get('horas', 1)
        
        cantidad_canceladas = limpiar_compras_pendientes_vencidas(horas)
        
        return JsonResponse({
            'success': True,
            'compras_canceladas': cantidad_canceladas,
            'horas_vencimiento': horas,
            'timestamp': datetime.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def estadisticas_disponibilidad(request):
    """
    Vista para obtener estadísticas de disponibilidad del sistema
    """
    try:
        from termas.models import Terma
        from ventas.models import Compra
        from django.db.models import Count, Sum
        from django.utils import timezone
        from datetime import timedelta
        
        # Estadísticas básicas
        total_termas = Terma.objects.filter(estado_suscripcion='activa').count()
        termas_con_limite = Terma.objects.filter(
            estado_suscripcion='activa',
            limite_ventas_diario__gt=0
        ).count()
        
        # Termas con disponibilidad hoy
        termas_disponibles_hoy = len(obtener_termas_con_disponibilidad(date.today()))
        
        # Compras pendientes
        compras_pendientes = Compra.objects.filter(estado_pago='pendiente').count()
        
        # Compras pendientes vencidas (>1 hora)
        hace_1_hora = timezone.now() - timedelta(hours=1)
        compras_vencidas = Compra.objects.filter(
            estado_pago='pendiente',
            fecha_compra__lt=hace_1_hora
        ).count()
        
        return JsonResponse({
            'estadisticas': {
                'total_termas_activas': total_termas,
                'termas_con_limite_diario': termas_con_limite,
                'termas_sin_limite': total_termas - termas_con_limite,
                'termas_disponibles_hoy': termas_disponibles_hoy,
                'compras_pendientes': compras_pendientes,
                'compras_pendientes_vencidas': compras_vencidas,
            },
            'fecha_consulta': date.today().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error al obtener estadísticas: {str(e)}'
        }, status=500)