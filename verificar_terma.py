#!/usr/bin/env python
"""
Script para verificar suscripciones de terma ID 1
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from termas.models import Terma, SuscripcionTerma, PlanSuscripcion

def verificar_terma_1():
    """Verificar suscripciones de la terma con ID 1"""
    
    try:
        # Obtener la terma
        terma = Terma.objects.get(id=1)
        print(f"🏔️ Terma encontrada: {terma.nombre_terma}")
        
        # Verificar suscripciones
        suscripciones = SuscripcionTerma.objects.filter(terma=terma)
        print(f"📋 Total suscripciones: {suscripciones.count()}")
        
        if suscripciones.exists():
            for s in suscripciones:
                print(f"   - Plan: {s.plan.nombre}")
                print(f"   - Estado: {s.estado}")
                print(f"   - Fecha inicio: {s.fecha_inicio}")
                print(f"   - Comisión: {s.plan.porcentaje_comision}%")
                print("   ---")
        else:
            print("❌ No tiene suscripciones")
            
            # Crear suscripción básica por defecto
            plan_basico = PlanSuscripcion.objects.filter(nombre='Básico').first()
            if plan_basico:
                from datetime import datetime, timedelta
                fecha_inicio = datetime.now().date()
                fecha_fin = fecha_inicio + timedelta(days=365)  # 1 año
                suscripcion = SuscripcionTerma.objects.create(
                    terma=terma,
                    plan=plan_basico,
                    estado='activa',
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    tipo_periodo='anual'
                )
                print(f"✅ Suscripción básica creada para {terma.nombre_terma}")
                print(f"   - Plan: {suscripcion.plan.nombre}")
                print(f"   - Comisión: {suscripcion.plan.porcentaje_comision}%")
            else:
                print("❌ No se encontró plan básico")
                
        # Verificar suscripción activa
        suscripcion_activa = SuscripcionTerma.objects.filter(
            terma=terma, 
            estado='activa'
        ).first()
        
        if suscripcion_activa:
            print(f"\n✅ Suscripción activa: {suscripcion_activa.plan.nombre}")
        else:
            print(f"\n❌ No hay suscripción activa")
            
    except Terma.DoesNotExist:
        print("❌ No se encontró la terma con ID 1")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    verificar_terma_1()