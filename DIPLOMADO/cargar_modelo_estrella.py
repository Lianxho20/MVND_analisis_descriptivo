# -*- coding: utf-8 -*-
"""
Carga mvnd_limpio.csv al modelo estrella (MySQL) o exporta tablas a data/warehouse/.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
CSV_LIMPIO = BASE / "datasets/mvnd_limpio.csv"
OUT_DIR = BASE / "data" / "warehouse"
MESES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}


def cargar_csv() -> pd.DataFrame:
    df = pd.read_csv(CSV_LIMPIO, encoding="utf-8-sig")
    df["FECHA_AUTORIZACION"] = pd.to_datetime(df["FECHA_AUTORIZACION"])
    if "ANIO_PARCIAL" not in df.columns:
        for c in df.columns:
            if "PARCIAL" in c.upper():
                df = df.rename(columns={c: "ANIO_PARCIAL"})
    return df


def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    """Valores canónicos para que dimensiones y hechos coincidan."""
    df = df.copy()
    df["IMPORTADOR"] = df["IMPORTADOR"].fillna("IMPORTADOR NO REPORTADO")
    df["PRINCIPIO_ACTIVO"] = df["PRINCIPIO_ACTIVO"].fillna("PRINCIPIO ACTIVO NO REPORTADO")
    mask_sin_ium = df["IUM"].isna() | df["IUM"].astype(str).str.upper().str.contains("SIN IUM", na=False)
    df.loc[mask_sin_ium, "IUM"] = "SIN IUM"
    df["DIAGNOSTICO"] = df["DIAGNOSTICO"].fillna("SIN DIAGNOSTICO REPORTADO")
    df["CODIGO_CIE10"] = df["CODIGO_CIE10"].fillna("SIN CODIGO")
    df["CAPITULO_CIE10"] = df["CAPITULO_CIE10"].fillna("SIN CAPITULO")
    return df


def construir_dimensiones(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = _preparar_df(df)

    fechas = df[["FECHA_AUTORIZACION", "ANIO", "MES", "TRIMESTRE", "ANIO_PARCIAL"]].drop_duplicates(
        subset=["FECHA_AUTORIZACION"]
    )
    dim_fecha = pd.DataFrame({
        "id_fecha": fechas["FECHA_AUTORIZACION"].dt.strftime("%Y%m%d").astype(int),
        "fecha": fechas["FECHA_AUTORIZACION"].dt.date,
        "anio": fechas["ANIO"],
        "mes": fechas["MES"],
        "trimestre": fechas["TRIMESTRE"],
        "nombre_mes": fechas["MES"].map(MESES),
        "anio_parcial": fechas["ANIO_PARCIAL"],
    })

    dim_tipo = (
        df[["TIPO_SOLICITUD", "ES_URGENCIA"]]
        .drop_duplicates()
        .sort_values("TIPO_SOLICITUD")
        .reset_index(drop=True)
    )
    dim_tipo.insert(0, "id_tipo", range(1, len(dim_tipo) + 1))
    dim_tipo = dim_tipo.rename(columns={
        "TIPO_SOLICITUD": "tipo_solicitud",
        "ES_URGENCIA": "es_urgencia",
    })

    dim_importador = (
        df[["IMPORTADOR"]].drop_duplicates().sort_values("IMPORTADOR").reset_index(drop=True)
    )
    dim_importador.insert(0, "id_importador", range(1, len(dim_importador) + 1))
    dim_importador = dim_importador.rename(columns={"IMPORTADOR": "importador"})

    cols_med = [
        "IUM", "PRINCIPIO_ACTIVO", "NOMBRE_COMERCIAL", "FORMA_FARMACEUTICA",
        "CONCENTRACION", "UNIDAD_MEDIDA", "PRESENTACION_COMERCIAL", "ES_COMBINADO",
    ]
    dim_medicamento = df[cols_med].drop_duplicates(subset=["IUM"]).sort_values("IUM").reset_index(drop=True)
    dim_medicamento.insert(0, "id_medicamento", range(1, len(dim_medicamento) + 1))
    dim_medicamento = dim_medicamento.rename(columns={
        "IUM": "ium",
        "PRINCIPIO_ACTIVO": "principio_activo",
        "NOMBRE_COMERCIAL": "nombre_comercial",
        "FORMA_FARMACEUTICA": "forma_farmaceutica",
        "CONCENTRACION": "concentracion",
        "UNIDAD_MEDIDA": "unidad_medida",
        "PRESENTACION_COMERCIAL": "presentacion_comercial",
        "ES_COMBINADO": "es_combinado",
    })

    dx = df[["CODIGO_CIE10", "DIAGNOSTICO", "CAPITULO_CIE10"]].copy()
    dx["tiene_diagnostico"] = (dx["DIAGNOSTICO"] != "SIN DIAGNOSTICO REPORTADO").astype(int)
    dim_diagnostico = dx.drop_duplicates(
        subset=["CODIGO_CIE10", "DIAGNOSTICO", "CAPITULO_CIE10"]
    ).reset_index(drop=True)
    dim_diagnostico.insert(0, "id_diagnostico", range(1, len(dim_diagnostico) + 1))
    dim_diagnostico = dim_diagnostico.rename(columns={
        "CODIGO_CIE10": "codigo_cie10",
        "DIAGNOSTICO": "diagnostico",
        "CAPITULO_CIE10": "capitulo_cie10",
    })

    dim_cat = (
        df[["CANTIDAD_CATEGORIA"]].dropna().drop_duplicates().sort_values("CANTIDAD_CATEGORIA")
        .reset_index(drop=True)
    )
    dim_cat.insert(0, "id_categoria", range(1, len(dim_cat) + 1))
    dim_cat = dim_cat.rename(columns={"CANTIDAD_CATEGORIA": "categoria"})

    return {
        "dim_fecha": dim_fecha,
        "dim_tipo_solicitud": dim_tipo,
        "dim_importador": dim_importador,
        "dim_medicamento": dim_medicamento,
        "dim_diagnostico": dim_diagnostico,
        "dim_cantidad_categoria": dim_cat,
    }


def construir_hechos(df: pd.DataFrame, dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    work = _preparar_df(df)
    work["id_fecha"] = work["FECHA_AUTORIZACION"].dt.strftime("%Y%m%d").astype(int)

    map_tipo = dims["dim_tipo_solicitud"].set_index("tipo_solicitud")["id_tipo"]
    map_imp = dims["dim_importador"].set_index("importador")["id_importador"]
    map_med = dims["dim_medicamento"].set_index("ium")["id_medicamento"]
    map_dx = dims["dim_diagnostico"].set_index(
        ["codigo_cie10", "diagnostico", "capitulo_cie10"]
    )["id_diagnostico"]
    map_cat = dims["dim_cantidad_categoria"].set_index("categoria")["id_categoria"]

    fact = pd.DataFrame({
        "id_fecha": work["id_fecha"],
        "id_tipo": work["TIPO_SOLICITUD"].map(map_tipo),
        "id_importador": work["IMPORTADOR"].map(map_imp),
        "id_medicamento": work["IUM"].map(map_med),
        "id_diagnostico": work.apply(
            lambda r: map_dx.get((r["CODIGO_CIE10"], r["DIAGNOSTICO"], r["CAPITULO_CIE10"])),
            axis=1,
        ),
        "id_categoria": work["CANTIDAD_CATEGORIA"].map(map_cat),
        "cantidad": work["CANTIDAD"],
        "es_urgencia": work["ES_URGENCIA"],
        "es_combinado": work["ES_COMBINADO"],
        "ium": work["IUM"],
    })

    nulos = fact[["id_tipo", "id_importador", "id_medicamento", "id_diagnostico"]].isna().sum()
    if nulos.any():
        print("  Advertencia FK nulas en hechos:", nulos.to_dict())
        fact = fact.dropna(subset=["id_tipo", "id_importador", "id_medicamento", "id_diagnostico"])

    return fact


def exportar_csv_tablas(dims: dict, fact: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in {**dims, "fact_autorizaciones": fact}.items():
        path = OUT_DIR / f"{nombre}.csv"
        tabla.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  {path.name}: {len(tabla):,} filas")
    print(f"\nTablas exportadas en: {OUT_DIR}")


def cargar_mysql(dims: dict, fact: pd.DataFrame) -> bool:
    host = os.getenv("MYSQL_HOST", "localhost")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "mvnd_dw")

    try:
        from sqlalchemy import create_engine
    except ImportError:
        print("Instala sqlalchemy y pymysql: pip install sqlalchemy pymysql")
        return False

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as e:
        print(f"No se pudo conectar a MySQL: {e}")
        return False

    orden = [
        "dim_fecha", "dim_tipo_solicitud", "dim_importador",
        "dim_medicamento", "dim_diagnostico", "dim_cantidad_categoria",
        "fact_autorizaciones",
    ]
    for nombre in orden:
        tabla = fact if nombre == "fact_autorizaciones" else dims[nombre]
        tabla.to_sql(nombre, engine, if_exists="replace", index=False, chunksize=1000)
        print(f"  MySQL ← {nombre}: {len(tabla):,} filas")
    print(f"\nCarga MySQL OK — base: {database}")
    return True


def main():
    print("=" * 60)
    print("  CARGA MODELO ESTRELLA — MVND")
    print("=" * 60)
    df = cargar_csv()
    print(f"Origen: {len(df):,} registros")

    dims = construir_dimensiones(df)
    fact = construir_hechos(df, dims)
    assert len(fact) == len(df), f"Hechos {len(fact)} != origen {len(df)}"
    print(f"Fact: {len(fact):,} | Dim fecha: {len(dims['dim_fecha'])} | Dim medicamento: {len(dims['dim_medicamento'])}")

    print("\n--- Exportar CSV (warehouse) ---")
    exportar_csv_tablas(dims, fact)

    print("\n--- MySQL (opcional) ---")
    print("Variables: MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
    if os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_LOAD", "").lower() == "1":
        cargar_mysql(dims, fact)
    else:
        print("Omitido (define MYSQL_PASSWORD o MYSQL_LOAD=1 para cargar).")
        print("Ejecuta antes: sql/01_ddl_modelo_estrella.sql en MySQL Workbench.")

    print("\nListo.")


if __name__ == "__main__":
    main()
