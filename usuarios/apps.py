from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'
    
    def ready(self):
        """Se ejecuta cuando la app está lista"""
        # Importar signals para que se registren
        from . import signals
        
        # Configurar signals de Terma después de que todas las apps estén cargadas
        signals.setup_terma_signals()
