
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — AUDITORIA SEMANTICA ===")

try:
    # Comparamos cada chave com os atributos
    # originais que ela deve representar.

    campos_via = [
        "Amenity", "Bump", "Crossing", "Give_Way",
        "Junction", "No_Exit", "Railway", "Roundabout",
        "Station", "Stop", "Traffic_Calming",
        "Traffic_Signal", "Turning_Loop"
    ]

    condicoes = {
        "DimData": """
            d.DataKey = CAST(
                STRFTIME(s.Start_Time, '%Y%m%d')
                AS INTEGER
            )
        """,

        "DimHora": """
            h.HoraKey = (
                EXTRACT(HOUR FROM s.Start_Time) * 100
                + EXTRACT(MINUTE FROM s.Start_Time)
            )
        """,

        "DimLocalizacao": """
            s.Country IS NOT DISTINCT FROM l.Country
            AND s.State IS NOT DISTINCT FROM l.State
            AND s.County IS NOT DISTINCT FROM l.County
            AND s.City IS NOT DISTINCT FROM l.City
            AND s.Zipcode IS NOT DISTINCT FROM l.Zipcode
        """,

        "DimCondicaoClimatica": """
            s.Weather_Condition
                IS NOT DISTINCT FROM c.Weather_Condition
            AND s.Wind_Direction
                IS NOT DISTINCT FROM c.Wind_Direction
        """,

        "DimLuminosidade": """
            s.Sunrise_Sunset
                IS NOT DISTINCT FROM lu.Sunrise_Sunset
            AND s.Civil_Twilight
                IS NOT DISTINCT FROM lu.Civil_Twilight
            AND s.Nautical_Twilight
                IS NOT DISTINCT FROM lu.Nautical_Twilight
            AND s.Astronomical_Twilight
                IS NOT DISTINCT FROM lu.Astronomical_Twilight
        """,

        "DimSeveridade": """
            s.Severity IS NOT DISTINCT FROM sv.Severity
        """,

        "DimFonte": """
            s.Source IS NOT DISTINCT FROM fo.Source
        """
    }

    condicoes["DimVia"] = " AND ".join(
        f'TRY_CAST(s."{campo}" AS BOOLEAN) '
        f'IS NOT DISTINCT FROM v."{campo}"'
        for campo in campos_via
    )

    dimensoes = [
        ("DimData", "d", "DataKey"),
        ("DimHora", "h", "HoraKey"),
        ("DimLocalizacao", "l", "LocalizacaoKey"),
        ("DimCondicaoClimatica", "c", "ClimaKey"),
        ("DimLuminosidade", "lu", "LuminosidadeKey"),
        ("DimSeveridade", "sv", "SeveridadeKey"),
        ("DimVia", "v", "ViaKey"),
        ("DimFonte", "fo", "FonteKey")
    ]

    for tabela, alias, chave in dimensoes:
        print(f"\nVerificando {tabela}...")

        condicao = condicoes[tabela]

        total, divergencias = con.execute(f"""
            SELECT
                COUNT(*),

                COUNT(*) FILTER (
                    WHERE NOT COALESCE(
                        ({condicao}),
                        FALSE
                    )
                )

            FROM FatoAcidente f

            JOIN StagingAcidentes s
                ON f.Accident_ID = s.Accident_ID

            LEFT JOIN "{tabela}" {alias}
                ON f."{chave}" = {alias}."{chave}"
        """).fetchone()

        print("Acidentes verificados:", total)
        print("Divergências:", divergencias)

        assert total == ESPERADO
        assert divergencias == 0, (
            f"Falha semântica em {tabela}"
        )

    print("\n====================================")
    print("AUDITORIA SEMANTICA APROVADA")
    print("8 dimensões verificadas.")
    print("Nenhuma divergência encontrada.")
    print("Nenhuma tabela modificada.")
    print("====================================")

finally:
    con.close()
