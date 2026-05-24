-- =============================================================================
-- MODELO ESTRELLA — MVND INVIMA (2018–2026)
-- Proyecto: Entre la necesidad y la disponibilidad
-- Motor: MySQL 8+ / MariaDB
-- =============================================================================

CREATE DATABASE IF NOT EXISTS mvnd_dw
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE mvnd_dw;

-- ─── DIMENSIONES ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_fecha (
    id_fecha        INT         NOT NULL PRIMARY KEY COMMENT 'YYYYMMDD',
    fecha           DATE        NOT NULL,
    anio            SMALLINT    NOT NULL,
    mes             TINYINT     NOT NULL,
    trimestre       TINYINT     NOT NULL,
    nombre_mes      VARCHAR(10) NOT NULL,
    anio_parcial    TINYINT     NOT NULL DEFAULT 0 COMMENT '1 si año incompleto (ej. 2026)',
    UNIQUE KEY uk_fecha (fecha)
) ENGINE=InnoDB COMMENT='Dimensión calendario';

CREATE TABLE IF NOT EXISTS dim_tipo_solicitud (
    id_tipo         TINYINT     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tipo_solicitud  VARCHAR(40) NOT NULL,
    es_urgencia     TINYINT     NOT NULL DEFAULT 0,
    UNIQUE KEY uk_tipo (tipo_solicitud)
) ENGINE=InnoDB COMMENT='Paciente específico / Más de un paciente / Urgencia clínica';

CREATE TABLE IF NOT EXISTS dim_importador (
    id_importador   INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    importador      VARCHAR(255) NOT NULL,
    UNIQUE KEY uk_importador (importador)
) ENGINE=InnoDB COMMENT='Empresas importadoras autorizadas';

CREATE TABLE IF NOT EXISTS dim_medicamento (
    id_medicamento  INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    ium             VARCHAR(50) NOT NULL,
    principio_activo VARCHAR(255) NOT NULL,
    nombre_comercial VARCHAR(255) NULL,
    forma_farmaceutica VARCHAR(80) NULL,
    concentracion   VARCHAR(80) NULL,
    unidad_medida   VARCHAR(40) NULL,
    presentacion_comercial VARCHAR(255) NULL,
    es_combinado    TINYINT     NOT NULL DEFAULT 0,
    UNIQUE KEY uk_ium (ium)
) ENGINE=InnoDB COMMENT='Medicamento por código IUM';

CREATE TABLE IF NOT EXISTS dim_diagnostico (
    id_diagnostico  INT         NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo_cie10    VARCHAR(20) NULL,
    diagnostico     VARCHAR(255) NULL,
    capitulo_cie10  VARCHAR(120) NULL,
    tiene_diagnostico TINYINT   NOT NULL DEFAULT 1,
    KEY idx_cie10 (codigo_cie10),
    KEY idx_capitulo (capitulo_cie10)
) ENGINE=InnoDB COMMENT='Diagnóstico CIE-10 (incluye registro Sin diagnóstico)';

CREATE TABLE IF NOT EXISTS dim_cantidad_categoria (
    id_categoria    TINYINT     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    categoria       VARCHAR(40) NOT NULL,
    UNIQUE KEY uk_categoria (categoria)
) ENGINE=InnoDB COMMENT='Pequeña / Mediana / Grande / Muy grande';

-- ─── TABLA DE HECHOS ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact_autorizaciones (
    id_fact             BIGINT      NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_fecha            INT         NOT NULL,
    id_tipo             TINYINT     NOT NULL,
    id_importador       INT         NOT NULL,
    id_medicamento      INT         NOT NULL,
    id_diagnostico      INT         NOT NULL,
    id_categoria        TINYINT     NULL,
    cantidad            DECIMAL(12,2) NULL,
    es_urgencia         TINYINT     NOT NULL DEFAULT 0,
    es_combinado        TINYINT     NOT NULL DEFAULT 0,
    ium                 VARCHAR(20) NOT NULL COMMENT 'Dimensión degenerada (trazabilidad INVIMA)',
    CONSTRAINT fk_fact_fecha       FOREIGN KEY (id_fecha)       REFERENCES dim_fecha(id_fecha),
    CONSTRAINT fk_fact_tipo        FOREIGN KEY (id_tipo)        REFERENCES dim_tipo_solicitud(id_tipo),
    CONSTRAINT fk_fact_importador  FOREIGN KEY (id_importador)  REFERENCES dim_importador(id_importador),
    CONSTRAINT fk_fact_medicamento FOREIGN KEY (id_medicamento) REFERENCES dim_medicamento(id_medicamento),
    CONSTRAINT fk_fact_diagnostico FOREIGN KEY (id_diagnostico) REFERENCES dim_diagnostico(id_diagnostico),
    CONSTRAINT fk_fact_categoria   FOREIGN KEY (id_categoria)   REFERENCES dim_cantidad_categoria(id_categoria),
    KEY idx_fact_anio_tipo (id_fecha, id_tipo),
    KEY idx_fact_importador (id_importador),
    KEY idx_fact_medicamento (id_medicamento)
) ENGINE=InnoDB COMMENT='Hecho: una autorización de importación MVND';

-- ─── VISTA ANALÍTICA (equivalente al CSV plano para BI) ─────────────────────

CREATE OR REPLACE VIEW vw_autorizaciones_analitica AS
SELECT
    f.id_fact,
    d.fecha,
    d.anio,
    d.mes,
    d.trimestre,
    d.anio_parcial,
    t.tipo_solicitud,
    t.es_urgencia,
    i.importador,
    m.ium,
    m.principio_activo,
    m.nombre_comercial,
    m.forma_farmaceutica,
    m.concentracion,
    m.unidad_medida,
    m.presentacion_comercial,
    m.es_combinado,
    g.codigo_cie10,
    g.diagnostico,
    g.capitulo_cie10,
    c.categoria AS cantidad_categoria,
    f.cantidad,
    f.es_urgencia AS es_urgencia_fact,
    f.es_combinado AS es_combinado_fact
FROM fact_autorizaciones f
JOIN dim_fecha d              ON f.id_fecha = d.id_fecha
JOIN dim_tipo_solicitud t     ON f.id_tipo = t.id_tipo
JOIN dim_importador i         ON f.id_importador = i.id_importador
JOIN dim_medicamento m        ON f.id_medicamento = m.id_medicamento
JOIN dim_diagnostico g        ON f.id_diagnostico = g.id_diagnostico
LEFT JOIN dim_cantidad_categoria c ON f.id_categoria = c.id_categoria;
