-- ==========================================================================
-- Esquema de referencia (CORREGIDO) - Sistema de Gestion Farmaceutica HEV-UAGRM
-- --------------------------------------------------------------------------
-- Basado en el script del documento Fase 2 (pag. 215-229), con las
-- correcciones acordadas frente a los defectos del generador (Enterprise
-- Architect):
--   1. Claves foraneas en el lado correcto: detalle -> cabecera
--      (DETALLE_COMPRA.idCompra, no COMPRA.idDetalleCompra).
--   2. FK opcionales declaradas NULL (un MOVIMIENTO_INVENTARIO referencia
--      UN solo origen, no todos a la vez).
--   3. Montos monetarios en NUMERIC(14,4) para precision contable (RNF19),
--      cantidades en NUMERIC(12,2).
--   4. Nombres de tablas/campos conservados respecto al documento.
--
-- NOTA: Este archivo es REFERENCIA / documentacion. La base real la crean
-- las migraciones de Django (python manage.py migrate). Las tablas Django
-- usan estos mismos db_table mediante Meta.db_table.
-- ==========================================================================

-- CREATE DATABASE farmacia_db;
-- \c farmacia_db

-- ============================ SEGURIDAD ===================================

CREATE TABLE ROL (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    descripcion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PERMISO (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(80) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ROL_PERMISO (
    id SERIAL PRIMARY KEY,
    idRol INT NOT NULL REFERENCES ROL(id),
    idPermiso INT NOT NULL REFERENCES PERMISO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (idRol, idPermiso)
);

-- USUARIO: gestionado por Django (AbstractUser). El hash de contrasena
-- usa el sistema seguro de Django (PBKDF2), no VARCHAR(50).
CREATE TABLE USUARIO (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(150) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,
    apellido VARCHAR(120) NOT NULL,
    correo VARCHAR(254) NOT NULL,
    password VARCHAR(256) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    ultimoAcceso TIMESTAMP,
    fechaCreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE USUARIO_ROL (
    id SERIAL PRIMARY KEY,
    idUsuario INT NOT NULL REFERENCES USUARIO(id),
    idRol INT NOT NULL REFERENCES ROL(id),
    fechaAsignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (idUsuario, idRol)
);

-- ============================ CATALOGOS ===================================

CREATE TABLE CATEGORIA_PRODUCTO (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    descripcion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE UNIDAD_MEDIDA (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    abreviatura VARCHAR(20) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PRODUCTO (
    id SERIAL PRIMARY KEY,
    codigoProducto VARCHAR(60) NOT NULL UNIQUE,
    nombre VARCHAR(160) NOT NULL,
    descripcion TEXT,
    tipoProducto VARCHAR(40) NOT NULL,
    precioVenta NUMERIC(14,4) NOT NULL DEFAULT 0,
    costoReferencial NUMERIC(14,4) NOT NULL DEFAULT 0,
    stockMinimo NUMERIC(12,2) NOT NULL DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    fechaCreacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    idCategoriaProducto INT NOT NULL REFERENCES CATEGORIA_PRODUCTO(id),
    idUnidadMedida INT NOT NULL REFERENCES UNIDAD_MEDIDA(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================ PROVEEDORES =================================

CREATE TABLE PROVEEDOR (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(160) NOT NULL,
    nit VARCHAR(40),
    telefono VARCHAR(40),
    correo VARCHAR(254),
    direccion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== INVENTARIO Y CAPAS DE COSTO ========================

CREATE TABLE INVENTARIO_PRODUCTO (
    id SERIAL PRIMARY KEY,
    idProducto INT NOT NULL UNIQUE REFERENCES PRODUCTO(id),
    cantidadActual NUMERIC(12,2) NOT NULL DEFAULT 0,
    costoReferencial NUMERIC(14,4) NOT NULL DEFAULT 0,
    fechaActualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CAPA_COSTO (
    id SERIAL PRIMARY KEY,
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    cantidadInicial NUMERIC(12,2) NOT NULL,
    cantidadDisponible NUMERIC(12,2) NOT NULL,
    costoUnitario NUMERIC(14,4) NOT NULL,
    fechaIngreso DATE NOT NULL,
    origen VARCHAR(40) NOT NULL,        -- COMPRA / AJUSTE / IMPORTACION
    origenId INT,
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVA',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE MOVIMIENTO_INVENTARIO (
    id SERIAL PRIMARY KEY,
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    fechaMovimiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sentido VARCHAR(20) NOT NULL,            -- ENTRADA / SALIDA
    tipoMovimiento VARCHAR(40) NOT NULL,     -- COMPRA/VENTA/BAJA/AJUSTE/ANULACION/IMPORTACION
    cantidad NUMERIC(12,2) NOT NULL,
    costoUnitarioAplicado NUMERIC(14,4) NOT NULL DEFAULT 0,
    valorMovimiento NUMERIC(14,4) NOT NULL DEFAULT 0,
    motivo VARCHAR(120),
    observacion TEXT,
    referenciaTipo VARCHAR(40),
    referenciaId INT,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CONSUMO_CAPA_COSTO (
    id SERIAL PRIMARY KEY,
    idMovimientoInventario INT NOT NULL REFERENCES MOVIMIENTO_INVENTARIO(id),
    idCapaCosto INT NOT NULL REFERENCES CAPA_COSTO(id),
    cantidadConsumida NUMERIC(12,2) NOT NULL,
    costoUnitario NUMERIC(14,4) NOT NULL,
    valorConsumido NUMERIC(14,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================ COMPRAS =====================================

CREATE TABLE COMPRA (
    id SERIAL PRIMARY KEY,
    numeroOrden VARCHAR(60),
    numeroFactura VARCHAR(60),
    fechaCompra DATE NOT NULL,
    fechaRegistro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',  -- BORRADOR/CONFIRMADA/ANULADA
    totalCompra NUMERIC(14,4) NOT NULL DEFAULT 0,
    observacion TEXT,
    idProveedor INT NOT NULL REFERENCES PROVEEDOR(id),
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_COMPRA (
    id SERIAL PRIMARY KEY,
    idCompra INT NOT NULL REFERENCES COMPRA(id),      -- CORREGIDO: detalle -> cabecera
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    idUnidadMedida INT REFERENCES UNIDAD_MEDIDA(id),
    cantidad NUMERIC(12,2) NOT NULL,
    costoUnitario NUMERIC(14,4) NOT NULL,
    costoTotal NUMERIC(14,4) NOT NULL,
    fechaVencimiento DATE,
    observacion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================ VENTAS ======================================

CREATE TABLE VENTA (
    id SERIAL PRIMARY KEY,
    numeroBoleta VARCHAR(60),
    fechaVenta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipoVenta VARCHAR(40) NOT NULL DEFAULT 'VENTA',   -- VENTA / DISPENSACION
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',   -- BORRADOR/CONFIRMADA/ANULADA
    totalVenta NUMERIC(14,4) NOT NULL DEFAULT 0,
    observacion TEXT,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_VENTA (
    id SERIAL PRIMARY KEY,
    idVenta INT NOT NULL REFERENCES VENTA(id),        -- CORREGIDO
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    cantidad NUMERIC(12,2) NOT NULL,
    precioUnitario NUMERIC(14,4) NOT NULL,
    subtotal NUMERIC(14,4) NOT NULL,
    costoTotalSalida NUMERIC(14,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ANULACION_BOLETA (
    id SERIAL PRIMARY KEY,
    idVenta INT NOT NULL REFERENCES VENTA(id),        -- CORREGIDO: referencia a la venta anulada
    fechaAnulacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    motivo VARCHAR(120),
    observacion TEXT,
    restauraStock BOOLEAN NOT NULL DEFAULT TRUE,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================ BAJAS =======================================

CREATE TABLE MOTIVO_BAJA (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    descripcion VARCHAR(255),
    estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE BAJA (
    id SERIAL PRIMARY KEY,
    numeroBaja VARCHAR(60),
    fechaBaja TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
    observacion TEXT,
    idMotivoBaja INT NOT NULL REFERENCES MOTIVO_BAJA(id),
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_BAJA (
    id SERIAL PRIMARY KEY,
    idBaja INT NOT NULL REFERENCES BAJA(id),          -- CORREGIDO
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    cantidad NUMERIC(12,2) NOT NULL,
    costoTotalBaja NUMERIC(14,4) NOT NULL DEFAULT 0,
    observacion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================ AJUSTES =====================================

CREATE TABLE AJUSTE_INVENTARIO (
    id SERIAL PRIMARY KEY,
    numeroAjuste VARCHAR(60),
    fechaAjuste TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipoAjuste VARCHAR(20) NOT NULL,                  -- POSITIVO / NEGATIVO
    estado VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
    motivo VARCHAR(120),
    observacion TEXT,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_AJUSTE (
    id SERIAL PRIMARY KEY,
    idAjusteInventario INT NOT NULL REFERENCES AJUSTE_INVENTARIO(id),  -- CORREGIDO
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    cantidad NUMERIC(12,2) NOT NULL,
    costoUnitario NUMERIC(14,4) NOT NULL DEFAULT 0,
    costoTotal NUMERIC(14,4) NOT NULL DEFAULT 0,
    observacion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== KARDEX Y PERIODOS ==================================

CREATE TABLE PERIODO (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) NOT NULL,
    fechaInicio DATE NOT NULL,
    fechaFin DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'ABIERTO',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE SALDO_PERIODO (
    id SERIAL PRIMARY KEY,
    idPeriodo INT NOT NULL REFERENCES PERIODO(id),
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    saldoInicialCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldoInicialValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    saldoFinalCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldoFinalValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE KARDEX_GENERADO (
    id SERIAL PRIMARY KEY,
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    idPeriodo INT REFERENCES PERIODO(id),
    fechaInicio DATE NOT NULL,
    fechaFin DATE NOT NULL,
    fechaGeneracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    saldoInicialCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldoInicialValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    saldoFinalCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldoFinalValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_KARDEX (
    id SERIAL PRIMARY KEY,
    idKardexGenerado INT NOT NULL REFERENCES KARDEX_GENERADO(id),     -- CORREGIDO
    idMovimientoInventario INT REFERENCES MOVIMIENTO_INVENTARIO(id),
    fecha DATE NOT NULL,
    concepto VARCHAR(120) NOT NULL,
    tipoMovimiento VARCHAR(40) NOT NULL,
    costoUnitarioReferencial NUMERIC(14,4) NOT NULL DEFAULT 0,
    entradaCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    entradaValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    salidaCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    salidaValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    saldoCantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldoValor NUMERIC(14,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== IMPORTACION ========================================

CREATE TABLE IMPORTACION_ARCHIVO (
    id SERIAL PRIMARY KEY,
    tipoImportacion VARCHAR(40) NOT NULL,    -- INVENTARIO_INICIAL/COMPRAS/VENTAS/BAJAS
    nombreArchivo VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',  -- PENDIENTE/VALIDADO/CONFIRMADO/ERROR
    totalRegistros INT NOT NULL DEFAULT 0,
    registrosValidos INT NOT NULL DEFAULT 0,
    registrosObservados INT NOT NULL DEFAULT 0,
    fechaImportacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DETALLE_IMPORTACION (
    id SERIAL PRIMARY KEY,
    idImportacionArchivo INT NOT NULL REFERENCES IMPORTACION_ARCHIVO(id),  -- CORREGIDO
    numeroFila INT NOT NULL,
    datosOriginales JSONB NOT NULL,
    estadoFila VARCHAR(20) NOT NULL,        -- VALIDO / ERROR
    mensajeError TEXT,
    referenciaCreadaTipo VARCHAR(40),
    referenciaCreadaId INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE LOG_IMPORTACION (
    id SERIAL PRIMARY KEY,
    idImportacionArchivo INT NOT NULL REFERENCES IMPORTACION_ARCHIVO(id),  -- CORREGIDO
    fila INT NOT NULL,
    campo VARCHAR(80),
    valor VARCHAR(255),
    tipoError VARCHAR(60) NOT NULL,
    descripcion TEXT,
    procesado BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== REPORTES ===========================================

CREATE TABLE REPORTE (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipoReporte VARCHAR(60) NOT NULL,
    formato VARCHAR(20) NOT NULL,           -- EXCEL / PDF
    parametros JSONB,
    rutaArchivo VARCHAR(255),
    fechaGeneracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE DOCUMENTO_EXPORTADO (
    id SERIAL PRIMARY KEY,
    tipoDocumento VARCHAR(60) NOT NULL,
    nombreArchivo VARCHAR(255) NOT NULL,
    rutaArchivo VARCHAR(255),
    referenciaTipo VARCHAR(40),
    referenciaId INT,
    fechaGeneracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== ANALITICA (K-MEANS) ================================

CREATE TABLE EJECUCION_K_MEANS (
    id SERIAL PRIMARY KEY,
    numeroClusters INT NOT NULL,
    periodoInicio DATE NOT NULL,
    periodoFin DATE NOT NULL,
    variablesUsadas JSONB NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'EJECUTADO',
    fechaEjecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    idUsuario INT REFERENCES USUARIO(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CLUSTER_K_MEANS (
    id SERIAL PRIMARY KEY,
    idEjecucionKMeans INT NOT NULL REFERENCES EJECUCION_K_MEANS(id),  -- CORREGIDO
    numeroCluster INT NOT NULL,
    nombreCluster VARCHAR(80) NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PRODUCTO_CLUSTER (
    id SERIAL PRIMARY KEY,
    idClusterKMeans INT NOT NULL REFERENCES CLUSTER_K_MEANS(id),      -- CORREGIDO
    idProducto INT NOT NULL REFERENCES PRODUCTO(id),
    rotacion NUMERIC(14,4) NOT NULL DEFAULT 0,
    consumoTotal NUMERIC(14,4) NOT NULL DEFAULT 0,
    costoTotal NUMERIC(14,4) NOT NULL DEFAULT 0,
    stockActual NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===================== AUDITORIA ==========================================

CREATE TABLE TIPO_OPERACION (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(60) NOT NULL UNIQUE,
    modulo VARCHAR(60) NOT NULL,
    descripcion VARCHAR(255),
    requiereMotivo BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PARAMETRO_SISTEMA (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(80) NOT NULL UNIQUE,
    valor VARCHAR(255) NOT NULL,
    descripcion VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE BITACORA_OPERACION (
    id SERIAL PRIMARY KEY,
    idUsuario INT REFERENCES USUARIO(id),
    idTipoOperacion INT REFERENCES TIPO_OPERACION(id),
    modulo VARCHAR(60) NOT NULL,
    accion VARCHAR(60) NOT NULL,
    entidad VARCHAR(60) NOT NULL,
    idEntidad INT,
    valoresAnteriores JSONB,
    valoresNuevos JSONB,
    ipOrigen VARCHAR(60),
    fechaOperacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
