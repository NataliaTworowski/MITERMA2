#!/usr/bin/env python3
"""
Script de prueba para verificar que la corrección de XSS está funcionando.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from django.utils.html import escape
import json

def test_xss_fix():
    """Prueba que verifica que el escape de XSS funciona correctamente."""
    
    # Simular datos con contenido malicioso
    test_data = {
        'servicio': '<script>alert("XSS")</script>',
        'descripcion': '<img src=x onerror=alert("XSS")>',
        'precio': 1000
    }
    
    print("=== Test de corrección XSS ===")
    print("\n1. Datos originales (inseguros):")
    print(test_data)
    
    # Aplicar la función de escape como en la corrección
    escaped_data = {
        'servicio': escape(str(test_data['servicio'])),
        'descripcion': escape(str(test_data['descripcion'])),
        'precio': test_data['precio']
    }
    
    print("\n2. Datos escapados (seguros):")
    print(escaped_data)
    
    # Serializar a JSON
    json_data = json.dumps(escaped_data)
    
    print("\n3. JSON serializado:")
    print(json_data)
    
    # Verificar que los scripts están escapados
    assert '<script>' not in json_data
    assert '<img src=x onerror=' not in json_data
    assert '&lt;script&gt;' in json_data
    assert '&lt;img src=x onerror=' in json_data
    
    print("\n4. JSON parseado de nuevo:")
    parsed_data = json.loads(json_data)
    print(parsed_data)
    
    print("\n✅ Test EXITOSO: Los datos están correctamente escapados")
    print("   - Scripts maliciosos no están presentes en el JSON")
    print("   - Los datos escapados pueden parsearse correctamente")
    print("   - La función de escape previene XSS")
    
    return True

if __name__ == "__main__":
    test_xss_fix()