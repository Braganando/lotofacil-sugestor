from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.nonparametric.smoothers_lowess import lowess

IN_PATH = Path("data/processed/lotofacil_features.csv")
FIG_DIR = Path("docs/figures")

sns.set_theme(style="whitegrid", context="notebook")


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(IN_PATH)
    validos = df.dropna(subset=["indice_popularidade_14"]).copy()
    return df, validos


def grafico_01_histogramas(df: pd.DataFrame, validos: pd.DataFrame) -> None:
    cols_dez = [f"d{i:02d}" for i in range(1, 16)]
    todas_dezenas = df[cols_dez].values.ravel()
    contagem = pd.Series(todas_dezenas).value_counts().sort_index()
    media_esperada = len(df) * 15 / 25

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Painel A: Frequência das 25 dezenas (uniformidade do sorteio)
    axes[0].bar(contagem.index, contagem.values, color="#3b82f6", alpha=0.85, edgecolor="white")
    axes[0].axhline(media_esperada, color="#dc2626", linestyle="--", linewidth=1.8, label=f"Esperado ao acaso ({media_esperada:.0f})")
    axes[0].set_title("1A. Frequência das Dezenas Sorteadas (Sorteio Aleatório)")
    axes[0].set_xlabel("Dezena")
    axes[0].set_ylabel("Vezes sorteada")
    axes[0].set_xticks(range(1, 26))
    axes[0].set_ylim(contagem.min() * 0.92, contagem.max() * 1.05)
    axes[0].legend()

    # Painel B: Distribuição do índice de popularidade (comportamento humano)
    pop_clip = validos["indice_popularidade_14"].clip(upper=4.0)
    axes[1].hist(pop_clip, bins=45, color="#f59e0b", alpha=0.85, edgecolor="white")
    axes[1].axvline(1.0, color="#111827", linestyle="--", linewidth=1.6, label="Referência ao acaso (1,0x)")
    axes[1].axvline(validos["indice_popularidade_14"].median(), color="#dc2626", linestyle="-", linewidth=1.8,
                    label=f"Mediana ({validos['indice_popularidade_14'].median():.2f}x)")
    axes[1].set_title("1B. Índice de Popularidade nos 14 Acertos (Comportamento Humano)")
    axes[1].set_xlabel("Índice de Popularidade (limitado a 4,0x para visualização)")
    axes[1].set_ylabel("Quantidade de concursos")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_histogramas_uniformidade_e_popularidade.png", dpi=150)
    plt.close()


