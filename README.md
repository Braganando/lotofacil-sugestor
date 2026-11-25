# Lotofácil Sugestor — Análise Comportamental e Otimização Anti-Rateio

Sistema de Ciência de Dados, Machine Learning e API Web desenvolvido em Python para analisar o comportamento dos apostadores da **Lotofácil** (Caixa Econômica Federal) e sugerir combinações estatisticamente **menos populares**, reduzindo o risco de divisão de prêmios nas faixas principais (14 e 15 acertos).

---

## Fundamentação Teórica

Inspirado no primeiro capítulo (*"How to Beat the Lottery"*) do clássico **The New S Language: A Programming Environment for Data Analysis and Graphics** (Becker, Chambers & Wilks, 1988), o projeto separa dois fenômenos distintos:

1. **O sorteio é aleatório:** toda combinação de 15 dezenas entre 25 possui exatamente a mesma probabilidade matemática ($1$ em $3.268.760$). Nenhum modelo prevê as próximas bolas sorteadas.
2. **O comportamento humano não é aleatório:** como as faixas de 14 e 15 acertos operam no sistema *pari-mutuel* (rateio), o prêmio individual depende de quantas outras pessoas marcaram padrões parecidos no volante.

> **Aviso de transparência:** evitar padrões populares reduz a expectativa de divisão do prêmio em caso de acerto, mas **não altera a probabilidade de ganhar** nem supera a margem retida pela loteria no longo prazo. Projeto com finalidade educacional e de engenharia de dados aplicada.

---

## Achados nos Dados Reais e Desempenho do Modelo

A partir da coleta oficial de **3.836 concursos** via API da Caixa (3.408 com arrecadação registrada, do concurso 429 ao 3836), o Índice de Popularidade nos 14 acertos (`ganhadores_reais / ganhadores_esperados_ao_acaso`) apresentou média calibrada em **0,988x**, mediana em **0,850x** e variação de **0,33x até 14,29x**.

### Vieses Comportamentais no Volante $5 \times 5$ (56 features)
| Atributo | Correlação (Spearman) | Interpretação Comportamental |
| :--- | :---: | :--- |
| `std_linhas` | **-0,5462** | Apostadores tendem a distribuir ~3 dezenas por linha; jogos desbalanceados sofrem muito menos rateio. |
| `qtd_pares_consecutivos` | **-0,4727** | Sequências coladas (ex.: `11-12-13-14-15`) são fortemente evitadas pelo público. |
| `qtd_blocos` | **+0,4727** | Jogos visualmente "espalhados" atraem muito mais apostas. |
| `maior_sequencia` | **-0,4088** | Quanto maior a sequência consecutiva, menor a divisão do prêmio. |
| `tem_06` / `tem_16` | **-0,2069 / -0,1943** | Forte rejeição às bordas esquerdas (`06` e `16` aparecem em 77,1% dos sorteios impopulares). |
| `tem_13` | **+0,1164** | Preferência marcante pelo centro exato do volante (`13` aparece em 71,6% dos sorteios populares). |

### Validação Temporal do `LightGBM` (80% passado / 20% futuro — 682 concursos)
* **$R^2$ (escala log):** `0,6475` | **MAE log:** `0,1472` (baseline ingênuo: `0,2844`)
* **Correlação de ranking (Spearman):** `0,8179`
* **Backtest nos 682 sorteios futuros:** os 10% menos populares previstos tiveram mediana real de **`0,604x`** nos 14 acertos e média de **`0,507x`** nos 15 acertos, contra **`1,604x`** (14 acertos) e **`2,014x`** (15 acertos) nos 10% mais populares — quase **4× menos rateio** na faixa principal.

---

## Desdobramento Matemático (15 a 20 Dezenas) e Bloqueio Histórico

Para preservar o rigor estatístico do modelo (treinado exclusivamente em sorteios oficiais de 15 dezenas), apostas múltiplas seguem a formulação combinatória da Caixa:

* **Avaliação por desdobramento:** um bilhete de $k$ dezenas equivale a $\binom{k}{15}$ apostas simples. Sua popularidade prevista é a média sobre todos os subconjuntos de 15 dezenas (cálculo **exato** para 15 a 18 dezenas; **amostragem determinística** de 500 subconjuntos para 19 e 20 dezenas), com explicabilidade `SHAP` agregada e cálculo dinâmico de custo (`custo_estimado`).
* **Política de histórico via bitmasks (`uint32`):**
  * **15 a 17 dezenas (`bloqueio_rigido`):** bloqueio total de qualquer combinação que contenha um dos 3.836 sorteios já realizados.
  * **18 a 20 dezenas (`minimizacao_transparente`):** como um volante de 19–20 dezenas cobre em média 4,5 a 18,2 sorteios históricos, o otimizador penaliza e minimiza a sobreposição e informa explicitamente `qtd_sorteios_historicos_cobertos` no retorno.

