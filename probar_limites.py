#!/usr/bin/env python
"""
Script para probar los límites de fotos por plan
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import Terma, PlanSuscripcion, ImagenTerma
from usuarios.models import Usuario

def probar_limites_fotos():
    """Probar los límites de fotos con diferentes planes"""
    
    try:
        # Obtener la terma de ID 1
        terma = Terma.objects.get(id=1)
        print(f"🏔️ Probando límites para: {terma.nombre_terma}")
        
        # Mostrar estado actual
        fotos_actuales = ImagenTerma.objects.filter(terma=terma).count()
        print(f"📸 Fotos actuales: {fotos_actuales}")
        
        if terma.plan_actual:
            print(f"📋 Plan actual: {terma.plan_actual.nombre}")
            print(f"🎯 Límite de fotos: {terma.plan_actual.limite_fotos}")
            print(f"💰 Comisión: {terma.plan_actual.porcentaje_comision}%")
            
            limite = terma.plan_actual.limite_fotos
            if limite == -1:
                print("✅ Plan con fotos ilimitadas")
            else:
                restantes = max(0, limite - fotos_actuales)
                print(f"📊 Fotos restantes: {restantes}")
                
                if restantes == 0:
                    print("🚫 ¡LÍMITE ALCANZADO! No se pueden subir más fotos")
                elif restantes <= 2:
                    print("⚠️ ¡ADVERTENCIA! Pocas fotos restantes")
                else:
                    print("✅ Puede subir más fotos")
        else:
            print("❌ Sin plan asignado")
            print(f"🎯 Límite por defecto: {terma.limite_fotos_actual}")
        
        # Probar con diferentes planes
        planes = PlanSuscripcion.objects.filter(activo=True).order_by('porcentaje_comision')
        print(f"\n📊 Planes disponibles:")
        
        for plan in planes:
            print(f"   - {plan.nombre}: {plan.limite_fotos} fotos, {plan.porcentaje_comision}% comisión")
            
            # Simular cambio de plan
            if plan.limite_fotos != -1:
                if fotos_actuales > plan.limite_fotos:
                    print(f"     ⚠️ EXCEDE el límite (tiene {fotos_actuales}, límite {plan.limite_fotos})")
                elif fotos_actuales == plan.limite_fotos:
                    print(f"     🟡 EN EL LÍMITE")
                else:
                    print(f"     ✅ OK ({plan.limite_fotos - fotos_actuales} restantes)")
            else:
                print(f"     ♾️ ILIMITADO")
    
    except Terma.DoesNotExist:
        print("❌ No se encontró la terma con ID 1")
    except Exception as e:
        print(f"❌ Error: {e}")

def simular_cambio_plan(terma_id, plan_nombre):
    """Simular cambio de plan para probar límites"""
    try:
        terma = Terma.objects.get(id=terma_id)
        plan = PlanSuscripcion.objects.get(nombre=plan_nombre)
        
        print(f"\n🔄 Cambiando plan de '{terma.plan_actual.nombre if terma.plan_actual else 'Sin plan'}' a '{plan.nombre}'")
        
        # Actualizar plan
        terma.plan_actual = plan
        terma.porcentaje_comision_actual = plan.porcentaje_comision
        terma.limite_fotos_actual = plan.limite_fotos
        terma.save()
        
        print(f"✅ Plan actualizado exitosamente")
        
        # Mostrar nuevo estado
        fotos_actuales = ImagenTerma.objects.filter(terma=terma).count()
        print(f"📸 Fotos actuales: {fotos_actuales}")
        print(f"🎯 Nuevo límite: {plan.limite_fotos}")
        
        if plan.limite_fotos != -1:
            if fotos_actuales > plan.limite_fotos:
                print(f"⚠️ ADVERTENCIA: Excede el límite del nuevo plan")
            else:
                print(f"✅ Dentro del límite ({plan.limite_fotos - fotos_actuales} restantes)")
        
    except Exception as e:
        print(f"❌ Error al cambiar plan: {e}")

if __name__ == '__main__':
    print("🧪 PROBANDO LÍMITES DE FOTOS POR PLAN")
    print("=" * 50)
    
    probar_limites_fotos()
    
    # Opcional: cambiar a plan básico para probar límite
    # simular_cambio_plan(1, 'Básico')
    # print("\n" + "=" * 50)
    # probar_limites_fotos()