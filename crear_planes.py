#!/usr/bin/env python
"""
Script para crear los planes de suscripción por defecto
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import PlanSuscripcion

def crear_planes():
    """Crear los planes de suscripción por defecto"""
    
    # Plan Básico
    plan_basico, created = PlanSuscripcion.objects.get_or_create(
        nombre='Básico',
        defaults={
            'descripcion': 'Plan básico con funcionalidades esenciales. Solo pagas comisión por venta.',
            'porcentaje_comision': 5.0,
            'limite_fotos': 5,
            'posicion_preferencial': False,
            'marketing_premium': False,
            'dashboard_avanzado': False,
            'soporte_prioritario': False,
            'aparece_destacadas': False,
            'activo': True
        }
    )
    if created:
        print("✅ Plan Básico creado")
    else:
        print("📌 Plan Básico ya existe")
    
    # Plan Estándar
    plan_estandar, created = PlanSuscripcion.objects.get_or_create(
        nombre='Estándar',
        defaults={
            'descripcion': 'Plan estándar con beneficios adicionales. Solo pagas comisión por venta.',
            'porcentaje_comision': 7.5,
            'limite_fotos': 15,
            'posicion_preferencial': True,
            'marketing_premium': False,
            'dashboard_avanzado': True,
            'soporte_prioritario': False,
            'aparece_destacadas': True,
            'activo': True
        }
    )
    if created:
        print("✅ Plan Estándar creado")
    else:
        print("📌 Plan Estándar ya existe")
    
    # Plan Premium
    plan_premium, created = PlanSuscripcion.objects.get_or_create(
        nombre='Premium',
        defaults={
            'descripcion': 'Plan premium con todos los beneficios. Solo pagas comisión por venta.',
            'porcentaje_comision': 10.0,
            'limite_fotos': -1,  # Ilimitadas
            'posicion_preferencial': True,
            'marketing_premium': True,
            'dashboard_avanzado': True,
            'soporte_prioritario': True,
            'aparece_destacadas': True,
            'activo': True
        }
    )
    if created:
        print("✅ Plan Premium creado")
    else:
        print("📌 Plan Premium ya existe")
    
    print(f"\n🎯 Total de planes activos: {PlanSuscripcion.objects.filter(activo=True).count()}")

if __name__ == '__main__':
    crear_planes()