def grafico_02_lowess(validos: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    y = validos["indice_popularidade_14"].values

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    pares = [
        ("std_linhas", "Desvio-padrão de dezenas por linha (std_linhas)", 0.03),
        ("qtd_pares_consecutivos", "Quantidade de pares consecutivos no jogo", 0.18),
    ]

    for ax, (col, xlabel, jitter) in zip(axes, pares):
        x = validos[col].values
        x_plot = x + rng.normal(0, jitter, size=len(x))

        ax.scatter(x_plot, y, alpha=0.18, s=14, color="#2563eb", edgecolors="none", label="Concursos")

        # Curva LOWESS suavizada (estilo The New S Language)
        curva = lowess(y, x, frac=0.35, return_sorted=True)
        ax.plot(curva[:, 0], curva[:, 1], color="#dc2626", linewidth=2.6, label="Tendência LOWESS")

        ax.axhline(1.0, color="#111827", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.set_ylim(0.2, 3.2)
        ax.set_title(f"Popularidade (14 acertos) vs. {col}")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Índice de Popularidade (x)")
        ax.legend()

    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_dispersao_lowess.png", dpi=150)
    plt.close()


def grafico_03_boxplots(validos: pd.DataFrame) -> None:
    df_plot = validos.copy()
    df_plot["grupo_seq"] = df_plot["maior_sequencia"].clip(upper=6).map(
        lambda v: f"{int(v)}+" if v >= 6 else str(int(v))
    )
    ordem_seq = [str(v) for v in sorted(df_plot["maior_sequencia"].clip(upper=6).unique())]
    ordem_seq = ["6+" if v == "6" else v for v in ordem_seq]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    sns.boxplot(
        data=df_plot,
        x="linhas_cheias",
        y="indice_popularidade_14",
        ax=axes[0],
        showfliers=False,
        color="#60a5fa",
    )
    axes[0].axhline(1.0, color="#dc2626", linestyle="--", linewidth=1.3)
    axes[0].set_title("3A. Popularidade por Número de Linhas Cheias no Volante")
    axes[0].set_xlabel("Quantidade de linhas completas (5 dezenas na mesma linha)")
    axes[0].set_ylabel("Índice de Popularidade (sem outliers extremos)")

    sns.boxplot(
        data=df_plot,
        x="grupo_seq",
        y="indice_popularidade_14",
        order=ordem_seq,
        ax=axes[1],
        showfliers=False,
        color="#34d399",
    )
    axes[1].axhline(1.0, color="#dc2626", linestyle="--", linewidth=1.3)
    axes[1].set_title("3B. Popularidade pelo Tamanho da Maior Sequência")
    axes[1].set_xlabel("Tamanho da maior sequência consecutiva")
    axes[1].set_ylabel("Índice de Popularidade (sem outliers extremos)")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_boxplots_padroes.png", dpi=150)
    plt.close()


def grafico_04_mapa_calor_volante(validos: pd.DataFrame) -> pd.DataFrame:
    cols_dez = [f"d{i:02d}" for i in range(1, 16)]
    q90 = validos["indice_popularidade_14"].quantile(0.90)
    q10 = validos["indice_popularidade_14"].quantile(0.10)

    top10 = validos[validos["indice_popularidade_14"] >= q90]
    bot10 = validos[validos["indice_popularidade_14"] <= q10]

    freq_top = pd.Series(top10[cols_dez].values.ravel()).value_counts().reindex(range(1, 26), fill_value=0) / len(top10)
    freq_bot = pd.Series(bot10[cols_dez].values.ravel()).value_counts().reindex(range(1, 26), fill_value=0) / len(bot10)

    diff_pp = (freq_top - freq_bot) * 100.0  # diferença em pontos percentuais
    matriz = diff_pp.values.reshape(5, 5)
    anotacoes = np.array(
        [f"{n:02d}\n{diff_pp[n]:+.1f} pp" for n in range(1, 26)]
    ).reshape(5, 5)

    plt.figure(figsize=(7.5, 6.5))
    limite = max(abs(matriz.min()), abs(matriz.max()))
    sns.heatmap(
        matriz,
        annot=anotacoes,
        fmt="",
        cmap="RdBu_r",
        center=0,
        vmin=-limite,
        vmax=limite,
        linewidths=1.5,
        cbar_kws={"label": "Diferença de presença: Top 10% Populares - Top 10% Impopulares (p.p.)"},
    )
    plt.title("4. Volante 5x5: Dezenas Preferidas (Vermelho) vs. Evitadas (Azul)")
    plt.xticks([])
    plt.yticks([])
    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_mapa_calor_volante_5x5.png", dpi=150)
    plt.close()

    resumo = pd.DataFrame({
        "dezena": range(1, 26),
        "freq_populares_%": (freq_top.values * 100).round(1),
        "freq_impopulares_%": (freq_bot.values * 100).round(1),
        "diff_pp": diff_pp.values.round(1),
    })
    return resumo


def imprimir_resumo_numerico(validos: pd.DataFrame, resumo_volante: pd.DataFrame) -> None:
    print(f"Gráficos gerados com sucesso em: {FIG_DIR.resolve()}\n")

    print("--- Mediana da Popularidade por Linhas Cheias ---")
    print(validos.groupby("linhas_cheias")["indice_popularidade_14"].agg(["count", "median", "mean"]).round(3))

    print("\n--- Mediana da Popularidade por Maior Sequência ---")
    seq_grp = validos["maior_sequencia"].clip(upper=6)
    print(validos.groupby(seq_grp)["indice_popularidade_14"].agg(["count", "median", "mean"]).round(3))

    print("\n--- Top 5 dezenas MAIS associadas a sorteios populares (vermelho) ---")
    print(resumo_volante.nlargest(5, "diff_pp").to_string(index=False))

    print("\n--- Top 5 dezenas MAIS associadas a sorteios impopulares (azul) ---")
    print(resumo_volante.nsmallest(5, "diff_pp").to_string(index=False))


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df_all, df_valid = carregar_dados()
    grafico_01_histogramas(df_all, df_valid)
    grafico_02_lowess(df_valid)
    grafico_03_boxplots(df_valid)
    resumo_dez = grafico_04_mapa_calor_volante(df_valid)
    imprimir_resumo_numerico(df_valid, resumo_dez)