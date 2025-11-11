from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Prueba de envío de email simple'

    def add_arguments(self, parser):
        parser.add_argument('email_destino', type=str, help='Email de destino para la prueba')

    def handle(self, *args, **options):
        email_destino = options['email_destino']
        
        self.stdout.write(f"Enviando email de prueba a: {email_destino}")
        self.stdout.write(f"Email host user: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"Email backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Default from email: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            resultado = send_mail(
                subject='Prueba de Email - MiTerma',
                message='Este es un email de prueba desde el comando de management de Django.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destino],
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Email enviado exitosamente. Resultado: {resultado}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al enviar email: {str(e)}')
            )