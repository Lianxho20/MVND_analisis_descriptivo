# -*- coding: utf-8 -*-
"""Conexión a MySQL — Capa de ingesta (Data Warehouse MVND)."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / "config" / ".env"


def cargar_variables_entorno() -> None:
    """Lee config/.env si existe (formato KEY=valor)."""
    if not ENV_FILE.exists():
        return
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ[clave.strip()] = valor.strip().strip('"').strip("'")


def get_config() -> dict:
    cargar_variables_entorno()
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "root"),
        "database": os.getenv("MYSQL_DATABASE", "mvnd_dw"),
    }


def get_url_sqlalchemy(incluir_bd: bool = True) -> str:
    cfg = get_config()
    pwd = quote_plus(cfg["password"]) if cfg["password"] else ""
    auth = f"{cfg['user']}:{pwd}@" if pwd else f"{cfg['user']}@"
    host = f"{cfg['host']}:{cfg['port']}"
    if incluir_bd:
        return f"mysql+pymysql://{auth}{host}/{cfg['database']}?charset=utf8mb4"
    return f"mysql+pymysql://{auth}{host}/?charset=utf8mb4"


def crear_engine(incluir_bd: bool = True):
    from sqlalchemy import create_engine
    return create_engine(get_url_sqlalchemy(incluir_bd=incluir_bd))


def probar_conexion() -> tuple[bool, str]:
    """Prueba conectividad. Retorna (ok, mensaje)."""
    cfg = get_config()
    try:
        import pymysql
    except ImportError:
        return False, "Falta pymysql: pip install pymysql"

    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            charset="utf8mb4",
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
        conn.close()
        return True, f"Conexión OK — MySQL {version} en {cfg['host']}:{cfg['port']}"
    except Exception as e:
        return False, f"Error de conexión: {e}"


def ejecutar_script_sql(ruta_sql: Path, usar_bd: bool = False) -> None:
    """Ejecuta un .sql statement por statement (;)."""
    import pymysql

    cfg = get_config()
    sql = ruta_sql.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"] if usar_bd else None,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                if stmt.upper().startswith("USE "):
                    bd = stmt.split()[1].strip("`; ")
                    conn.select_db(bd)
                    continue
                cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()
