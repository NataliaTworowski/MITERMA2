from django.core.management.base import BaseCommand
from django.utils import timezone
from usuarios.models import Usuario, HistorialTrabajador

class Command(BaseCommand):
    help = 'Inicializa el historial de trabajadores para los usuarios existentes'

    def handle(self, *args, **options):
        self.stdout.write('Inicializando historial de trabajadores...')
        
        # Obtener todos los trabajadores activos que tienen una terma asignada
        trabajadores_activos = Usuario.objects.filter(
            rol__nombre='trabajador',
            terma__isnull=False,
            is_active=True
        )
        
        count = 0
        for trabajador in trabajadores_activos:
            # Verificar si ya tiene historial
            if not HistorialTrabajador.objects.filter(usuario=trabajador, terma=trabajador.terma, activo=True).exists():
                # Crear historial activo
                HistorialTrabajador.objects.create(
                    usuario=trabajador,
                    terma=trabajador.terma,
                    rol=trabajador.rol,
                    fecha_inicio=trabajador.date_joined,  # Usar fecha de registro como inicio
                    activo=True
                )
                count += 1
                self.stdout.write(f'  ✓ Creado historial para {trabajador.get_full_name()} en {trabajador.terma.nombre_terma}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Historial inicializado exitosamente. {count} registros creados.')
        )