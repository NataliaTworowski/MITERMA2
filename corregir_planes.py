#!/usr/bin/env python
"""
Script para corregir los límites de los planes
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import PlanSuscripcion

def corregir_planes():
    """Corregir los límites de fotos de los planes"""
    
    # Actualizar plan básico
    try:
        plan_basico = PlanSuscripcion.objects.get(nombre='Básico')
        plan_basico.limite_fotos = 5  # Cambiar a 5 fotos
        plan_basico.save()
        print(f"✅ Plan Básico actualizado: {plan_basico.limite_fotos} fotos")
    except PlanSuscripcion.DoesNotExist:
        print("❌ Plan Básico no encontrado")
    
    # Actualizar plan estándar
    try:
        plan_estandar = PlanSuscripcion.objects.get(nombre='Estándar')
        plan_estandar.limite_fotos = 15  # Mantener 15 fotos
        plan_estandar.save()
        print(f"✅ Plan Estándar mantenido: {plan_estandar.limite_fotos} fotos")
    except PlanSuscripcion.DoesNotExist:
        print("❌ Plan Estándar no encontrado")
    
    # Verificar plan premium
    try:
        plan_premium = PlanSuscripcion.objects.get(nombre='Premium')
        print(f"✅ Plan Premium: {plan_premium.limite_fotos} fotos (ilimitado)")
    except PlanSuscripcion.DoesNotExist:
        print("❌ Plan Premium no encontrado")
    
    # Eliminar plan básico duplicado si existe
    try:
        plan_basico_dup = PlanSuscripcion.objects.get(nombre='basico')  # minúscula
        print(f"⚠️ Encontrado plan duplicado 'basico': {plan_basico_dup.limite_fotos} fotos")
        plan_basico_dup.delete()
        print("✅ Plan duplicado eliminado")
    except PlanSuscripcion.DoesNotExist:
        print("📝 No hay plan básico duplicado")

if __name__ == '__main__':
    print("🔧 CORRIGIENDO LÍMITES DE PLANES")
    print("=" * 35)
    
    corregir_planes()
    
    print("\n📋 PLANES DESPUÉS DE LA CORRECCIÓN:")
    print("=" * 35)
    
    for plan in PlanSuscripcion.objects.filter(activo=True).order_by('porcentaje_comision'):
        limite_texto = 'ilimitado' if plan.limite_fotos == -1 else f'{plan.limite_fotos} fotos'
        print(f"• {plan.nombre}: {limite_texto}, {plan.porcentaje_comision}% comisión")