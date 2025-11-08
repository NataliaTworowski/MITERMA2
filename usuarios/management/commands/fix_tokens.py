from django.core.management.base import BaseCommand
from django.db import transaction
from usuarios.models import TokenRestablecerContrasena
import secrets


class Command(BaseCommand):
    help = 'Limpia tokens duplicados y prepara la base de datos para la migración de autenticación'

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
                # Obtener todos los tokens
                tokens = TokenRestablecerContrasena.objects.all()
                total_tokens = tokens.count()
                
                self.stdout.write(f'Encontrados {total_tokens} tokens en la base de datos')
                
                # Contar tokens vacíos
                tokens_vacios = tokens.filter(codigo='').count()
                self.stdout.write(f'Tokens con código vacío: {tokens_vacios}')
                
                if not dry_run:
                    # Eliminar tokens expirados o inválidos
                    from django.utils import timezone
                    from datetime import timedelta
                    
                    tiempo_limite = timezone.now() - timedelta(hours=1)
                    tokens_expirados = TokenRestablecerContrasena.objects.filter(
                        fecha_creacion__lt=tiempo_limite
                    )
                    count_expirados = tokens_expirados.count()
                    tokens_expirados.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Eliminados {count_expirados} tokens expirados')
                    )
                    
                    # Generar códigos únicos para tokens sin código
                    tokens_sin_codigo = TokenRestablecerContrasena.objects.filter(codigo='')
                    
                    for token in tokens_sin_codigo:
                        # Generar nuevo código único
                        import random
                        import string
                        nuevo_codigo = ''.join(random.choices(string.digits, k=6))
                        
                        # Verificar que sea único
                        while TokenRestablecerContrasena.objects.filter(codigo=nuevo_codigo).exists():
                            nuevo_codigo = ''.join(random.choices(string.digits, k=6))
                        
                        token.codigo = nuevo_codigo
                        token.save()
                    
                    tokens_actualizados = tokens_sin_codigo.count()
                    self.stdout.write(
                        self.style.SUCCESS(f'Actualizados {tokens_actualizados} tokens sin código')
                    )
                
                else:
                    self.stdout.write('En modo DRY RUN - Se eliminarían tokens expirados y se actualizarían códigos vacíos')
                
                self.stdout.write(
                    self.style.SUCCESS('Limpieza de tokens completada exitosamente')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error durante la limpieza: {str(e)}')
            )
            raise