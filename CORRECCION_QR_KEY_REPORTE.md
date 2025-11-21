# Corrección de Vulnerabilidad: Gestión Insegura de Claves QR

## 🚨 Problema Crítico Identificado

### Ubicación:
- **Archivo**: `MiTerma/settings.py`
- **Línea problemática**: `QR_ENCRYPTION_KEY = config('QR_ENCRYPTION_KEY', default=Fernet.generate_key())`

### Descripción del Problema:
La configuración original tenía una **vulnerabilidad crítica de gestión de claves**:

```python
# CONFIGURACIÓN INSEGURA (ANTES)
QR_ENCRYPTION_KEY = config('QR_ENCRYPTION_KEY', default=Fernet.generate_key())
```

#### Problemas:
1. **Regeneración de clave**: Cada reinicio del servidor generaba una nueva clave si no había variable de entorno
2. **Invalidación masiva**: Todos los códigos QR existentes se volvían inutilizables
3. **Pérdida de datos**: Entradas compradas con códigos QR se volvían inaccesibles
4. **Experiencia de usuario degradada**: Usuarios con códigos QR válidos no podían ingresar

---

## ✅ Solución Implementada

### 1. Nueva Función de Gestión Segura de Claves

```python
def get_or_create_qr_key():
    """
    Obtiene o crea una clave de encriptación QR persistente.
    
    Prioridad:
    1. Variable de entorno QR_ENCRYPTION_KEY
    2. Archivo de clave local .qr_key (para desarrollo)
    3. Genera nueva clave y la guarda (solo si no existe)
    """
```

### 2. Comportamiento por Entorno

#### 🔧 **Desarrollo (DEBUG=True):**
- ✅ Genera automáticamente una clave persistente
- ✅ La guarda en archivo `.qr_key` 
- ✅ Los códigos QR persisten entre reinicios
- ✅ Muestra la clave para configuración en producción

#### 🏭 **Producción (DEBUG=False):**
- ✅ **REQUIERE** variable de entorno `QR_ENCRYPTION_KEY`
- ✅ **FALLA** si no está configurada (previene pérdida de QR)
- ✅ No crea archivos locales por seguridad
- ✅ Error claro para el administrador del sistema

### 3. Medidas de Seguridad Adicionales

#### Archivo `.gitignore` actualizado:
```gitignore
# Secret keys and sensitive data
.qr_key
```

#### Validación de claves:
- Verifica que la clave sea válida para Fernet
- Manejo de errores para claves corruptas
- Regeneración automática si el archivo está corrupto

---

## 🔐 Configuración en Producción

### Generar Clave Segura:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"QR_ENCRYPTION_KEY={key.decode()}")
```

### Configurar en Servidor:
```bash
export QR_ENCRYPTION_KEY="tu_clave_generada_aquí"
```

---

## 🧪 Verificación y Testing

### Test Automatizado Creado:
- `termas/test_qr_key_security.py`
- Verifica persistencia de claves
- Valida comportamiento en desarrollo vs producción
- Comprueba encriptación/desencriptación

### Verificación Manual:
```bash
# En desarrollo - debe generar archivo .qr_key
python manage.py shell

# En producción - debe fallar sin variable de entorno
DEBUG=False python manage.py check
```

---

## 📊 Resultados de la Corrección

### ✅ **Problemas Resueltos:**

1. **Persistencia de códigos QR**: Los códigos QR ahora persisten entre reinicios
2. **Gestión segura en producción**: Requiere configuración explícita
3. **Experiencia de usuario mejorada**: No más códigos QR invalidados
4. **Seguridad reforzada**: Claves no se almacenan en repositorio

### ✅ **Beneficios Adicionales:**

1. **Configuración clara**: Documentación completa para administradores
2. **Detección temprana**: Falla rápido en producción si no está configurado
3. **Desarrollo simplificado**: Gestión automática en entorno de desarrollo
4. **Auditabilidad**: Logs claros sobre gestión de claves

---

## ⚠️ Migración y Consideraciones

### Para Sistemas Existentes:
1. **Generar clave única** para el entorno
2. **Configurar variable de entorno** antes del próximo reinicio
3. **Hacer backup** de la clave de forma segura
4. **Verificar funcionamiento** de códigos QR existentes

### Rotación de Claves:
- ⚠️ **IMPORTANTE**: Cambiar la clave invalidará todos los códigos QR existentes
- Planificar rotación durante ventanas de mantenimiento
- Notificar a usuarios sobre regeneración de códigos QR

---

## 📁 Archivos Modificados:

1. `✏️ MiTerma/settings.py` - Nueva función de gestión de claves
2. `✏️ .gitignore` - Agregado `.qr_key`
3. `➕ CONFIGURACION_QR_KEY.md` - Documentación para administradores
4. `➕ termas/test_qr_key_security.py` - Tests de seguridad

---

## 🎯 Estado Final:

✅ **VULNERABILIDAD CRÍTICA CORREGIDA**
- Gestión segura y persistente de claves QR
- Protección contra pérdida de códigos QR
- Configuración clara para producción
- Tests automatizados para verificación

*Corrección implementada el 20 de noviembre de 2025*