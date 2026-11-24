import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    """Inicializa o app com lifespan para carregar o modelo 1x na suíte."""
    with TestClient(app) as c:
        yield c


def test_health_ok(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["total_combinacoes_bloqueadas"] > 0
    assert data["preco_aposta_simples_atual"] > 0
    assert data["metricas_modelo_teste"]["spearman"] > 0.7


def test_ultimo_concurso(client: TestClient):
    resp = client.get("/ultimo-concurso")
    assert resp.status_code == 200
    data = resp.json()
    assert data["concurso"] > 0
    assert len(data["dezenas"]) == 15
    assert len(set(data["dezenas"])) == 15


def test_avaliar_jogo_popular_15_dezenas(client: TestClient):
    payload = {
        "dezenas": [1, 3, 5, 7, 9, 10, 11, 13, 15, 17, 19, 21, 23, 24, 25],
        "top_fatores": 4,
    }
    resp = client.post("/avaliar", json=payload)
    assert resp.status_code == 200
    aval = resp.json()["avaliacao"]
    assert aval["qtd_dezenas"] == 15
    assert aval["combinacoes_equivalentes"] == 1
    assert aval["modo_avaliacao"] == "exato_15"
    assert aval["indice_popularidade_previsto"] > 1.0
    assert 0.0 <= aval["nota_anti_rateio"] <= 100.0
    assert len(aval["fatores_desfavoraveis"]) > 0


def test_avaliar_detecta_jogo_ja_sorteado(client: TestClient):
    ultimo = client.get("/ultimo-concurso").json()
    resp = client.post("/avaliar", json={"dezenas": ultimo["dezenas"]})
    assert resp.status_code == 200
    aval = resp.json()["avaliacao"]
    assert aval["ja_sorteado"] is True
    assert aval["concurso_ja_sorteado"] == ultimo["concurso"]
    assert aval["qtd_sorteios_historicos_cobertos"] == 1


def test_avaliar_jogo_16_dezenas_desdobramento(client: TestClient):
    payload = {
        "dezenas": [1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 17, 18, 19, 20, 22, 25],
        "top_fatores": 3,
    }
    resp = client.post("/avaliar", json=payload)
    assert resp.status_code == 200
    aval = resp.json()["avaliacao"]
    assert aval["qtd_dezenas"] == 16
    assert aval["combinacoes_equivalentes"] == 16
    assert aval["modo_avaliacao"] == "desdobramento_exato"
    assert aval["custo_estimado"] > 0
    assert 0.0 <= aval["nota_anti_rateio"] <= 100.0


def test_avaliar_dezenas_invalidas_retorna_422(client: TestClient):
    payload = {"dezenas": [1, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}
    resp = client.post("/avaliar", json=payload)
    assert resp.status_code == 422


def test_sugerir_jogos_15_dezenas_filtros_e_bloqueio(client: TestClient):
    payload = {
        "n_jogos": 3,
        "qtd_dezenas": 15,
        "fixas": [6, 16],
        "excluidas": [13],
        "diversidade_minima": 3,
        "excluir_ja_sorteados": True,
        "n_candidatos": 1000,
        "seed": 42,
    }
    resp = client.post("/sugerir", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filtros_aplicados"]["politica_bloqueio_historico"] == "bloqueio_rigido"
    jogos = data["jogos"]
    assert len(jogos) == 3

    conjuntos = []
    for jogo in jogos:
        conj = set(jogo["dezenas"])
        assert len(conj) == 15
        assert {6, 16}.issubset(conj)
        assert 13 not in conj
        assert jogo["ja_sorteado"] is False
        assert jogo["qtd_sorteios_historicos_cobertos"] == 0
        conjuntos.append(conj)

    for i in range(len(conjuntos)):
        for j in range(i + 1, len(conjuntos)):
            assert len(conjuntos[i] - conjuntos[j]) >= 3


def test_sugerir_jogos_17_dezenas_bloqueio_rigido(client: TestClient):
    payload = {
        "n_jogos": 2,
        "qtd_dezenas": 17,
        "fixas": [6, 16],
        "excluidas": [13],
        "excluir_ja_sorteados": True,
        "seed": 42,
    }
    resp = client.post("/sugerir", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filtros_aplicados"]["qtd_dezenas"] == 17
    assert data["filtros_aplicados"]["politica_bloqueio_historico"] == "bloqueio_rigido"
    assert len(data["jogos"]) == 2
    for jogo in data["jogos"]:
        assert jogo["qtd_dezenas"] == 17
        assert jogo["combinacoes_equivalentes"] == 136
        assert jogo["modo_avaliacao"] == "desdobramento_exato"
        assert jogo["qtd_sorteios_historicos_cobertos"] == 0


def test_sugerir_jogos_19_dezenas_minimizacao_transparente(client: TestClient):
    payload = {
        "n_jogos": 2,
        "qtd_dezenas": 19,
        "excluir_ja_sorteados": True,
        "seed": 42,
    }
    resp = client.post("/sugerir", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filtros_aplicados"]["qtd_dezenas"] == 19
    assert data["filtros_aplicados"]["politica_bloqueio_historico"] == "minimizacao_transparente"
    assert data["custo_total_estimado"] > 0
    assert len(data["jogos"]) == 2
    for jogo in data["jogos"]:
        assert jogo["qtd_dezenas"] == 19
        assert jogo["combinacoes_equivalentes"] == 3876
        assert jogo["modo_avaliacao"] == "desdobramento_amostral"
        assert isinstance(jogo["qtd_sorteios_historicos_cobertos"], int)


def test_sugerir_conflito_fixas_excluidas_retorna_422(client: TestClient):
    payload = {"n_jogos": 2, "fixas": [6], "excluidas": [6]}
    resp = client.post("/sugerir", json=payload)
    assert resp.status_code == 422