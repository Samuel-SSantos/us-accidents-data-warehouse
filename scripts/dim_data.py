
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(f"Banco não encontrado: {BANCO}")

# Datas civis UTC dos equinócios e solstícios.
# A classificação é por dia, não por instante local.
# O inverno é associado ao ano em que começa.

TRANSICOES = {
    2016: ("03-20", "06-20", "09-22", "12-21"),
    2017: ("03-20", "06-21", "09-22", "12-21"),
    2018: ("03-20", "06-21", "09-23", "12-21"),
    2019: ("03-20", "06-21", "09-23", "12-22"),
    2020: ("03-20", "06-20", "09-22", "12-21"),
    2021: ("03-20", "06-21", "09-22", "12-21"),
    2022: ("03-20", "06-21", "09-23", "12-21"),
    2023: ("03-20", "06-21", "09-23", "12-22"),
}

estacoes = ("Spring", "Summer", "Autumn", "Winter")

eventos = [
    ("2015-12-22", "Winter", 2015)
]

for ano, datas in TRANSICOES.items():
    for estacao, mes_dia in zip(estacoes, datas):
        eventos.append(
            (f"{ano}-{mes_dia}", estacao, ano)
        )

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMDATA ===")

try:
    # Transições em tabela temporária.
    con.execute("""
        CREATE TEMP TABLE TransicoesAstronomicas (
            Inicio DATE,
            Season VARCHAR,
            Season_Year INTEGER
        )
    """)

    con.executemany(
        "INSERT INTO TransicoesAstronomicas VALUES (?, ?, ?)",
        eventos
    )

    # Criamos uma candidata antes de publicar.
    con.execute("""
        CREATE TEMP TABLE DimData_Candidata AS

        WITH calendario AS (
            SELECT
                CAST(dia AS DATE) AS Data
            FROM generate_series(
                DATE '2016-01-01',
                DATE '2023-03-31',
                INTERVAL 1 DAY
            ) AS t(dia)
        )

        SELECT
            CAST(strftime(c.Data, '%Y%m%d') AS INTEGER)
                AS DataKey,

            c.Data,

            YEAR(c.Data) AS Ano,
            QUARTER(c.Data) AS Trimestre,
            MONTH(c.Data) AS Mes,
            DAY(c.Data) AS Dia,

            DAYOFWEEK(c.Data) AS DiaSemana,
            strftime(c.Data, '%A') AS NomeDiaSemana,

            t.Season,
            t.Season_Year,

            CONCAT(
                t.Season,
                ' ',
                CAST(t.Season_Year AS VARCHAR)
            ) AS Season_Label

        FROM calendario c

        ASOF JOIN TransicoesAstronomicas t
            ON c.Data >= t.Inicio
    """)

    # Testes antes da publicação.
    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT DataKey),
            COUNT(*) FILTER (
                WHERE Season IS NULL
                   OR Season_Year IS NULL
            )
        FROM DimData_Candidata
    """).fetchone()

    esperado = con.execute("""
        SELECT date_diff(
            'day',
            DATE '2016-01-01',
            DATE '2023-03-31'
        ) + 1
    """).fetchone()[0]

    print("Dias esperados:", esperado)
    print("Dias criados:", total)
    print("Chaves únicas:", chaves)
    print("Estações nulas:", nulos)

    assert total == esperado
    assert chaves == total
    assert nulos == 0

    # Casos conhecidos, incluindo a virada do ano.
    testes = {
        "2021-12-15": ("Autumn", 2021),
        "2021-12-25": ("Winter", 2021),
        "2022-01-15": ("Winter", 2021),
        "2022-03-15": ("Winter", 2021),
        "2022-03-25": ("Spring", 2022),
        "2023-03-20": ("Spring", 2023),
    }

    for data, esperado in testes.items():
        resultado = con.execute("""
            SELECT Season, Season_Year
            FROM DimData_Candidata
            WHERE Data = CAST(? AS DATE)
        """, [data]).fetchone()

        assert resultado == esperado, (
            f"Erro em {data}: {resultado}"
        )

        print(data, "->", resultado)

    # Publicação protegida por transação.
    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimData AS
            SELECT * FROM DimData_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimData publicada com sucesso.")
    print("STAGING preservada.")

finally:
    con.close()
