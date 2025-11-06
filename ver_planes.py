#!/usr/bin/env python
"""
Script para ver los planes y sus límites
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import PlanSuscripcion

# Ver todos los planes
print("📋 PLANES DISPONIBLES:")
print("=" * 30)

for plan in PlanSuscripcion.objects.filter(activo=True).order_by('porcentaje_comision'):
    print(f"• {plan.nombre}:")
    print(f"  - Límite fotos: {plan.limite_fotos} ({'ilimitado' if plan.limite_fotos == -1 else 'fotos'})")
    print(f"  - Comisión: {plan.porcentaje_comision}%")
    print(f"  - Precio mensual: ${plan.precio_mensual}")
    print(f"  - Precio anual: ${plan.precio_anual}")
    print()