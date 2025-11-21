# Configuración de Variables de Entorno para Producción

## Configuración de Clave QR

Para evitar la invalidación de códigos QR al reiniciar el servidor, es CRÍTICO configurar una clave de encriptación persistente en producción.

### Generar Clave Segura

Ejecute el siguiente comando para generar una clave segura:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"QR_ENCRYPTION_KEY={key.decode()}")
```

### Configuración en Servidor de Producción

1. **Mediante variables de entorno:**
```bash
export QR_ENCRYPTION_KEY="tu_clave_generada_aquí"
```

2. **En archivo .env (si usas python-decouple):**
```
QR_ENCRYPTION_KEY=tu_clave_generada_aquí
```

3. **En Docker:**
```yaml
environment:
  - QR_ENCRYPTION_KEY=tu_clave_generada_aquí
```

### ⚠️ IMPORTANTE - SEGURIDAD

- **NUNCA** subir la clave al repositorio
- **SIEMPRE** usar la misma clave en todos los servidores de un entorno
- **HACER BACKUP** seguro de la clave
- **ROTAR** la clave periódicamente (invalidará códigos QR existentes)

### Comportamiento por Entorno

#### Desarrollo (DEBUG=True):
- Genera automáticamente una clave y la guarda en `.qr_key`
- Los códigos QR persisten entre reinicios del servidor de desarrollo
- Muestra mensaje con la clave para uso en producción

#### Producción (DEBUG=False):
- **REQUIERE** configuración de QR_ENCRYPTION_KEY
- **FALLA** si no está configurada (previene pérdida de códigos QR)
- No genera archivo local por seguridad

### Verificación

Para verificar que la clave está correctamente configurada:

```python
# En Django shell
from django.conf import settings
from cryptography.fernet import Fernet
try:
    f = Fernet(settings.QR_ENCRYPTION_KEY)
    print("✅ Clave QR configurada correctamente")
except:
    print("❌ Error en configuración de clave QR")
```