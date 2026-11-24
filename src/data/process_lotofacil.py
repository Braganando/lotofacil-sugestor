import json
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

DB_PATH = Path("data/raw/lotofacil.db")
OUT_PATH = Path("data/processed/lotofacil_concursos.csv")

TOTAL_COMBINACOES = 3_268_760
PROB_15 = 1 / TOTAL_COMBINACOES
PROB_14 = 150 / TOTAL_COMBINACOES


def extrair_faixas(lista_rateio: list[dict]) -> dict[int, tuple[int, float]]:
    """Mapeia faixa (1=15 acertos ... 5=11 acertos) -> (ganhadores, valor_premio)."""
    mapa = {}
    for item in lista_rateio or []:
        faixa = item.get("faixa")
        if faixa is not None:
            mapa[int(faixa)] = (
                int(item.get("numeroDeGanhadores") or 0),
                float(item.get("valorPremio") or 0.0),
            )
    return mapa


def processar_banco(db_path: Path = DB_PATH, out_path: Path = OUT_PATH) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT payload_json FROM concursos_raw ORDER BY numero ASC")

    linhas = []
    for (payload_str,) in cursor.fetchall():
        d = json.loads(payload_str)
        dezenas = sorted(int(x) for x in (d.get("listaDezenas") or []))
        if len(dezenas) != 15:
            continue

        faixas = extrair_faixas(d.get("listaRateioPremio"))
        ganh_15, prem_15 = faixas.get(1, (0, 0.0))
        ganh_14, prem_14 = faixas.get(2, (0, 0.0))
        ganh_13, prem_13 = faixas.get(3, (0, 0.0))
        ganh_12, prem_12 = faixas.get(4, (0, 0.0))
        ganh_11, prem_11 = faixas.get(5, (0, 0.0))

        registro = {
            "concurso": int(d["numero"]),
            "data_apuracao": d.get("dataApuracao"),
            "especial": int(d.get("indicadorConcursoEspecial") or 0),
            "acumulado": int(bool(d.get("acumulado"))),
            "valor_arrecadado": float(d.get("valorArrecadado") or 0.0),
            "ganhadores_15": ganh_15,
            "premio_15": prem_15,
            "ganhadores_14": ganh_14,
            "premio_14": prem_14,
            "ganhadores_13": ganh_13,
            "ganhadores_12": ganh_12,
            "ganhadores_11": ganh_11,
            "premio_11": prem_11,
        }

        for idx, dez in enumerate(dezenas, start=1):
            registro[f"d{idx:02d}"] = dez

        linhas.append(registro)

    conn.close()

    df = pd.DataFrame(linhas)
    df["data_apuracao"] = pd.to_datetime(df["data_apuracao"], format="%d/%m/%Y", errors="coerce")

    # Preço da aposta simples = metade do prêmio fixo de 11 acertos
    df["preco_aposta"] = np.where(df["premio_11"] > 0, df["premio_11"] / 2.0, np.nan)

    # Apostas equivalentes apenas quando há arrecadação registrada
    df["apostas_equivalentes"] = np.where(
        (df["valor_arrecadado"] > 0) & (df["preco_aposta"] > 0),
        df["valor_arrecadado"] / df["preco_aposta"],
        np.nan,
    )

    # Índice de popularidade: razão (ganhadores reais / ganhadores esperados ao acaso)
    df["esperados_14"] = df["apostas_equivalentes"] * PROB_14
    df["esperados_15"] = df["apostas_equivalentes"] * PROB_15

    df["indice_popularidade_14"] = df["ganhadores_14"] / df["esperados_14"]
    df["indice_popularidade_15"] = df["ganhadores_15"] / df["esperados_15"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")
    return df


def imprimir_diagnostico(df: pd.DataFrame) -> None:
    validos = df.dropna(subset=["indice_popularidade_14"])
    print(f"Total de concursos processados: {len(df)}")
    print(f"Concursos com arrecadação válida: {len(validos)} "
          f"(do concurso {int(validos['concurso'].min())} ao {int(validos['concurso'].max())})")
    print(f"Arquivo salvo em: {OUT_PATH}\n")

    print("--- Resumo estatístico (estilo summary() do artigo) ---")
    print(validos[["apostas_equivalentes", "ganhadores_14", "indice_popularidade_14", "indice_popularidade_15"]].describe().round(3))

    cols_view = ["concurso", "data_apuracao", "especial", "ganhadores_15", "ganhadores_14", "indice_popularidade_14"]
    print("\n--- 5 sorteios MAIS populares (maior crowding em 14 acertos) ---")
    print(validos.nlargest(5, "indice_popularidade_14")[cols_view].to_string(index=False))

    print("\n--- 5 sorteios MENOS populares (menor crowding em 14 acertos) ---")
    print(validos.nsmallest(5, "indice_popularidade_14")[cols_view].to_string(index=False))


if __name__ == "__main__":
    df_proc = processar_banco()
    imprimir_diagnostico(df_proc)