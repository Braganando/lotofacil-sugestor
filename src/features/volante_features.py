from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd

IN_PATH = Path("data/processed/lotofacil_concursos.csv")
OUT_PATH = Path("data/processed/lotofacil_features.csv")

MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
FIBONACCI = {1, 2, 3, 5, 8, 13, 21}
DIAG_PRINCIPAL = {1, 7, 13, 19, 25}
DIAG_SECUNDARIA = {5, 9, 13, 17, 21}
PADRAO_X = DIAG_PRINCIPAL | DIAG_SECUNDARIA

BASE_FEATURE_COLS = [
    "soma", "dist_soma_195", "qtd_pares", "dist_pares_equilibrio",
    "qtd_primos", "qtd_fibonacci", "qtd_baixas_1_15", "qtd_multiplos_3",
    "dezena_min", "dezena_max", "qtd_pares_consecutivos", "maior_sequencia",
    "maior_salto", "qtd_blocos", "qtd_moldura", "linhas_cheias", "linhas_vazias",
    "colunas_cheias", "colunas_vazias", "std_linhas", "std_colunas",
    "diag_principal", "diag_secundaria", "diag_max", "qtd_x_volante",
    "simetria_horizontal", "simetria_vertical", "simetria_rotacional",
    "vizinhos_ortogonais", "repetidas_anterior", "dist_repetidas_9",
]
DEZENA_FLAG_COLS = [f"tem_{n:02d}" for n in range(1, 26)]
FEATURE_COLS = BASE_FEATURE_COLS + DEZENA_FLAG_COLS


def extrair_features(
    dezenas: Iterable[int],
    dezenas_anterior: Iterable[int] | None = None,
) -> dict[str, float | int]:
    """Extrai 56 atributos (numéricos, sequenciais, geométricos 5x5, recência e flags por dezena)."""
    nums = sorted(int(d) for d in dezenas)
    if len(nums) != 15:
        raise ValueError(f"Esperadas 15 dezenas, recebidas {len(nums)}.")

    conj = set(nums)
    arr = np.array(nums, dtype=int)

    # --- 1. Atributos numéricos / aritméticos ---
    soma = int(arr.sum())
    dist_soma_195 = abs(soma - 195)
    qtd_pares = int(np.sum(arr % 2 == 0))
    dist_pares_equilibrio = abs(qtd_pares - 7.2)
    qtd_primos = len(conj & PRIMOS)
    qtd_fibonacci = len(conj & FIBONACCI)
    qtd_baixas_1_15 = int(np.sum(arr <= 15))
    qtd_multiplos_3 = int(np.sum(arr % 3 == 0))
    dezena_min = int(arr[0])
    dezena_max = int(arr[-1])

    # --- 2. Sequências consecutivas ---
    diffs = np.diff(arr)
    qtd_pares_consecutivos = int(np.sum(diffs == 1))
    maior_salto = int(np.max(diffs))
    qtd_blocos = 1 + int(np.sum(diffs > 1))

    maior_sequencia = 1
    seq_atual = 1
    for d in diffs:
        if d == 1:
            seq_atual += 1
            if seq_atual > maior_sequencia:
                maior_sequencia = seq_atual
        else:
            seq_atual = 1

    # --- 3. Geometria do volante 5x5 ---
    grid = np.zeros((5, 5), dtype=int)
    for n in nums:
        r, c = divmod(n - 1, 5)
        grid[r, c] = 1

    soma_linhas = grid.sum(axis=1)
    soma_colunas = grid.sum(axis=0)

    qtd_moldura = len(conj & MOLDURA)
    linhas_cheias = int(np.sum(soma_linhas == 5))
    linhas_vazias = int(np.sum(soma_linhas == 0))
    colunas_cheias = int(np.sum(soma_colunas == 5))
    colunas_vazias = int(np.sum(soma_colunas == 0))
    std_linhas = float(np.std(soma_linhas))
    std_colunas = float(np.std(soma_colunas))

    diag_principal = len(conj & DIAG_PRINCIPAL)
    diag_secundaria = len(conj & DIAG_SECUNDARIA)
    diag_max = max(diag_principal, diag_secundaria)
    qtd_x_volante = len(conj & PADRAO_X)

    simetria_horizontal = float(np.mean(grid == grid[:, ::-1]))
    simetria_vertical = float(np.mean(grid == grid[::-1, :]))
    simetria_rotacional = float(np.mean(grid == grid[::-1, ::-1]))

    viz_horiz = int(np.sum(grid[:, :-1] & grid[:, 1:]))
    viz_vert = int(np.sum(grid[:-1, :] & grid[1:, :]))
    vizinhos_ortogonais = viz_horiz + viz_vert

    # --- 4. Viés de recência (comparação com concurso anterior) ---
    if dezenas_anterior is not None:
        repetidas_anterior = len(conj & set(int(d) for d in dezenas_anterior))
        dist_repetidas_9 = abs(repetidas_anterior - 9)
    else:
        repetidas_anterior = np.nan
        dist_repetidas_9 = np.nan

    feats: dict[str, float | int] = {
        "soma": soma,
        "dist_soma_195": dist_soma_195,
        "qtd_pares": qtd_pares,
        "dist_pares_equilibrio": round(dist_pares_equilibrio, 2),
        "qtd_primos": qtd_primos,
        "qtd_fibonacci": qtd_fibonacci,
        "qtd_baixas_1_15": qtd_baixas_1_15,
        "qtd_multiplos_3": qtd_multiplos_3,
        "dezena_min": dezena_min,
        "dezena_max": dezena_max,
        "qtd_pares_consecutivos": qtd_pares_consecutivos,
        "maior_sequencia": maior_sequencia,
        "maior_salto": maior_salto,
        "qtd_blocos": qtd_blocos,
        "qtd_moldura": qtd_moldura,
        "linhas_cheias": linhas_cheias,
        "linhas_vazias": linhas_vazias,
        "colunas_cheias": colunas_cheias,
        "colunas_vazias": colunas_vazias,
        "std_linhas": round(std_linhas, 4),
        "std_colunas": round(std_colunas, 4),
        "diag_principal": diag_principal,
        "diag_secundaria": diag_secundaria,
        "diag_max": diag_max,
        "qtd_x_volante": qtd_x_volante,
        "simetria_horizontal": round(simetria_horizontal, 4),
        "simetria_vertical": round(simetria_vertical, 4),
        "simetria_rotacional": round(simetria_rotacional, 4),
        "vizinhos_ortogonais": vizinhos_ortogonais,
        "repetidas_anterior": repetidas_anterior,
        "dist_repetidas_9": dist_repetidas_9,
    }

    # --- 5. Indicadores individuais das 25 dezenas ---
    for n in range(1, 26):
        feats[f"tem_{n:02d}"] = 1 if n in conj else 0

    return feats


