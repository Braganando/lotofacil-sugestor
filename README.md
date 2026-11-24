# Lotofácil Sugestor — Análise Comportamental e Otimização Anti-Rateio

Sistema de Ciência de Dados, Machine Learning e API Web desenvolvido em Python para analisar o comportamento dos apostadores da **Lotofácil** (Caixa Econômica Federal) e sugerir combinações estatisticamente **menos populares**, reduzindo o risco de divisão de prêmios nas faixas principais (14 e 15 acertos).

---

## Fundamentação Teórica

Este projeto é inspirado no primeiro capítulo (*"How to Beat the Lottery"*) do clássico **The New S Language: A Programming Environment for Data Analysis and Graphics** (Becker, Chambers & Wilks, 1988).

A premissa central separa dois fenômenos distintos:
1. **O sorteio é aleatório:** toda combinação de 15 dezenas entre 25 possui exatamente a mesma probabilidade matemática de ser sorteada ($1$ em $3.268.760$). Nenhum modelo preditivo é capaz de prever as próximas bolas sorteadas.
2. **O comportamento humano não é aleatório:** como as faixas de 14 e 15 acertos operam no sistema *pari-mutuel* (rateio), o valor pago a cada ganhador depende de quantas outras pessoas escolheram padrões parecidos.

O foco do projeto não é prever o sorteio, mas modelar o **Índice de Popularidade (Crowding Score)** a partir do histórico oficial da Caixa para otimizar o valor esperado *condicionado ao acerto*.

> **Aviso de transparência:** evitar combinações populares reduz a expectativa de divisão do prêmio em caso de acerto, mas **não altera a probabilidade de ganhar** nem supera a margem retida pela loteria no longo prazo. Este repositório tem finalidade educacional e de engenharia de dados aplicada.

---

## Achados Iniciais nos Dados Reais (3.408 concursos válidos)

A partir da coleta dos **3.836 concursos** oficiais via API da Caixa (3.408 com arrecadação registrada, do concurso 429 ao 3836), o índice de popularidade na faixa de 14 acertos (`ganhadores_reais / ganhadores_esperados_ao_acaso`) apresentou média calibrada em **0,988**, mediana em **0,850** e variação de **0,33x até 14,29x**.

A extração de 30 atributos do volante $5 \times 5$ revelou fortes vieses cognitivos dos apostadores:

| Atributo do Volante $5 \times 5$ | Correlação (Spearman) | Interpretação Comportamental |
| :--- | :---: | :--- |
| `std_linhas` (desvio de dezenas por linha) | **-0,5462** | Apostadores tendem a distribuir 3 dezenas por linha; jogos desbalanceados têm muito menos rateio. |
| `qtd_pares_consecutivos` | **-0,4727** | Sequências coladas (ex.: `11-12-13-14-15`) são fortemente evitadas pelo público. |
| `qtd_blocos` (grupos isolados) | **+0,4727** | Jogos visualmente "espalhados" atraem muito mais apostas. |
| `maior_sequencia` | **-0,4088** | Quanto maior a sequência consecutiva, menor o número de ganhadores dividindo o prêmio. |
| `linhas_cheias` | **-0,3186** | O público evita preencher uma linha horizontal inteira do volante. |
| `colunas_cheias` / `std_colunas` | **+0,1531 / +0,1692** | Ao contrário das linhas, apostadores costumam marcar colunas verticais completas. |

---

## Arquitetura e Estrutura do Projeto

```text
lotofacil-sugestor/
├── data/
│   ├── raw/                  # SQLite local com payloads brutos da API da Caixa (ignorado no Git)
│   └── processed/            # Bases tabulares limpas e features 5x5 extraídas (ignorado no Git)
├── notebooks/                # Análise exploratória visual (EDA)
├── src/
│   ├── data/
│   │   ├── fetch_lotofacil.py    # Coletor assíncrono e incremental da API oficial da Caixa
│   │   └── process_lotofacil.py  # Limpeza, cálculo de apostas equivalentes e índice de popularidade
│   ├── features/
│   │   └── volante_features.py   # Extrator de 30 atributos geométricos, aritméticos e de recência
│   ├── models/               # Treino de ML (LightGBM), explicabilidade (SHAP) e otimizador (em breve)
│   └── api/                  # API REST em FastAPI (em breve)
├── requirements.txt
└── README.md
```

---

## Como Executar Localmente

**Pré-requisitos:** Python 3.12+

```powershell
# 1. Clonar o repositório
git clone https://github.com/Braganando/lotofacil-sugestor.git
cd lotofacil-sugestor

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Baixar histórico oficial da Caixa (incremental)
python src/data/fetch_lotofacil.py

# 5. Processar base e calcular índice de popularidade
python src/data/process_lotofacil.py

# 6. Extrair atributos do volante 5x5 e exibir diagnóstico de correlações
python src/features/volante_features.py
```

---

## Roadmap

- [x] **Fase 1:** Coletor assíncrono incremental via API oficial da Caixa + armazenamento SQLite local
- [x] **Fase 2:** Pipeline de tratamento e cálculo calibrado do Índice de Popularidade (14 e 15 acertos)
- [x] **Fase 3:** Engenharia de atributos do volante $5 \times 5$ e validação estatística de vieses
- [ ] **Fase 4:** Análise exploratória visual (histogramas, dispersão com `LOWESS` e boxplots)
- [ ] **Fase 5:** Modelo preditivo de popularidade (`LightGBM` + validação temporal + `SHAP`) e otimizador de jogos
- [ ] **Fase 6:** Persistência em nuvem (`Supabase`), API REST (`FastAPI`) e Interface Web com volante $5 \times 5$ interativo
