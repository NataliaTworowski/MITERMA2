#!/usr/bin/env python
"""
Script para verificar los comentarios y calificaciones de la terma ID 14
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import Terma, Calificacion
from usuarios.models import Usuario
from django.db.models import Avg, Count

def verificar_terma_14():
    print("=== VERIFICACIÓN TERMA ID 14 ===\n")
    
    try:
        # Obtener la terma
        terma = Terma.objects.get(id=14)
        print(f"✅ Terma encontrada: {terma.nombre_terma}")
        print(f"   Ubicación: {terma.comuna}")
        print(f"   Estado: {terma.estado_suscripcion}")
        print(f"   Calificación promedio actual: {terma.calificacion_promedio}")
        print()
        
        # Verificar calificaciones/comentarios
        calificaciones = Calificacion.objects.filter(terma=terma)
        total_calificaciones = calificaciones.count()
        
        print(f"📊 ESTADÍSTICAS DE CALIFICACIONES:")
        print(f"   Total de calificaciones: {total_calificaciones}")
        
        if total_calificaciones > 0:
            # Calcular estadísticas
            stats = calificaciones.aggregate(
                promedio=Avg('puntuacion'),
                total=Count('id')
            )
            
            print(f"   Promedio calculado: {stats['promedio']:.2f}" if stats['promedio'] else "   Sin promedio")
            print(f"   Calificaciones por puntuación:")
            
            for i in range(1, 6):
                count = calificaciones.filter(puntuacion=i).count()
                stars = "⭐" * i
                print(f"     {stars} ({i}): {count} calificaciones")
            
            print("\n📝 COMENTARIOS:")
            comentarios_con_texto = calificaciones.exclude(comentario__isnull=True).exclude(comentario='')
            print(f"   Comentarios con texto: {comentarios_con_texto.count()}")
            
            print("\n📋 DETALLE DE CALIFICACIONES:")
            for i, cal in enumerate(calificaciones.order_by('-fecha')[:10], 1):
                usuario_nombre = cal.usuario.nombre if hasattr(cal.usuario, 'nombre') else f"Usuario {cal.usuario.id}"
                comentario_preview = (cal.comentario[:50] + "...") if cal.comentario and len(cal.comentario) > 50 else (cal.comentario or "Sin comentario")
                print(f"   {i}. Usuario: {usuario_nombre}")
                print(f"      Puntuación: {'⭐' * cal.puntuacion} ({cal.puntuacion}/5)")
                print(f"      Fecha: {cal.fecha.strftime('%d/%m/%Y %H:%M')}")
                print(f"      Comentario: {comentario_preview}")
                print()
                
            if calificaciones.count() > 10:
                print(f"   ... y {calificaciones.count() - 10} calificaciones más\n")
                
        else:
            print("   ❌ No hay calificaciones registradas\n")
        
        # Verificar si el promedio está actualizado
        promedio_calculado = calificaciones.aggregate(promedio=Avg('puntuacion'))['promedio']
        
        print("🔍 VERIFICACIÓN DE CONSISTENCIA:")
        if promedio_calculado is None:
            print("   ⚠️  No hay calificaciones para calcular promedio")
            if terma.calificacion_promedio is not None:
                print("   ❌ La terma tiene un promedio pero no debería")
                return False
        else:
            print(f"   Promedio calculado en tiempo real: {promedio_calculado:.2f}")
            print(f"   Promedio almacenado en la terma: {terma.calificacion_promedio}")
            
            if terma.calificacion_promedio is None:
                print("   ❌ La terma no tiene promedio almacenado")
                return False
            elif abs(float(terma.calificacion_promedio) - float(promedio_calculado)) > 0.01:
                print("   ❌ Los promedios no coinciden")
                return False
            else:
                print("   ✅ Los promedios coinciden correctamente")
        
        return True
        
    except Terma.DoesNotExist:
        print("❌ No se encontró la terma con ID 14")
        return False
    except Exception as e:
        print(f"❌ Error al verificar la terma: {str(e)}")
        return False

def corregir_promedio_terma_14():
    """Función para corregir el promedio si está mal"""
    try:
        terma = Terma.objects.get(id=14)
        calificaciones = Calificacion.objects.filter(terma=terma)
        
        if calificaciones.exists():
            promedio_calculado = calificaciones.aggregate(promedio=Avg('puntuacion'))['promedio']
            terma.calificacion_promedio = promedio_calculado
            terma.save(update_fields=['calificacion_promedio'])
            print(f"✅ Promedio corregido a: {promedio_calculado:.2f}")
        else:
            terma.calificacion_promedio = None
            terma.save(update_fields=['calificacion_promedio'])
            print("✅ Promedio establecido como None (sin calificaciones)")
            
    except Exception as e:
        print(f"❌ Error al corregir promedio: {str(e)}")

if __name__ == "__main__":
    resultado = verificar_terma_14()
    
    if not resultado:
        print("\n🔧 ¿Quieres corregir el promedio? (s/n): ", end="")
        respuesta = input().lower().strip()
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            print("\n🔧 Corrigiendo promedio...")
            corregir_promedio_terma_14()
            print("\n📊 Verificando nuevamente...")
            verificar_terma_14()