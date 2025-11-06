#!/usr/bin/env python
"""
Script para asignar suscripción por defecto a termas sin plan
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import Terma, PlanSuscripcion, SuscripcionTerma
from usuarios.models import Usuario

def asignar_suscripciones():
    """Asignar suscripciones por defecto a termas sin plan"""
    
    # Obtener el plan básico
    plan_basico = PlanSuscripcion.objects.filter(nombre='Básico').first()
    
    if not plan_basico:
        print("❌ No se encontró el plan básico")
        return
    
    # Obtener todas las termas que no tienen suscripción activa
    termas_sin_plan = Terma.objects.exclude(
        suscripcionterma__estado='activa'
    )
    
    print(f"🔍 Encontradas {termas_sin_plan.count()} termas sin plan activo")
    
    for terma in termas_sin_plan:
        # Crear suscripción básica
        suscripcion, created = SuscripcionTerma.objects.get_or_create(
            terma=terma,
            estado='activa',
            defaults={
                'plan': plan_basico
            }
        )
        
        if created:
            print(f"✅ Suscripción básica creada para: {terma.nombre_terma}")
        else:
            print(f"📌 Suscripción ya existe para: {terma.nombre_terma}")
    
    # Mostrar resumen
    total_activas = SuscripcionTerma.objects.filter(estado='activa').count()
    print(f"\n🎯 Total de suscripciones activas: {total_activas}")
    
    # Mostrar suscripciones por plan
    for plan in PlanSuscripcion.objects.filter(activo=True):
        count = SuscripcionTerma.objects.filter(plan=plan, estado='activa').count()
        print(f"   - {plan.nombre}: {count} termas")

if __name__ == '__main__':
    asignar_suscripciones()