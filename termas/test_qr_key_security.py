"""
Test de seguridad para verificar gestión segura de claves QR.
"""
import os
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from django.conf import settings
from cryptography.fernet import Fernet


class QRKeySecurityTest(TestCase):
    """Tests para verificar gestión segura de claves QR."""
    
    def test_qr_key_persistence(self):
        """Verificar que la clave QR es persistente entre 'reinicios'."""
        # Simular primera carga
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock del BASE_DIR para este test
            test_base_dir = Path(temp_dir)
            key_file = test_base_dir / '.qr_key'
            
            # Simular configuración de settings sin variable de entorno
            original_env = os.environ.get('QR_ENCRYPTION_KEY')
            if 'QR_ENCRYPTION_KEY' in os.environ:
                del os.environ['QR_ENCRYPTION_KEY']
            
            try:
                # Importar la función después de limpiar el entorno
                from MiTerma.settings import get_or_create_qr_key
                
                # Primera llamada - debería generar y guardar clave
                with override_settings(BASE_DIR=test_base_dir, DEBUG=True):
                    key1 = get_or_create_qr_key()
                
                # Verificar que se creó el archivo
                self.assertTrue(key_file.exists(), "Archivo .qr_key debe crearse")
                
                # Verificar que la clave es válida
                fernet1 = Fernet(key1)
                test_data = b"test_data"
                encrypted = fernet1.encrypt(test_data)
                decrypted = fernet1.decrypt(encrypted)
                self.assertEqual(test_data, decrypted)
                
                # Segunda llamada - debería cargar la misma clave
                with override_settings(BASE_DIR=test_base_dir, DEBUG=True):
                    key2 = get_or_create_qr_key()
                
                # Las claves deben ser idénticas
                self.assertEqual(key1, key2, "La clave debe persistir entre 'reinicios'")
                
                # Verificar que ambas claves pueden desencriptar los mismos datos
                fernet2 = Fernet(key2)
                decrypted2 = fernet2.decrypt(encrypted)
                self.assertEqual(test_data, decrypted2)
                
            finally:
                # Restaurar variable de entorno original
                if original_env:
                    os.environ['QR_ENCRYPTION_KEY'] = original_env
    
    def test_qr_key_from_environment(self):
        """Verificar que se usa la clave de la variable de entorno si está presente."""
        # Generar clave de prueba
        test_key = Fernet.generate_key()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_base_dir = Path(temp_dir)
            
            # Configurar variable de entorno
            with override_settings(BASE_DIR=test_base_dir):
                os.environ['QR_ENCRYPTION_KEY'] = test_key.decode()
                
                try:
                    from MiTerma.settings import get_or_create_qr_key
                    
                    # Debería usar la clave del entorno
                    key = get_or_create_qr_key()
                    self.assertEqual(key, test_key)
                    
                    # No debería crear archivo local
                    key_file = test_base_dir / '.qr_key'
                    self.assertFalse(key_file.exists(), 
                                   "No debe crear archivo local si hay variable de entorno")
                    
                finally:
                    # Limpiar variable de entorno
                    if 'QR_ENCRYPTION_KEY' in os.environ:
                        del os.environ['QR_ENCRYPTION_KEY']
    
    def test_production_requires_environment_key(self):
        """Verificar que en producción se requiere variable de entorno."""
        # Limpiar variable de entorno
        original_env = os.environ.get('QR_ENCRYPTION_KEY')
        if 'QR_ENCRYPTION_KEY' in os.environ:
            del os.environ['QR_ENCRYPTION_KEY']
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_base_dir = Path(temp_dir)
                
                from MiTerma.settings import get_or_create_qr_key
                
                # En producción (DEBUG=False) sin variable de entorno debe fallar
                with override_settings(BASE_DIR=test_base_dir, DEBUG=False):
                    with self.assertRaises(ValueError) as cm:
                        get_or_create_qr_key()
                    
                    self.assertIn("QR_ENCRYPTION_KEY no configurada", str(cm.exception))
                    
        finally:
            # Restaurar variable de entorno
            if original_env:
                os.environ['QR_ENCRYPTION_KEY'] = original_env
    
    def test_current_settings_qr_key_valid(self):
        """Verificar que la clave QR actual en settings es válida."""
        key = settings.QR_ENCRYPTION_KEY
        
        # Verificar que es un bytes válido
        self.assertIsInstance(key, bytes)
        
        # Verificar que puede usarse con Fernet
        fernet = Fernet(key)
        
        # Probar encriptación/desencriptación
        test_data = b"test_qr_code_data"
        encrypted = fernet.encrypt(test_data)
        decrypted = fernet.decrypt(encrypted)
        
        self.assertEqual(test_data, decrypted)