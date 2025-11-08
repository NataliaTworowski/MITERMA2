from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from usuarios.models import Usuario
import hashlib
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migra contraseñas existentes a hashes seguros de Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra lo que se haría sin ejecutar los cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true', 
            help='Fuerza la migración incluso para contraseñas ya hasheadas',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo DRY RUN - No se realizarán cambios'))
        
        try:
            with transaction.atomic():
                # Obtener todos los usuarios
                usuarios = Usuario.objects.all()
                total_usuarios = usuarios.count()
                
                self.stdout.write(f'Encontrados {total_usuarios} usuarios en la base de datos')
                
                usuarios_migrados = 0
                usuarios_ya_seguros = 0
                usuarios_con_error = 0
                
                for usuario in usuarios:
                    password = usuario.password
                    
                    # Verificar si ya tiene hash seguro de Django
                    if self._is_django_hash(password) and not force:
                        usuarios_ya_seguros += 1
                        continue
                    
                    # Intentar detectar tipo de hash legacy
                    password_to_hash = None
                    
                    if self._is_plain_text(password):
                        self.stdout.write(
                            self.style.WARNING(f'Contraseña en texto plano detectada para {usuario.email}')
                        )
                        password_to_hash = password
                    
                    elif self._is_md5_hash(password):
                        self.stdout.write(
                            self.style.WARNING(f'Hash MD5 legacy detectado para {usuario.email}')
                        )
                        # No podemos recuperar la contraseña original de MD5
                        # Generar una contraseña temporal y notificar
                        if not dry_run:
                            import secrets
                            temp_password = secrets.token_urlsafe(12)
                            password_to_hash = temp_password
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Contraseña temporal generada para {usuario.email}: {temp_password}'
                                )
                            )
                    
                    elif force and self._is_django_hash(password):
                        # Si forzamos y ya es hash de Django, regenerar con contraseña temporal
                        if not dry_run:
                            import secrets
                            temp_password = secrets.token_urlsafe(12)
                            password_to_hash = temp_password
                            self.stdout.write(
                                f'Contraseña temporal para usuario forzado {usuario.email}: {temp_password}'
                            )
                    
                    # Migrar si tenemos una contraseña para hashear
                    if password_to_hash and not dry_run:
                        try:
                            usuario.set_password(password_to_hash)
                            usuario.save(update_fields=['password'])
                            usuarios_migrados += 1
                            self.stdout.write(f'✓ Contraseña migrada para {usuario.email}')
                        except Exception as e:
                            usuarios_con_error += 1
                            self.stdout.write(
                                self.style.ERROR(f'Error migrando {usuario.email}: {str(e)}')
                            )
                    elif password_to_hash:
                        usuarios_migrados += 1  # Conteo para dry-run
                        self.stdout.write(f'DRY RUN: Se migraría contraseña para {usuario.email}')
                    else:
                        usuarios_con_error += 1
                        self.stdout.write(
                            self.style.WARNING(f'No se pudo determinar tipo de hash para {usuario.email}')
                        )
                
                # Resumen
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('RESUMEN DE MIGRACIÓN'))
                self.stdout.write('='*50)
                self.stdout.write(f'Total usuarios: {total_usuarios}')
                self.stdout.write(f'Usuarios migrados: {usuarios_migrados}')
                self.stdout.write(f'Usuarios ya seguros: {usuarios_ya_seguros}')
                self.stdout.write(f'Usuarios con error: {usuarios_con_error}')
                
                if not dry_run:
                    self.stdout.write(
                        self.style.SUCCESS('Migración completada exitosamente')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Ejecución en modo DRY RUN - No se realizaron cambios')
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante la migración: {str(e)}')
            )
            raise

    def _is_django_hash(self, password):
        """Verifica si es un hash de Django válido."""
        return password.startswith(('pbkdf2_', 'bcrypt', 'argon2'))
    
    def _is_plain_text(self, password):
        """Verifica si parece ser texto plano (heurística simple)."""
        # Si no empieza con identificadores de hash comunes y tiene longitud razonable
        return (
            not password.startswith(('pbkdf2_', 'bcrypt', 'argon2', '$', 'sha1$', 'md5$')) and
            8 <= len(password) <= 50 and
            not self._is_hex_hash(password)
        )
    
    def _is_md5_hash(self, password):
        """Verifica si parece ser un hash MD5."""
        return len(password) == 32 and all(c in '0123456789abcdef' for c in password.lower())
    
    def _is_hex_hash(self, password):
        """Verifica si es un hash hexadecimal (MD5, SHA1, etc.)."""
        try:
            int(password, 16)
            return len(password) in [32, 40, 64]  # MD5, SHA1, SHA256
        except ValueError:
            return False