---

## Endpoints da API (`FastAPI`)

| Método | Rota | Descrição |
| :---: | :--- | :--- |
| `GET` | `/health` | Status do serviço, último concurso, preço atual da aposta simples e métricas de teste do modelo. |
| `GET` | `/ultimo-concurso` | Número e dezenas do concurso de referência usado no cálculo de repetidas. |
| `POST` | `/avaliar` | Avalia qualquer jogo (15 a 20 dezenas), checa cobertura histórica e retorna Nota Anti-Rateio + fatores `SHAP`. |
| `POST` | `/sugerir` | Gera de 1 a 20 sugestões otimizadas (15 a 20 dezenas), respeitando fixas, excluídas, diversidade mínima e política de histórico. |

---

## Estrutura do Projeto

```text
lotofacil-sugestor/
├── data/
│   ├── raw/                     # SQLite local com payloads brutos da Caixa (ignorado no Git)
│   └── processed/               # Bases tabulares limpas e 56 features extraídas (ignorado no Git)
├── docs/figures/                # Gráficos da análise exploratória (histogramas, LOWESS, boxplots, heatmap 5x5)
├── models/                      # Artefato treinado LightGBM (.joblib, ignorado no Git)
├── notebooks/eda_visual.py      # Geração dos gráficos exploratórios
├── src/
│   ├── data/
│   │   ├── fetch_lotofacil.py   # Coletor assíncrono incremental da API oficial da Caixa
│   │   └── process_lotofacil.py # Limpeza e cálculo calibrado do Índice de Popularidade
│   ├── features/
│   │   └── volante_features.py  # Extrator das 56 features geométricas, aritméticas e flags individuais
│   ├── models/
│   │   ├── train_model.py       # Treino LightGBM, validação temporal, backtest e SHAP global
│   │   └── optimizer.py         # Avaliador SHAP, desdobramento 15–20 dezenas e otimizador com bitmask
│   ├── api/
│   │   └── main.py              # API REST FastAPI + serviço de arquivos estáticos (/ e /docs)
│   └── web/
│       ├── index.html           # Interface Web com abas Sugerir e Avaliar
│       ├── styles.css           # Tema de alto contraste com fundo gelo e mini-volantes 5x5
│       └── app.js               # Lógica do volante interativo, custo em tempo real e barras SHAP
├── tests/test_api.py            # Suíte automatizada de testes (pytest + TestClient)
├── requirements.txt
└── README.md
```

---

## Como Executar Localmente

**Pré-requisitos:** Python 3.12+

```powershell
# 1. Clonar e preparar o ambiente virtual
git clone https://github.com/Braganando/lotofacil-sugestor.git
cd lotofacil-sugestor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Pipeline completo de dados e treino do modelo
python src/data/fetch_lotofacil.py
python src/data/process_lotofacil.py
python src/features/volante_features.py
python -m src.models.train_model

# 3. Subir a aplicação (Interface Web em http://127.0.0.1:8000 | Swagger em /docs)
uvicorn src.api.main:app --reload

# 4. Rodar a suíte de testes automatizados
python -m pytest -v
```

---

## Roadmap

- [x] **Fase 1:** Coletor assíncrono incremental via API oficial da Caixa + SQLite local
- [x] **Fase 2:** Pipeline de tratamento e cálculo calibrado do Índice de Popularidade
- [x] **Fase 3:** Engenharia de 56 atributos do volante $5 \times 5$
- [x] **Fase 4:** Análise exploratória visual estilo *The New S Language* (`v0.1.0`)
- [x] **Fase 5:** Modelo `LightGBM` com validação temporal, explicabilidade `SHAP` e otimizador anti-rateio (`v0.2.0`)
- [x] **Fase 6A:** Suporte matemático a desdobramentos (15–20 dezenas), API REST `FastAPI` e testes automatizados (`v0.3.0`)
- [x] **Fase 6B:** Interface Web interativa com volante $5 \times 5$, seletor de jogos/dezenas (15–20) e barras SHAP (`v0.4.0`)
- [ ] **Fase 6C:** Fechamento combinatório real (*Covering Design* guiado pelo `LightGBM`) e simulador Monte Carlo de carteira (`v0.5.0`)
- [ ] **Fase 6D:** Persistência em nuvem (`Supabase`), conferência automática de apostas e relatório final de execução (`v1.0.0`)