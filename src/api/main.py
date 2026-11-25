from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.models.optimizer import (
    MAX_DEZENAS,
    MAX_DEZENAS_BLOQUEIO_RIGIDO,
    MIN_DEZENAS,
    LotofacilOptimizer,
)

from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# --- Schemas de Entrada ---


class AvaliarJogoRequest(BaseModel):
    dezenas: list[int] = Field(
        ...,
        min_length=MIN_DEZENAS,
        max_length=MAX_DEZENAS,
        description="Lista com 15 a 20 dezenas distintas entre 1 e 25.",
        examples=[[1, 3, 5, 7, 9, 10, 11, 13, 15, 17, 19, 21, 23, 24, 25]],
    )
    top_fatores: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Quantidade máxima de fatores SHAP favoráveis e desfavoráveis retornados.",
    )


class SugerirJogosRequest(BaseModel):
    n_jogos: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Quantidade de jogos sugeridos.",
    )
    qtd_dezenas: int = Field(
        default=15,
        ge=MIN_DEZENAS,
        le=MAX_DEZENAS,
        description="Quantidade de dezenas por jogo sugerido (15 a 20, padrão oficial da Caixa).",
    )
    fixas: list[int] = Field(
        default_factory=list,
        max_length=19,
        description="Dezenas obrigatórias em todos os jogos sugeridos (entre 1 e 25).",
        examples=[[6, 16]],
    )
    excluidas: list[int] = Field(
        default_factory=list,
        max_length=10,
        description="Dezenas proibidas nos jogos sugeridos (entre 1 e 25).",
        examples=[[13]],
    )
    diversidade_minima: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Mínimo de dezenas diferentes entre quaisquer dois jogos retornados.",
    )
    excluir_ja_sorteados: bool = Field(
        default=True,
        description=(
            "Bloqueio rígido de jogos já sorteados para 15-17 dezenas; "
            "minimização transparente para 18-20 dezenas."
        ),
    )
    n_candidatos: int = Field(
        default=3000,
        ge=500,
        le=10000,
        description="Tamanho da amostra inicial de candidatos avaliados pelo modelo.",
    )
    seed: int | None = Field(
        default=None,
        description="Semente opcional para reprodutibilidade das sugestões.",
    )


# --- Ciclo de vida da aplicação ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.optimizer = LotofacilOptimizer()
    yield


app = FastAPI(
    title="Lotofácil Sugestor API — Otimização Anti-Rateio",
    description=(
        "API de Machine Learning (LightGBM + SHAP) inspirada em *The New S Language* (1988) "
        "para estimar a popularidade de combinações da Lotofácil (15 a 20 dezenas) e sugerir "
        "jogos com menor risco de divisão de prêmio."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(WEB_DIR / "index.html")

def _get_optimizer() -> LotofacilOptimizer:
    opt = getattr(app.state, "optimizer", None)
    if opt is None:
        raise HTTPException(status_code=503, detail="Motor de otimização ainda não inicializado.")
    return opt


# --- Endpoints ---


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, Any]:
    opt = _get_optimizer()
    return {
        "status": "ok",
        "ultimo_concurso_referencia": opt.ultimo_concurso_num,
        "ultimo_concurso_treino": opt.ultimo_concurso_treino,
        "total_combinacoes_bloqueadas": len(opt.historico_sorteios),
        "preco_aposta_simples_atual": opt.preco_aposta_atual,
        "metricas_modelo_teste": opt.metricas_teste,
    }


@app.get("/ultimo-concurso", tags=["Dados"])
def ultimo_concurso() -> dict[str, Any]:
    opt = _get_optimizer()
    return {
        "concurso": opt.ultimo_concurso_num,
        "dezenas": opt.ultimas_dezenas,
    }


@app.post("/avaliar", tags=["Otimizador"])
def avaliar_jogo(payload: AvaliarJogoRequest) -> dict[str, Any]:
    opt = _get_optimizer()
    try:
        resultado = opt.avaliar_jogo(
            dezenas=payload.dezenas,
            top_fatores=payload.top_fatores,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "concurso_referencia": opt.ultimo_concurso_num,
        "avaliacao": resultado,
    }


@app.post("/sugerir", tags=["Otimizador"])
def sugerir_jogos(payload: SugerirJogosRequest) -> dict[str, Any]:
    opt = _get_optimizer()
    try:
        jogos = opt.sugerir_jogos(
            n_jogos=payload.n_jogos,
            qtd_dezenas=payload.qtd_dezenas,
            fixas=payload.fixas,
            excluidas=payload.excluidas,
            n_candidatos=payload.n_candidatos,
            diversidade_minima=payload.diversidade_minima,
            excluir_ja_sorteados=payload.excluir_ja_sorteados,
            seed=payload.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not payload.excluir_ja_sorteados:
        politica_bloqueio = "desativado"
    elif payload.qtd_dezenas <= MAX_DEZENAS_BLOQUEIO_RIGIDO:
        politica_bloqueio = "bloqueio_rigido"
    else:
        politica_bloqueio = "minimizacao_transparente"

    custo_total = round(sum(j["custo_estimado"] for j in jogos), 2)

    return {
        "concurso_referencia": opt.ultimo_concurso_num,
        "total_retornado": len(jogos),
        "custo_total_estimado": custo_total,
        "filtros_aplicados": {
            "qtd_dezenas": payload.qtd_dezenas,
            "fixas": sorted(set(payload.fixas)),
            "excluidas": sorted(set(payload.excluidas)),
            "diversidade_minima": payload.diversidade_minima,
            "excluir_ja_sorteados": payload.excluir_ja_sorteados,
            "politica_bloqueio_historico": politica_bloqueio,
        },
        "jogos": jogos,
    }