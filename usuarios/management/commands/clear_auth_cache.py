"""
Comando de management para limpiar cache de autenticación.
Uso: python manage.py clear_auth_cache [opciones]
"""

from django.core.management.base import BaseCommand
from usuarios.cache_utils import clear_all_auth_cache, clear_user_cache, clear_rate_limit_cache
from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Limpia el cache de autenticación para resolver problemas de login'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Email del usuario específico para limpiar su cache',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Limpia todo el cache de autenticación',
        )
        parser.add_argument(
            '--rate-limit',
            type=str,
            help='Email del usuario para limpiar su rate limiting',
        )

    def handle(self, *args, **options):
        if options['user']:
            # Limpiar cache de usuario específico
            email = options['user']
            try:
                usuario = Usuario.objects.get(email=email)
                clear_user_cache(usuario)
                self.stdout.write(
                    self.style.SUCCESS(f'Cache limpiado para usuario: {email}')
                )
            except Usuario.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Usuario no encontrado: {email}')
                )
        
        elif options['rate_limit']:
            # Limpiar rate limiting de usuario específico
            email = options['rate_limit']
            clear_rate_limit_cache(email)
            self.stdout.write(
                self.style.SUCCESS(f'Rate limiting limpiado para usuario: {email}')
            )
        
        elif options['all']:
            # Limpiar todo el cache
            clear_all_auth_cache()
            self.stdout.write(
                self.style.SUCCESS('Todo el cache de autenticación ha sido limpiado')
            )
        
        else:
            # Sin opciones, mostrar ayuda básica
            self.stdout.write(
                self.style.WARNING('Especifica una opción:')
            )
            self.stdout.write('  --user <email>     : Limpiar cache de usuario específico')
            self.stdout.write('  --rate-limit <email> : Limpiar rate limiting de usuario')
            self.stdout.write('  --all              : Limpiar todo el cache')
            self.stdout.write('')
            self.stdout.write('Ejemplos:')
            self.stdout.write('  python manage.py clear_auth_cache --user usuario@ejemplo.com')
            self.stdout.write('  python manage.py clear_auth_cache --all')