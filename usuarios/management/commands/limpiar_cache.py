"""
Comando para limpiar automáticamente el caché de autenticación.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.contrib.sessions.models import Session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('usuarios')


class Command(BaseCommand):
    help = 'Limpia el caché de autenticación y sesiones expiradas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Limpiar todo el caché, no solo el de autenticación',
        )
        parser.add_argument(
            '--sessions',
            action='store_true',
            help='Limpiar también sesiones expiradas',
        )

    def handle(self, *args, **options):
        self.stdout.write('Iniciando limpieza de caché...')
        
        if options['all']:
            # Limpiar todo el caché
            cache.clear()
            self.stdout.write(
                self.style.SUCCESS('Todo el caché ha sido limpiado.')
            )
        else:
            # Limpiar solo cachés específicos de autenticación
            self.clean_auth_cache()
            self.stdout.write(
                self.style.SUCCESS('Caché de autenticación limpiado.')
            )
        
        if options['sessions']:
            self.clean_expired_sessions()
        
        self.stdout.write(
            self.style.SUCCESS('Limpieza completada exitosamente.')
        )

    def clean_auth_cache(self):
        """Limpia cachés específicos de autenticación"""
        # Lista de patrones de caché a limpiar
        cache_patterns = [
            'user_*',
            'auth_attempts_*',
            'user_email_*',
            'session_*'
        ]
        
        # Como Django cache no tiene delete_pattern, usamos una lista conocida
        # En producción, podrías usar Redis con SCAN para esto
        try:
            # Obtener todas las claves del caché (solo funciona con algunos backends)
            if hasattr(cache, '_cache') and hasattr(cache._cache, 'keys'):
                all_keys = cache._cache.keys()
                auth_keys = [
                    key for key in all_keys 
                    if any(pattern.replace('*', '') in str(key) for pattern in cache_patterns)
                ]
                cache.delete_many(auth_keys)
                self.stdout.write(f'Limpiadas {len(auth_keys)} claves de caché de autenticación.')
            else:
                # Fallback: limpiar todo el caché si no podemos ser selectivos
                cache.clear()
                self.stdout.write('Cache backend no soporta limpieza selectiva, limpiando todo.')
                
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}")
            # Fallback seguro
            cache.clear()
            self.stdout.write('Error en limpieza selectiva, limpiando todo el caché.')

    def clean_expired_sessions(self):
        """Limpia sesiones expiradas de la base de datos"""
        expired_sessions = Session.objects.filter(
            expire_date__lt=datetime.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'{count} sesiones expiradas eliminadas.')
        )