#!/usr/bin/env python
"""
Script para cambiar temporalmente a plan básico y probar límites
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import Terma, PlanSuscripcion

def cambiar_a_plan_basico():
    """Cambiar la terma a plan básico para probar límites"""
    try:
        terma = Terma.objects.get(id=1)
        plan_basico = PlanSuscripcion.objects.get(nombre='Básico')
        
        print(f"🔄 Cambiando de '{terma.plan_actual.nombre if terma.plan_actual else 'Sin plan'}' a '{plan_basico.nombre}'")
        
        # Guardar plan anterior
        plan_anterior = terma.plan_actual
        
        # Cambiar a plan básico
        terma.plan_actual = plan_basico
        terma.porcentaje_comision_actual = plan_basico.porcentaje_comision
        terma.limite_fotos_actual = plan_basico.limite_fotos
        terma.save()
        
        print(f"✅ Terma ahora tiene plan Básico:")
        print(f"   - Límite de fotos: {plan_basico.limite_fotos}")
        print(f"   - Comisión: {plan_basico.porcentaje_comision}%")
        
        # Mostrar estado con fotos actuales
        from termas.models import ImagenTerma
        fotos_actuales = ImagenTerma.objects.filter(terma=terma).count()
        print(f"   - Fotos actuales: {fotos_actuales}")
        
        if fotos_actuales >= plan_basico.limite_fotos:
            print(f"⚠️ ATENCIÓN: Ya alcanzó el límite! ({fotos_actuales}/{plan_basico.limite_fotos})")
        else:
            restantes = plan_basico.limite_fotos - fotos_actuales
            print(f"✅ Puede subir {restantes} fotos más")
            
        return plan_anterior
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def restaurar_plan(plan_anterior):
    """Restaurar el plan anterior"""
    if plan_anterior:
        try:
            terma = Terma.objects.get(id=1)
            terma.plan_actual = plan_anterior
            terma.porcentaje_comision_actual = plan_anterior.porcentaje_comision
            terma.limite_fotos_actual = plan_anterior.limite_fotos
            terma.save()
            print(f"🔄 Plan restaurado a: {plan_anterior.nombre}")
        except Exception as e:
            print(f"❌ Error al restaurar: {e}")

if __name__ == '__main__':
    print("🧪 PROBANDO CAMBIO A PLAN BÁSICO")
    print("=" * 40)
    
    # Cambiar a plan básico temporalmente
    plan_anterior = cambiar_a_plan_basico()
    
    print("\n📝 Ahora la página de subir fotos debería mostrar:")
    print("   - Límite alcanzado (5/5 fotos)")
    print("   - Botón deshabilitado")
    print("   - Barra de progreso en rojo")
    
    input("\n⏸️ Presiona Enter para restaurar el plan anterior...")
    
    # Restaurar plan anterior
    restaurar_plan(plan_anterior)
    print("✅ Plan restaurado exitosamente")