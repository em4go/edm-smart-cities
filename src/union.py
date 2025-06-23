import duckdb, pathlib

# 1. Conecta a una base DuckDB (temporal o en disco)
con = duckdb.connect(
    "valenbici2025.duckdb"
)  # ← cambia a ":memory:" si no quieres archivo .duckdb

# 2. Ruta con todos los CSV de 2025
csv_glob = str(pathlib.Path("extracted_2025").joinpath("*.csv"))

# 3. Crea una tabla a partir de todos los CSV (AUTO_DETECT infiere tipos)
con.execute(f"""
    CREATE OR REPLACE TABLE valenbici_2025 AS
    SELECT *
           -- Extra opcional: añade un timestamp a partir del nombre de archivo
           , strptime(
                 regexp_extract(filename, '.+_(\\d{{2}}-\\d{{2}}-\\d{{4}}_\\d{{2}}-\\d{{2}}-\\d{{2}})\\.csv', 1),
                 '%d-%m-%Y_%H-%M-%S'
             ) AS snapshot_ts
    FROM read_csv_auto('{csv_glob}', filename=true, ignore_errors=true)
""")

# 4. Exporta directamente a Parquet comprimido (ZSTD por defecto)
con.execute("""
    COPY valenbici_2025
    TO 'valenbici_2025.parquet'
    (FORMAT PARQUET, COMPRESSION ZSTD);
""")

# 5. Validación rápida
rowcount = con.execute("SELECT COUNT(*) FROM valenbici_2025").fetchone()[0]
print(f"✓ Parquet creado con {rowcount:,} filas")
