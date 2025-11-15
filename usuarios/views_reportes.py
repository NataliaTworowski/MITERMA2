from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
import json
import csv
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from .decorators import admin_terma_required


@admin_terma_required
def reportes_premium(request):
    """Vista para mostrar reportes premium para administradores de termas."""
    usuario = request.user
    terma = usuario.terma
    
    # Verificar que el usuario tenga plan premium (a través de la terma)
    if not (hasattr(usuario, 'terma') and usuario.terma and usuario.terma.plan_actual and usuario.terma.plan_actual.nombre == 'premium'):
        messages.error(request, 'Esta funcionalidad requiere un plan premium.')
        return redirect('usuarios:adm_termas')
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    reportes_data = None
    
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Importar modelo Compra
            from ventas.models import Compra
            
            # Obtener compras del período
            compras = Compra.objects.filter(
                terma=terma,
                fecha_compra__date__gte=fecha_inicio_dt,
                fecha_compra__date__lte=fecha_fin_dt,
                estado_pago='pagado'
            )
            
            # Calcular KPIs
            total_ingresos = compras.aggregate(total=Sum('total'))['total'] or 0
            total_entradas = compras.aggregate(total=Sum('cantidad'))['total'] or 0
            total_clientes = compras.values('usuario').distinct().count()
            promedio_venta = compras.aggregate(avg=Avg('total'))['avg'] or 0
            
            # Nuevas métricas: Clientes nuevos vs recurrentes
            clientes_periodo = set(compras.values_list('usuario', flat=True).distinct())
            
            # Obtener compras anteriores al período para identificar clientes recurrentes
            compras_anteriores = Compra.objects.filter(
                terma=terma,
                fecha_compra__date__lt=fecha_inicio_dt,
                estado_pago='pagado'
            ).values_list('usuario', flat=True).distinct()
            
            clientes_anteriores = set(compras_anteriores)
            clientes_nuevos = len(clientes_periodo - clientes_anteriores)
            clientes_recurrentes = len(clientes_periodo & clientes_anteriores)
            
            # Porcentaje de retención
            if total_clientes > 0:
                porcentaje_retencion = (clientes_recurrentes / total_clientes) * 100
            else:
                porcentaje_retencion = 0
            
            # Comparativa de ventas con período anterior
            dias_periodo = (fecha_fin_dt - fecha_inicio_dt).days + 1
            fecha_inicio_anterior = fecha_inicio_dt - timedelta(days=dias_periodo)
            fecha_fin_anterior = fecha_inicio_dt - timedelta(days=1)
            
            ventas_anterior = Compra.objects.filter(
                terma=terma,
                fecha_compra__date__gte=fecha_inicio_anterior,
                fecha_compra__date__lte=fecha_fin_anterior,
                estado_pago='pagado'
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Calcular porcentaje de crecimiento
            if ventas_anterior > 0:
                crecimiento_ventas = ((total_ingresos - ventas_anterior) / ventas_anterior) * 100
            else:
                crecimiento_ventas = 100 if total_ingresos > 0 else 0
                
            crecimiento_positivo = crecimiento_ventas >= 0
            
            # Ventas por día
            ventas_por_dia = compras.annotate(
                fecha=TruncDate('fecha_compra')
            ).values('fecha').annotate(
                total_dia=Sum('total')
            ).order_by('fecha')
            
            # Tipos de entrada más vendidos - agrupar por nombre para evitar duplicados
            from entradas.models import EntradaTipo
            from django.db.models import Q
            from collections import defaultdict
            
            # Obtener datos agrupados por nombre de entrada
            tipos_vendidos = defaultdict(int)
            for compra in compras.prefetch_related('detalles__entrada_tipo'):
                for detalle in compra.detalles.all():
                    tipos_vendidos[detalle.entrada_tipo.nombre] += detalle.cantidad
            
            # Convertir a lista ordenada y tomar los top 5
            tipos_entrada_ordenados = sorted(tipos_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # Preparar datos para gráficos
            fechas_labels = []
            ventas_valores = []
            fecha_actual = fecha_inicio_dt
            while fecha_actual <= fecha_fin_dt:
                fechas_labels.append(fecha_actual.strftime('%d/%m'))
                venta_dia = next((v['total_dia'] for v in ventas_por_dia if v['fecha'] == fecha_actual), 0)
                ventas_valores.append(float(venta_dia))
                fecha_actual += timedelta(days=1)
            
            tipos_entrada_labels = [nombre for nombre, cantidad in tipos_entrada_ordenados]
            tipos_entrada_data = [cantidad for nombre, cantidad in tipos_entrada_ordenados]
            
            reportes_data = {
                'total_ingresos': total_ingresos,
                'total_entradas': total_entradas,
                'total_clientes': total_clientes,
                'promedio_venta': promedio_venta,
                'clientes_nuevos': clientes_nuevos,
                'clientes_recurrentes': clientes_recurrentes,
                'porcentaje_retencion': porcentaje_retencion,
                'crecimiento_ventas': crecimiento_ventas,
                'crecimiento_positivo': crecimiento_positivo,
                'ventas_anterior': ventas_anterior,
                'ventas_detalle': compras.select_related('usuario').prefetch_related('detalles__entrada_tipo'),
                'fechas_labels': fechas_labels,
                'ventas_por_dia': ventas_valores,
                'tipos_entrada_labels': tipos_entrada_labels,
                'tipos_entrada_data': tipos_entrada_data,
            }
            
        except ValueError:
            messages.error(request, 'Formato de fecha inválido.')
    
    context = {
        'title': 'Reportes Premium - MiTerma',
        'usuario': usuario,
        'terma': terma,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'reportes_data': reportes_data,
    }
    
    return render(request, 'administrador_termas/reporte_premium.html', context)


@admin_terma_required
def exportar_reporte_csv(request):
    """Vista para exportar reportes a CSV."""
    from django.http import JsonResponse
    
    usuario = request.user
    terma = usuario.terma
    
    # Verificar que el usuario tenga plan premium (a través de la terma)
    if not (hasattr(usuario, 'terma') and usuario.terma and usuario.terma.plan_actual and usuario.terma.plan_actual.nombre == 'premium'):
        return JsonResponse({'error': 'Esta funcionalidad requiere un plan premium.'}, status=403)
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        return JsonResponse({'error': 'Debe especificar fechas de inicio y fin.'}, status=400)
    
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        # Importar modelo Compra
        from ventas.models import Compra
        
        # Obtener compras del período
        compras = Compra.objects.filter(
            terma=terma,
            fecha_compra__date__gte=fecha_inicio_dt,
            fecha_compra__date__lte=fecha_fin_dt,
            estado_pago='pagado'
        ).select_related('usuario').prefetch_related('detalles__entrada_tipo')
        
        # Crear respuesta CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reporte_{terma.nombre_terma}_{fecha_inicio}_{fecha_fin}.csv"'
        response.write('\ufeff')  # BOM para UTF-8
        
        writer = csv.writer(response)
        writer.writerow([
            'Fecha Compra', 'Nombre Cliente', 'Apellido Cliente', 'Email Cliente', 
            'Tipo Entrada', 'Cantidad', 'Precio Unitario', 'Subtotal', 'Total Compra'
        ])
        
        for compra in compras:
            for detalle in compra.detalles.all():
                writer.writerow([
                    compra.fecha_compra.strftime('%d/%m/%Y %H:%M'),
                    compra.usuario.nombre,
                    compra.usuario.apellido,
                    compra.usuario.email,
                    detalle.entrada_tipo.nombre,
                    detalle.cantidad,
                    detalle.precio_unitario,
                    detalle.subtotal,
                    compra.total
                ])
        
        return response
        
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al generar CSV: {str(e)}'}, status=500)