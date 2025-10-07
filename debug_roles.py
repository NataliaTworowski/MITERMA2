#!/usr/bin/env python
import os
import sys
import django

# Agregar el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MiTerma.settings')
django.setup()

from usuarios.models import Rol, Usuario
from termas.models import SolicitudTerma

print("=== ROLES DISPONIBLES ===")
try:
    roles = Rol.objects.all()
    if roles:
        for rol in roles:
            print(f"ID: {rol.id}, Nombre: {rol.nombre}")
    else:
        print("No hay roles en la base de datos")
except Exception as e:
    print(f"Error al obtener roles: {e}")

print("\n=== SOLICITUDES PENDIENTES ===")
try:
    solicitudes = SolicitudTerma.objects.filter(estado='pendiente')
    for solicitud in solicitudes:
        print(f"ID: {solicitud.id}, Nombre: {solicitud.nombre_terma}, Usuario: {solicitud.usuario}")
except Exception as e:
    print(f"Error al obtener solicitudes: {e}")

print("\n=== USUARIOS ADMINISTRADORES GENERALES ===")
try:
    admins = Usuario.objects.filter(rol_id=4)
    for admin in admins:
        print(f"ID: {admin.id}, Email: {admin.email}, Rol ID: {admin.rol_id}")
except Exception as e:
    print(f"Error al obtener admins: {e}")