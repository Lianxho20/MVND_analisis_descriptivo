# -*- coding: utf-8 -*-
"""
Punto de entrada — INGESTA de datos limpios a MySQL

Uso:
1. pip install -r requirements-db.txt
2. python ingesta_mysql.py              # DDL + datos (primera vez)
python ingesta_mysql.py --solo-datos # Solo carga (ya tienes tablas en Workbench)

Equivalente al notebook 08_Modelo_Estrella_MySQL.ipynb
"""
import argparse

from db.ingesta import ingesta_completa, verificar_carga
from db.conexion import probar_conexion


def main():
    parser = argparse.ArgumentParser(description="Ingesta MVND a MySQL")
    parser.add_argument(
        "--solo-datos",
        action="store_true",
        help="No ejecutar DDL (usar si ya creaste tablas en MySQL Workbench)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  INGESTA MVND - CSV limpio a MySQL (modelo estrella)")
    print("=" * 60)

    ok, msg = probar_conexion()
    print(msg)
    if not ok:
        print("\nConfigura la conexión en: config/.env")
        print("Plantilla: config/env.example")
        return

    ingesta_completa(
        crear_esquema=not args.solo_datos,
        exportar_warehouse=True,
    )
    verificar_carga()
    print("\nListo. En Workbench: SELECT COUNT(*) FROM fact_autorizaciones;")
    print("Power BI → mvnd_dw.vw_autorizaciones_analitica")


if __name__ == "__main__":
    main()
