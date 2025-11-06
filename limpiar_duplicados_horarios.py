#!/usr/bin/env python
"""
Script para limpiar duplicados en HorarioDisponible antes de aplicar la migración.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from entradas.models import HorarioDisponible
from django.db.models import Min

def limpiar_duplicados():
    print("Iniciando limpieza de duplicados en HorarioDisponible...")
    
    # Obtener todos los HorarioDisponible
    horarios = HorarioDisponible.objects.all()
    total_inicial = horarios.count()
    print(f"Total de registros encontrados: {total_inicial}")
    
    # Agrupar por terma, entrada_tipo y fecha, y obtener el ID mínimo para cada grupo
    duplicados_grupos = HorarioDisponible.objects.values(
        'terma', 'entrada_tipo', 'fecha'
    ).annotate(
        min_id=Min('id')
    ).values_list('min_id', flat=True)
    
    # Eliminar todos los registros que no sean el mínimo en cada grupo
    horarios_a_mantener = list(duplicados_grupos)
    horarios_a_eliminar = HorarioDisponible.objects.exclude(id__in=horarios_a_mantener)
    
    eliminados = horarios_a_eliminar.count()
    print(f"Registros duplicados a eliminar: {eliminados}")
    
    if eliminados > 0:
        # Mostrar algunos ejemplos de duplicados
        print("\nEjemplos de duplicados encontrados:")
        for horario in horarios_a_eliminar[:5]:
            print(f"- ID {horario.id}: {horario.entrada_tipo.nombre} - {horario.fecha} (Terma ID: {horario.terma.id})")
        
        # Eliminar duplicados
        horarios_a_eliminar.delete()
        print(f"\n✅ Eliminados {eliminados} registros duplicados.")
    else:
        print("✅ No se encontraron duplicados.")
    
    # Verificar resultado final
    total_final = HorarioDisponible.objects.count()
    print(f"Total de registros después de la limpieza: {total_final}")
    
    # Verificar que no quedan duplicados
    duplicados_restantes = HorarioDisponible.objects.values(
        'terma', 'entrada_tipo', 'fecha'
    ).annotate(
        count=models.Count('id')
    ).filter(count__gt=1)
    
    if duplicados_restantes.exists():
        print("⚠️  Aún quedan duplicados:")
        for dup in duplicados_restantes:
            print(f"   - Terma {dup['terma']}, Entrada {dup['entrada_tipo']}, Fecha {dup['fecha']}: {dup['count']} registros")
    else:
        print("✅ Verificación completada: No quedan duplicados.")

if __name__ == '__main__':
    from django.db import models
    limpiar_duplicados()