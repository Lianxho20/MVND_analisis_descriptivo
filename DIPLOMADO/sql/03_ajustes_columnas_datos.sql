-- Ajustes de tamaño según datos reales del INVIMA (ejecutar antes de ingesta)
USE mvnd_dw;

ALTER TABLE dim_medicamento
    MODIFY ium VARCHAR(50) NOT NULL,
    MODIFY principio_activo VARCHAR(255) NOT NULL,
    MODIFY presentacion_comercial TEXT NULL,
    MODIFY forma_farmaceutica VARCHAR(100) NULL,
    MODIFY concentracion VARCHAR(100) NULL;

ALTER TABLE dim_importador
    MODIFY importador VARCHAR(255) NOT NULL;

ALTER TABLE dim_diagnostico
    MODIFY diagnostico VARCHAR(255) NULL,
    MODIFY capitulo_cie10 VARCHAR(150) NULL,
    MODIFY codigo_cie10 VARCHAR(30) NULL;

ALTER TABLE fact_autorizaciones
    MODIFY ium VARCHAR(50) NOT NULL;
