
from pathlib import Path
import csv
import json

# Localização do dataset
PASTA = Path(__file__).resolve().parents[1]
ARQUIVO = PASTA / "dados" / "bruto" / "US_Accidents_March23.csv"

# Altere "dataset.csv" para o nome real do arquivo

print("=== DIAGNÓSTICO INICIAL ===")

# 1. Verificar arquivo
if not ARQUIVO.exists():
    raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO}")

tamanho_gb = ARQUIVO.stat().st_size / (1024 ** 3)
print(f"Tamanho: {tamanho_gb:.2f} GB")

# 2. Ler uma pequena amostra
with ARQUIVO.open("r", encoding="utf-8-sig", newline="") as f:
    amostra = f.read(65536)

    try:
        dialeto = csv.Sniffer().sniff(
            amostra, delimiters=",;\t|"
        )
        separador = dialeto.delimiter
    except csv.Error:
        separador = ","

    f.seek(0)
    leitor = csv.reader(f, delimiter=separador)

    cabecalho = next(leitor)
    linhas = list(
        next(leitor, None) for _ in range(5)
    )

# 3. Mostrar estrutura
print(f"Separador detectado: {repr(separador)}")
print(f"Quantidade de colunas: {len(cabecalho)}")

print("\n=== COLUNAS ===")
for indice, coluna in enumerate(cabecalho, start=1):
    print(f"{indice}. {coluna}")

print("\n=== PRIMEIRAS 5 LINHAS ===")
for linha in linhas:
    if linha is not None:
        print(linha)

# 4. Salvar metadados
saida = PASTA / "resultados"
saida.mkdir(exist_ok=True)

relatorio = {
    "arquivo": ARQUIVO.name,
    "tamanho_gb": round(tamanho_gb, 3),
    "separador": separador,
    "quantidade_colunas": len(cabecalho),
    "colunas": cabecalho
}

with (saida / "diagnostico_inicial.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(relatorio, f, indent=2, ensure_ascii=False)

print("\nDiagnóstico inicial concluído!")
