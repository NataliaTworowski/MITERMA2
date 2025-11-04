import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MiTerma.settings")
django.setup()

from django.core.mail import send_mail
from django.conf import settings
print("[TEST] Configuración de correo:")
print(f"[TEST] EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"[TEST] EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"[TEST] EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"[TEST] EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"[TEST] DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

try:
    print("[TEST] Intentando enviar correo de prueba...")
    send_mail(
        'Prueba de correo MiTerma',
        'Este es un correo de prueba para verificar la configuración.',
        settings.DEFAULT_FROM_EMAIL,
        [settings.EMAIL_HOST_USER],
        fail_silently=False,
    )
    print("[TEST] Correo enviado exitosamente")
except Exception as e:
    print(f"[TEST] Error al enviar correo: {str(e)}")