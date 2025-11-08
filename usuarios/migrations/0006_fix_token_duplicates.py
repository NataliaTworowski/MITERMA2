# Generated migration to fix token duplicates

from django.db import migrations, models
import secrets

def populate_tokens(apps, schema_editor):
    """
    Poblamos los tokens vacíos con valores únicos antes de aplicar la restricción unique.
    """
    TokenRestablecerContrasena = apps.get_model('usuarios', 'TokenRestablecerContrasena')
    
    for token in TokenRestablecerContrasena.objects.all():
        if not token.token:
            # Generar token único
            token.token = secrets.token_urlsafe(48)
            token.save()

def reverse_populate_tokens(apps, schema_editor):
    """
    Función reversa para el rollback (dejar tokens vacíos).
    """
    TokenRestablecerContrasena = apps.get_model('usuarios', 'TokenRestablecerContrasena')
    TokenRestablecerContrasena.objects.all().update(token='')

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_tokenrestablecercontrasena'),
    ]

    operations = [
        # Primero agregar el campo sin restricción unique
        migrations.AddField(
            model_name='tokenrestablecercontrasena',
            name='token',
            field=models.CharField(max_length=64, default=''),
        ),
        
        # Poblar los tokens
        migrations.RunPython(populate_tokens, reverse_populate_tokens),
        
        # Ahora hacer el campo unique
        migrations.AlterField(
            model_name='tokenrestablecercontrasena',
            name='token',
            field=models.CharField(max_length=64, unique=True),
        ),
        
        # Agregar otros campos nuevos
        migrations.AddField(
            model_name='tokenrestablecercontrasena',
            name='ip_creacion',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tokenrestablecercontrasena',
            name='user_agent',
            field=models.TextField(blank=True, null=True),
        ),
    ]