def formatar_volante(dezenas: Iterable[int]) -> str:
    """Retorna uma representação visual 5x5 do volante para inspeção no terminal."""
    conj = set(int(d) for d in dezenas)
    linhas = []
    for r in range(5):
        celulas = []
        for c in range(5):
            n = r * 5 + c + 1
            celulas.append(f"[{n:02d}]" if n in conj else "  . ")
        linhas.append(" ".join(celulas))
    return "\n".join(linhas)


def gerar_base_features(in_path: Path = IN_PATH, out_path: Path = OUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(in_path).sort_values("concurso").reset_index(drop=True)
    cols_dezenas = [f"d{i:02d}" for i in range(1, 16)]

    lista_feats = []
    dezenas_prev = None
    concurso_prev = None

    for row in df.itertuples(index=False):
        dezenas = [getattr(row, c) for c in cols_dezenas]
        prev = dezenas_prev if (concurso_prev is not None and row.concurso == concurso_prev + 1) else None
        lista_feats.append(extrair_features(dezenas, prev))
        dezenas_prev = dezenas
        concurso_prev = row.concurso

    df_feats = pd.DataFrame(lista_feats)
    df_final = pd.concat([df, df_feats], axis=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(out_path, index=False, encoding="utf-8")
    return df_final


def relatorio_exploratorio(df: pd.DataFrame) -> None:
    validos = df.dropna(subset=["indice_popularidade_14", "repetidas_anterior"]).copy()
    validos["log_pop_14"] = np.log(validos["indice_popularidade_14"])

    corrs = []
    for col in FEATURE_COLS:
        spearman = validos[col].corr(validos["indice_popularidade_14"], method="spearman")
        pearson_log = validos[col].corr(validos["log_pop_14"], method="pearson")
        corrs.append({"feature": col, "spearman": spearman, "pearson_log": pearson_log, "abs_s": abs(spearman)})

    df_corr = pd.DataFrame(corrs).sort_values("abs_s", ascending=False).drop(columns=["abs_s"])

    print(f"Base enriquecida salva em: {OUT_PATH} ({len(df)} concursos, {len(FEATURE_COLS)} features)\n")
    print("--- Top 20 correlações com Popularidade (14 acertos) ---")
    print(df_corr.head(20).to_string(index=False, float_format=lambda x: f"{x:+.4f}"))


if __name__ == "__main__":
    df_enriquecido = gerar_base_features()
    relatorio_exploratorio(df_enriquecido)