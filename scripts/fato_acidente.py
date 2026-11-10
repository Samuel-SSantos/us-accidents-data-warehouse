
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — FATOACIDENTE ===")

try:
    # Conferimos as dependências antes de iniciar.
    tabelas = [
        "StagingAcidentes",
        "DimData",
        "DimHora",
        "DimLocalizacao",
        "DimCondicaoClimatica",
        "DimLuminosidade",
        "DimSeveridade",
        "DimVia",
        "DimFonte"
    ]

    existentes = {
        linha[0]
        for linha in con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()
    }

    for tabela in tabelas:
        assert tabela in existentes, (
            f"Tabela ausente: {tabela}"
        )

    print("Todas as tabelas necessárias estão disponíveis.")

    # Condições das 13 características viárias.
    campos_via = [
        "Amenity", "Bump", "Crossing", "Give_Way",
        "Junction", "No_Exit", "Railway", "Roundabout",
        "Station", "Stop", "Traffic_Calming",
        "Traffic_Signal", "Turning_Loop"
    ]

    condicao_via = " AND ".join(
        f'TRY_CAST(s."{campo}" AS BOOLEAN) '
        f'IS NOT DISTINCT FROM v."{campo}"'
        for campo in campos_via
    )

    # A tabela candidata é criada separadamente.
    # A FatoAcidente definitiva permanece intacta
    # até que todas as verificações sejam aprovadas.

    print("\nConstruindo FatoAcidente_Candidata...")
    print("Aguarde: são mais de 7,7 milhões de registros.")

    con.execute(f"""
        CREATE OR REPLACE TABLE FatoAcidente_Candidata AS

        SELECT
            s.Accident_ID,

            d.DataKey,
            h.HoraKey,
            l.LocalizacaoKey,
            c.ClimaKey,
            lu.LuminosidadeKey,
            sv.SeveridadeKey,
            v.ViaKey,
            f.FonteKey,

            1 AS Accident_Count,

            s.Duration_Minutes,
            s.Distance_km,
            s.Temperature_C,
            s.Wind_Chill_C,
            s.Humidity_Pct,
            s.Pressure_hPa,
            s.Visibility_km,
            s.Wind_Speed_kmh,
            s.Precipitation_mm,

            s.Duration_Suspect,
            s.Temperature_Suspect

        FROM StagingAcidentes s

        LEFT JOIN DimData d
            ON d.DataKey = CAST(
                STRFTIME(s.Start_Time, '%Y%m%d')
                AS INTEGER
            )

        LEFT JOIN DimHora h
            ON h.HoraKey = (
                EXTRACT(HOUR FROM s.Start_Time) * 100
                + EXTRACT(MINUTE FROM s.Start_Time)
            )

        LEFT JOIN DimLocalizacao l
            ON s.Country IS NOT DISTINCT FROM l.Country
           AND s.State IS NOT DISTINCT FROM l.State
           AND s.County IS NOT DISTINCT FROM l.County
           AND s.City IS NOT DISTINCT FROM l.City
           AND s.Zipcode IS NOT DISTINCT FROM l.Zipcode

        LEFT JOIN DimCondicaoClimatica c
            ON s.Weather_Condition
               IS NOT DISTINCT FROM c.Weather_Condition
           AND s.Wind_Direction
               IS NOT DISTINCT FROM c.Wind_Direction

        LEFT JOIN DimLuminosidade lu
            ON s.Sunrise_Sunset
               IS NOT DISTINCT FROM lu.Sunrise_Sunset
           AND s.Civil_Twilight
               IS NOT DISTINCT FROM lu.Civil_Twilight
           AND s.Nautical_Twilight
               IS NOT DISTINCT FROM lu.Nautical_Twilight
           AND s.Astronomical_Twilight
               IS NOT DISTINCT FROM lu.Astronomical_Twilight

        LEFT JOIN DimSeveridade sv
            ON s.Severity IS NOT DISTINCT FROM sv.Severity

        LEFT JOIN DimVia v
            ON {condicao_via}

        LEFT JOIN DimFonte f
            ON s.Source IS NOT DISTINCT FROM f.Source
    """)

    print("\nValidando a tabela candidata...")

    chaves = [
        "DataKey", "HoraKey", "LocalizacaoKey",
        "ClimaKey", "LuminosidadeKey",
        "SeveridadeKey", "ViaKey", "FonteKey"
    ]

    verificacoes = ",\n".join(
        f'COUNT(*) FILTER (WHERE "{chave}" IS NULL)'
        for chave in chaves
    )

    resultado = con.execute(f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT Accident_ID),
            SUM(Accident_Count),
            COUNT(*) FILTER (
                WHERE Accident_ID IS NULL
            ),
            {verificacoes}
        FROM FatoAcidente_Candidata
    """).fetchone()

    total, ids_unicos, soma, ids_nulos = resultado[:4]
    chaves_nulas = resultado[4:]

    print("Registros:", total)
    print("IDs únicos:", ids_unicos)
    print("Soma de Accident_Count:", soma)
    print("IDs nulos:", ids_nulos)

    assert total == ESPERADO
    assert ids_unicos == ESPERADO
    assert soma == ESPERADO
    assert ids_nulos == 0

    print("\nIntegridade das chaves estrangeiras:")

    for chave, quantidade in zip(chaves, chaves_nulas):
        print(f"{chave}: {quantidade} nulas")
        assert quantidade == 0, (
            f"Falha na associação: {chave}"
        )

    # Confirma que os indicadores de qualidade
    # continuam iguais aos da STAGING.
    qualidade = con.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE Temperature_Suspect = TRUE
            ),
            COUNT(*) FILTER (
                WHERE Duration_Suspect = TRUE
            )
        FROM FatoAcidente_Candidata
    """).fetchone()

    print("\nIndicadores de qualidade:")
    print("Temperaturas suspeitas:", qualidade[0])
    print("Durações suspeitas:", qualidade[1])

    assert qualidade == (22, 6824)

    # Publicação transacional.
    # Se houver erro, a tabela definitiva anterior
    # não será substituída.

    print("\nPublicando FatoAcidente...")

    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE FatoAcidente AS
            SELECT * FROM FatoAcidente_Candidata
        """)

        con.execute("""
            DROP TABLE FatoAcidente_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nFatoAcidente publicada com sucesso.")
    print("STAGING e as 8 dimensões preservadas.")
    print("CARGA DA TABELA FATO CONCLUÍDA.")

finally:
    con.close()
