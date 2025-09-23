from django.db import migrations

def crear_roles_iniciales(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    
    # Crear rol Cliente (ID 1)
    rol_cliente, created = Rol.objects.get_or_create(
        id=1, 
        defaults={'nombre': 'Cliente'}
    )
    
    # Crear rol Administrador (ID 2)
    rol_admin, created = Rol.objects.get_or_create(
        id=2, 
        defaults={'nombre': 'Administrador'}
    )

def eliminar_roles_iniciales(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')
    Rol.objects.filter(id__in=[1, 2]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_roles_iniciales, eliminar_roles_iniciales),
    ]