-- ============================================
-- ESTRUCTURA COMPLETA DE BASE DE DATOS 
-- PROYECTO MITERMA2
-- ============================================

-- ============================================
-- TABLAS DE USUARIOS
-- ============================================

-- Tabla de roles de usuarios
CREATE TABLE usuarios_rol (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla principal de usuarios
CREATE TABLE usuarios_usuario (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME,
    is_superuser BOOLEAN DEFAULT FALSE,
    email VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    telefono VARCHAR(20),
    estado BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    tiene_password_temporal BOOLEAN DEFAULT FALSE,
    rol_id BIGINT,
    terma_id BIGINT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_rol (rol_id),
    FOREIGN KEY (rol_id) REFERENCES usuarios_rol(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE SET NULL
);

-- Tabla de permisos de usuario
CREATE TABLE usuarios_usuario_user_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    permission_id INT NOT NULL,
    UNIQUE KEY unique_usuario_permission (usuario_id, permission_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE
);


-- Tabla de tokens para restablecer contraseña
CREATE TABLE usuarios_tokenrestablecercontrasena (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    token VARCHAR(64) UNIQUE,
    codigo VARCHAR(6) NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    usado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE
);

-- Tabla de favoritos de usuarios
CREATE TABLE usuarios_favorito (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    terma_id BIGINT NOT NULL,
    fecha_agregado DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_usuario_terma (usuario_id, terma_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de historial de trabajadores
CREATE TABLE usuarios_historialtrabajador (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    terma_id BIGINT NOT NULL,
    rol_id BIGINT NOT NULL,
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_fin DATETIME,
    motivo_fin VARCHAR(20),
    activo BOOLEAN DEFAULT TRUE,
    INDEX idx_usuario_terma (usuario_id, terma_id),
    INDEX idx_terma_activo (terma_id, activo),
    INDEX idx_usuario_activo (usuario_id, activo),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE,
    FOREIGN KEY (rol_id) REFERENCES usuarios_rol(id) ON DELETE CASCADE
);

-- ============================================
-- TABLAS DE UBICACIÓN
-- ============================================

-- Tabla de regiones
CREATE TABLE termas_region (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL
);

-- Tabla de comunas
CREATE TABLE termas_comuna (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    region_id BIGINT NOT NULL,
    FOREIGN KEY (region_id) REFERENCES termas_region(id) ON DELETE CASCADE
);

-- ============================================
-- TABLAS DE PLANES Y SUSCRIPCIONES
-- ============================================

-- Tabla de planes de suscripción
CREATE TABLE termas_plansuscripcion (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT NOT NULL,
    porcentaje_comision DECIMAL(5,2) NOT NULL,
    limite_fotos INT NOT NULL,
    posicion_preferencial BOOLEAN DEFAULT FALSE,
    marketing_premium BOOLEAN DEFAULT FALSE,
    dashboard_avanzado BOOLEAN DEFAULT FALSE,
    soporte_prioritario BOOLEAN DEFAULT FALSE,
    aparece_destacadas BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLAS DE TERMAS
-- ============================================

-- Tabla principal de termas
CREATE TABLE termas_terma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre_terma VARCHAR(100) NOT NULL,
    descripcion_terma TEXT,
    direccion_terma TEXT,
    comuna_id BIGINT,
    telefono_terma VARCHAR(20),
    email_terma VARCHAR(100),
    estado_suscripcion VARCHAR(20) DEFAULT 'inactiva',
    fecha_suscripcion DATE,
    calificacion_promedio DECIMAL(3,2),
    rut_empresa VARCHAR(12),
    limite_ventas_diario INT DEFAULT 100,
    administrador_id BIGINT,
    plan_actual_id BIGINT,
    porcentaje_comision_actual DECIMAL(5,2) DEFAULT 5.00,
    limite_fotos_actual INT DEFAULT 5,
    FOREIGN KEY (comuna_id) REFERENCES termas_comuna(id) ON DELETE SET NULL,
    FOREIGN KEY (administrador_id) REFERENCES usuarios_usuario(id) ON DELETE SET NULL,
    FOREIGN KEY (plan_actual_id) REFERENCES termas_plansuscripcion(id) ON DELETE SET NULL
);

-- Tabla de calificaciones
CREATE TABLE termas_calificacion (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    terma_id BIGINT NOT NULL,
    puntuacion INT NOT NULL,
    comentario TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de imágenes de termas
CREATE TABLE termas_imagenterma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    terma_id BIGINT NOT NULL,
    url_imagen TEXT NOT NULL,
    descripcion TEXT,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de servicios de termas
CREATE TABLE termas_servicioterma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    terma_id BIGINT NOT NULL,
    servicio VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio VARCHAR(20),
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de solicitudes de termas
CREATE TABLE termas_solicitudterma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT,
    nombre_terma VARCHAR(100) NOT NULL,
    descripcion TEXT,
    rut_empresa VARCHAR(12),
    correo_institucional VARCHAR(254),
    telefono_contacto VARCHAR(20),
    region_id BIGINT,
    comuna_id BIGINT,
    direccion TEXT,
    plan_seleccionado_id BIGINT,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP,
    terma_id BIGINT,
    motivo_rechazo TEXT,
    observaciones_admin TEXT,
    fecha_respuesta DATETIME,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (region_id) REFERENCES termas_region(id) ON DELETE SET NULL,
    FOREIGN KEY (comuna_id) REFERENCES termas_comuna(id) ON DELETE SET NULL,
    FOREIGN KEY (plan_seleccionado_id) REFERENCES termas_plansuscripcion(id) ON DELETE SET NULL,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE SET NULL
);

-- Tabla de historial de suscripciones
CREATE TABLE termas_historialsuscripcion (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    terma_id BIGINT NOT NULL,
    plan_anterior_id BIGINT,
    plan_nuevo_id BIGINT,
    fecha_cambio DATETIME DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT,
    usuario_admin_id BIGINT,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_anterior_id) REFERENCES termas_plansuscripcion(id) ON DELETE SET NULL,
    FOREIGN KEY (plan_nuevo_id) REFERENCES termas_plansuscripcion(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_admin_id) REFERENCES usuarios_usuario(id) ON DELETE SET NULL
);

-- ============================================
-- TABLAS DE ENTRADAS
-- ============================================

-- Tabla de tipos de entrada (fusionada con disponibilidad por fecha)
CREATE TABLE entradas_entradatipo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    terma_id BIGINT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    duracion_horas INT,
    duracion_tipo VARCHAR(20) DEFAULT 'dia',
    estado BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de relación entre entradas y servicios
CREATE TABLE entradas_entradatipo_servicios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entradatipo_id BIGINT NOT NULL,
    servicioterma_id BIGINT NOT NULL,
    UNIQUE KEY unique_entrada_servicio (entradatipo_id, servicioterma_id),
    FOREIGN KEY (entradatipo_id) REFERENCES entradas_entradatipo(id) ON DELETE CASCADE,
    FOREIGN KEY (servicioterma_id) REFERENCES termas_servicioterma(id) ON DELETE CASCADE
);

-- Tabla de disponibilidad diaria por tipo de entrada
CREATE TABLE entradas_disponibilidaddiaria (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entrada_tipo_id BIGINT NOT NULL,
    fecha DATE NOT NULL,
    cupos_totales INT NOT NULL,
    cupos_disponibles INT NOT NULL,
    UNIQUE KEY unique_entrada_fecha (entrada_tipo_id, fecha),
    FOREIGN KEY (entrada_tipo_id) REFERENCES entradas_entradatipo(id) ON DELETE CASCADE
);

-- ============================================
-- TABLAS DE VENTAS
-- ============================================

-- Tabla de métodos de pago
CREATE TABLE ventas_metodopago (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de compras
CREATE TABLE ventas_compra (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cantidad INT DEFAULT 1,
    usuario_id BIGINT NOT NULL,
    metodo_pago_id BIGINT,
    terma_id BIGINT,
    fecha_compra DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_visita DATE NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    estado_pago VARCHAR(20) NOT NULL,
    visible BOOLEAN DEFAULT TRUE,
    mercado_pago_id VARCHAR(100),
    codigo_confirmacion VARCHAR(100),
    pagador_email VARCHAR(254),
    monto_pagado DECIMAL(10,2),
    fecha_confirmacion_pago DATETIME,
    payment_id VARCHAR(100),
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (metodo_pago_id) REFERENCES ventas_metodopago(id) ON DELETE SET NULL,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE SET NULL
);

-- Tabla de detalles de compra
CREATE TABLE ventas_detallecompra (
    id INT PRIMARY KEY AUTO_INCREMENT,
    compra_id BIGINT NOT NULL,
    disponibilidad_diaria_id BIGINT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (compra_id) REFERENCES ventas_compra(id) ON DELETE CASCADE,
    FOREIGN KEY (disponibilidad_diaria_id) REFERENCES entradas_disponibilidaddiaria(id) ON DELETE CASCADE
);

-- Tabla de relación entre detalles de compra y servicios
CREATE TABLE ventas_detallecompra_servicios (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    detallecompra_id INT NOT NULL,
    servicioterma_id BIGINT NOT NULL,
    UNIQUE KEY unique_detalle_servicio (detallecompra_id, servicioterma_id),
    FOREIGN KEY (detallecompra_id) REFERENCES ventas_detallecompra(id) ON DELETE CASCADE,
    FOREIGN KEY (servicioterma_id) REFERENCES termas_servicioterma(id) ON DELETE CASCADE
);

-- Tabla de servicios extra en detalles
CREATE TABLE ventas_servicioextradetalle (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    detalle_compra_id INT NOT NULL,
    servicio_id BIGINT NOT NULL,
    cantidad INT DEFAULT 1,
    precio_unitario DECIMAL(10,2) NOT NULL,
    UNIQUE KEY unique_detalle_servicio (detalle_compra_id, servicio_id),
    FOREIGN KEY (detalle_compra_id) REFERENCES ventas_detallecompra(id) ON DELETE CASCADE,
    FOREIGN KEY (servicio_id) REFERENCES termas_servicioterma(id) ON DELETE CASCADE
);

-- Tabla de códigos QR
CREATE TABLE ventas_codigoqr (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    compra_id BIGINT NOT NULL,
    codigo TEXT NOT NULL,
    fecha_generacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_uso DATETIME,
    usado BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (compra_id) REFERENCES ventas_compra(id) ON DELETE CASCADE
);

-- Tabla de registro de escaneos
CREATE TABLE ventas_registroescaneo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    codigo_qr_id BIGINT NOT NULL,
    fecha_escaneo DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_scanner_id BIGINT,
    exitoso BOOLEAN DEFAULT FALSE,
    mensaje VARCHAR(255),
    ip_address VARCHAR(45),
    dispositivo VARCHAR(255),
    FOREIGN KEY (codigo_qr_id) REFERENCES ventas_codigoqr(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_scanner_id) REFERENCES usuarios_usuario(id) ON DELETE SET NULL
);

-- Tabla de cupones de descuento
CREATE TABLE ventas_cupondescuento (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    descuento_porcentaje INT NOT NULL,
    fecha_vencimiento DATE,
    terma_id BIGINT,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE SET NULL
);

-- Tabla de cupones usados
CREATE TABLE ventas_cuponusado (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cupon_id BIGINT NOT NULL,
    usuario_id BIGINT NOT NULL,
    compra_id BIGINT NOT NULL,
    fecha_uso DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cupon_id) REFERENCES ventas_cupondescuento(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (compra_id) REFERENCES ventas_compra(id) ON DELETE CASCADE
);

-- Tabla de carrito de compras
CREATE TABLE ventas_carrito (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario_id BIGINT NOT NULL,
    disponibilidad_diaria_id BIGINT NOT NULL,
    cantidad INT DEFAULT 1,
    precio_unitario DECIMAL(10,2) NOT NULL,
    fecha_agregado DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (disponibilidad_diaria_id) REFERENCES entradas_disponibilidaddiaria(id) ON DELETE CASCADE
);

-- Tabla de distribución de pagos
CREATE TABLE ventas_distribucionpago (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    compra_id BIGINT NOT NULL,
    terma_id BIGINT NOT NULL,
    plan_utilizado_id BIGINT,
    monto_total DECIMAL(10,2) NOT NULL,
    porcentaje_comision DECIMAL(5,2) NOT NULL,
    monto_comision_plataforma DECIMAL(10,2) NOT NULL,
    monto_para_terma DECIMAL(10,2) NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente',
    fecha_calculo DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_procesado DATETIME,
    fecha_pago_terma DATETIME,
    observaciones TEXT,
    referencia_pago_terma VARCHAR(100),
    FOREIGN KEY (compra_id) REFERENCES ventas_compra(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_utilizado_id) REFERENCES termas_plansuscripcion(id) ON DELETE SET NULL
);

-- Tabla de historial de pagos a termas
CREATE TABLE ventas_historialpagoterma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    distribucion_id BIGINT NOT NULL,
    terma_id BIGINT NOT NULL,
    monto_pagado DECIMAL(10,2) NOT NULL,
    fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP,
    metodo_pago_usado VARCHAR(100) NOT NULL,
    referencia_externa VARCHAR(200),
    info_pago_terma JSON,
    observaciones TEXT,
    exitoso BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (distribucion_id) REFERENCES ventas_distribucionpago(id) ON DELETE CASCADE,
    FOREIGN KEY (terma_id) REFERENCES termas_terma(id) ON DELETE CASCADE
);

-- Tabla de resumen de comisiones de la plataforma
CREATE TABLE ventas_resumencomisionesplataforma (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    mes INT NOT NULL,
    año INT NOT NULL,
    total_ventas DECIMAL(12,2) DEFAULT 0,
    total_comisiones DECIMAL(12,2) DEFAULT 0,
    total_pagado_termas DECIMAL(12,2) DEFAULT 0,
    cantidad_transacciones INT DEFAULT 0,
    fecha_calculo DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_mes_año (mes, año)
);

-- ============================================
-- DATOS INICIALES
-- ============================================

-- Insertar roles por defecto
INSERT INTO usuarios_rol (nombre, descripcion, activo) VALUES
('administrador_general', 'Administrador con acceso total al sistema', TRUE),
('administrador_terma', 'Administrador de una terma específica', TRUE),
('trabajador', 'Empleado de una terma', TRUE),
('cliente', 'Cliente regular del sistema', TRUE);

-- Insertar métodos de pago por defecto
INSERT INTO ventas_metodopago (nombre, activo) VALUES
('Mercado Pago', TRUE),
('Transferencia Bancaria', TRUE),
('Efectivo', TRUE);

-- Insertar planes de suscripción por defecto
INSERT INTO termas_plansuscripcion (nombre, descripcion, porcentaje_comision, limite_fotos, posicion_preferencial, marketing_premium, dashboard_avanzado, soporte_prioritario, aparece_destacadas, activo) VALUES
('basico', 'Plan básico con funcionalidades estándar', 8.00, 5, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE),
('estandar', 'Plan estándar con beneficios adicionales', 6.00, 15, TRUE, FALSE, TRUE, FALSE, TRUE, TRUE),
('premium', 'Plan premium con todos los beneficios', 4.00, -1, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE);

-- ============================================
-- ÍNDICES ADICIONALES PARA OPTIMIZACIÓN
-- ============================================

-- Índices para consultas frecuentes
CREATE INDEX idx_compra_fecha ON ventas_compra(fecha_compra);
CREATE INDEX idx_compra_estado ON ventas_compra(estado_pago);
CREATE INDEX idx_compra_terma_fecha ON ventas_compra(terma_id, fecha_compra);
CREATE INDEX idx_disponibilidad_fecha ON entradas_disponibilidaddiaria(fecha);
CREATE INDEX idx_terma_estado ON termas_terma(estado_suscripcion);
CREATE INDEX idx_calificacion_fecha ON termas_calificacion(fecha);
CREATE INDEX idx_distribucion_estado ON ventas_distribucionpago(estado);

-- ============================================
-- COMENTARIOS FINALES
-- ============================================

/*
Esta estructura de base de datos incluye todas las tablas actualmente utilizadas en el proyecto MITERMA2:

1. USUARIOS: Gestión completa de usuarios, roles, autenticación y favoritos
2. UBICACIÓN: Regiones y comunas para geolocalización
3. TERMAS: Información completa de termas, imágenes, servicios y calificaciones
4. ENTRADAS: Tipos de entrada y disponibilidad diaria por fecha
5. VENTAS: Sistema completo de compras, pagos, carrito y distribución de comisiones
6. PLANES: Sistema de suscripciones y planes para las termas

Total de tablas: 31 tablas principales más sus tablas de relación Many-to-Many

OPTIMIZACIÓN REALIZADA:
- Se fusionó HorarioDisponible con EntradaTipo
- Se eliminaron campos no utilizados: hora_inicio, hora_fin
- Se simplificó a una tabla de disponibilidad diaria por tipo de entrada
- Los cupos se manejan por fecha, no por horarios específicos

Características principales:
- Soporte para sistema de roles y permisos
- Sistema de geolocalización con regiones/comunas
- Gestión completa de termas con imágenes y servicios
- Sistema de entradas simplificado con disponibilidad por fecha
- Carrito de compras y procesamiento de pagos
- Sistema de distribución de comisiones
- Códigos QR para validación de entradas
- Sistema de calificaciones y reseñas
- Gestión de cupones de descuento
- Historial completo de transacciones y pagos
*/