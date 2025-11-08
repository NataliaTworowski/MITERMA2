from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import TokenRestablecerContrasena
import secrets


class Command(BaseCommand):
    help = 'Poblaclos tokens vacíos con valores únicos seguros'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra lo que se haría sin ejecutar los cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Modo DRY RUN - No se realizarán cambios'))
        
        try:
            with transaction.atomic():
                # Obtener todos los tokens sin token
                tokens_sin_token = TokenRestablecerContrasena.objects.filter(
                    token__isnull=True
                ) | TokenRestablecerContrasena.objects.filter(token='')
                
                total_tokens = tokens_sin_token.count()
                
                self.stdout.write(f'Encontrados {total_tokens} tokens sin valor de token')
                
                if not dry_run and total_tokens > 0:
                    # Generar tokens únicos para cada registro
                    for token_obj in tokens_sin_token:
                        nuevo_token = secrets.token_urlsafe(48)
                        
                        # Verificar que sea único (aunque es muy improbable que no lo sea)
                        while TokenRestablecerContrasena.objects.filter(token=nuevo_token).exists():
                            nuevo_token = secrets.token_urlsafe(48)
                        
                        token_obj.token = nuevo_token
                        token_obj.save()
                        
                        self.stdout.write(f'Token actualizado para usuario: {token_obj.usuario.email}')
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Actualizados {total_tokens} tokens')
                    )
                elif total_tokens == 0:
                    self.stdout.write(
                        self.style.SUCCESS('Todos los tokens ya tienen valores asignados')
                    )
                else:
                    self.stdout.write(f'En modo DRY RUN - Se actualizarían {total_tokens} tokens')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante la actualización: {str(e)}')
            )
            raise