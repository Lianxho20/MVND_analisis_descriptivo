# -*- coding: utf-8 -*-
"""
INGESTA — mvnd_limpio.csv → modelo estrella → MySQL

Este es el punto de entrada de la Capa 2 (almacenamiento):
  1. Lee el CSV limpio (salida del ETL)
  2. Construye dimensiones y hechos
  3. Inserta en MySQL (tablas dim_* y fact_autorizaciones)
"""
from __future__ import annotations

from pathlib import Path

from db.conexion import BASE, crear_engine, ejecutar_script_sql, get_config, probar_conexion

# Reutiliza transformación del cargador existente
import sys
sys.path.insert(0, str(BASE))
from cargar_modelo_estrella import (  # noqa: E402
    CSV_LIMPIO,
    cargar_csv,
    construir_dimensiones,
    construir_hechos,
    exportar_csv_tablas,
)

DDL_PATH = BASE / "sql" / "01_ddl_modelo_estrella.sql"
AJUSTES_PATH = BASE / "sql" / "03_ajustes_columnas_datos.sql"

ORDEN_CARGA = [
    "dim_fecha",
    "dim_tipo_solicitud",
    "dim_importador",
    "dim_medicamento",
    "dim_diagnostico",
    "dim_cantidad_categoria",
    "fact_autorizaciones",
]


def preparar_datos(ruta_csv: Path | None = None):
    """Transforma CSV limpio → dict de DataFrames (dims + fact)."""
    import pandas as pd

    ruta = ruta_csv or CSV_LIMPIO
    if ruta != CSV_LIMPIO:
        df = pd.read_csv(ruta, encoding="utf-8-sig")
        df["FECHA_AUTORIZACION"] = pd.to_datetime(df["FECHA_AUTORIZACION"])
    else:
        df = cargar_csv()

    dims = construir_dimensiones(df)
    fact = construir_hechos(df, dims)
    if len(fact) != len(df):
        raise ValueError(f"Ingesta: hechos {len(fact)} != origen {len(df)}")
    return dims, fact, len(df)


def crear_esquema_bd() -> None:
    """Ejecuta DDL (CREATE DATABASE + tablas + vista)."""
    if not DDL_PATH.exists():
        raise FileNotFoundError(f"No existe: {DDL_PATH}")
    ejecutar_script_sql(DDL_PATH, usar_bd=False)
    print(f"Esquema creado/actualizado — script: {DDL_PATH.name}")


def ajustar_columnas_bd() -> None:
    """Amplía VARCHAR según longitudes reales del CSV (evita error 1406)."""
    if AJUSTES_PATH.exists():
        ejecutar_script_sql(AJUSTES_PATH, usar_bd=True)
        print(f"Columnas ajustadas — script: {AJUSTES_PATH.name}")


def _ajustar_tipos(tabla, nombre: str):
    """Alinea tipos con el DDL de MySQL Workbench."""
    import pandas as pd

    t = tabla.copy()
    if nombre == "dim_fecha":
        t["id_fecha"] = t["id_fecha"].astype("int32")
        t["anio"] = t["anio"].astype("int16")
        t["mes"] = t["mes"].astype("int8")
        t["trimestre"] = t["trimestre"].astype("int8")
        t["anio_parcial"] = t["anio_parcial"].astype("int8")
    elif nombre == "fact_autorizaciones":
        for c in ("id_fecha", "id_importador", "id_medicamento", "id_diagnostico"):
            t[c] = pd.to_numeric(t[c], errors="coerce").astype("Int64")
        for c in ("id_tipo", "id_categoria", "es_urgencia", "es_combinado"):
            if c in t.columns:
                t[c] = pd.to_numeric(t[c], errors="coerce").astype("Int64")
    return t


def insertar_en_mysql(dims: dict, fact) -> None:
    """Ingesta: TRUNCATE + INSERT en tablas creadas por el DDL (Workbench)."""
    cfg = get_config()
    engine = crear_engine(incluir_bd=True)

    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
        for nombre in reversed(ORDEN_CARGA):
            conn.exec_driver_sql(f"TRUNCATE TABLE `{nombre}`")

    for nombre in ORDEN_CARGA:
        tabla = fact if nombre == "fact_autorizaciones" else dims[nombre]
        tabla = _ajustar_tipos(tabla, nombre)
        # Quitar filas inválidas en dimensiones obligatorias
        if nombre == "dim_importador":
            tabla = tabla[tabla["importador"].notna() & (tabla["importador"].astype(str).str.strip() != "")]
        if nombre == "dim_medicamento":
            tabla = tabla[tabla["ium"].notna()]
        tabla.to_sql(nombre, engine, if_exists="append", index=False, chunksize=500)
        print(f"  Ingesta MySQL <- {nombre}: {len(tabla):,} filas")

    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")

    print(f"\nIngesta completada en base: {cfg['database']}")
    print("Vista analitica: vw_autorizaciones_analitica")


def ingesta_completa(
    ruta_csv: Path | None = None,
    crear_esquema: bool = True,
    exportar_warehouse: bool = True,
) -> dict:
    """
    Pipeline completo de ingesta.

    Returns
    -------
    dict con filas_origen, ok_mysql, mensaje_conexion
    """
    ok, msg = probar_conexion()
    print(msg)
    if not ok:
        raise ConnectionError(
            "No hay conexión a MySQL. Revisa config/.env (copia desde config/env.example)."
        )

    dims, fact, n = preparar_datos(ruta_csv)
    print(f"Datos preparados desde CSV: {n:,} registros")

    if exportar_warehouse:
        print("\n--- Respaldo CSV (data/warehouse/) ---")
        exportar_csv_tablas(dims, fact)

    if crear_esquema:
        print("\n--- Crear esquema (DDL) ---")
        crear_esquema_bd()

    print("\n--- Ajustar columnas ---")
    ajustar_columnas_bd()

    print("\n--- Ingesta a MySQL ---")
    insertar_en_mysql(dims, fact)

    return {"filas_origen": n, "ok_mysql": True, "mensaje_conexion": msg}


def verificar_carga() -> None:
    """Cuenta filas en MySQL tras la ingesta."""
    import pandas as pd

    engine = crear_engine()
    tablas = ORDEN_CARGA + ["vw_autorizaciones_analitica"]
    print("\n--- Verificación post-ingesta ---")
    for t in tablas:
        try:
            n = pd.read_sql(f"SELECT COUNT(*) AS n FROM {t}", engine).iloc[0, 0]
            print(f"  {t:35} {int(n):>8,} filas")
        except Exception as e:
            print(f"  {t:35} ERROR: {e}")
