import argparse
import asyncio
import json
import sqlite3
from pathlib import Path
import httpx

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
DB_PATH = Path("data/raw/lotofacil.db")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def inicializar_banco(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS concursos_raw (
            numero INTEGER PRIMARY KEY,
            data_apuracao TEXT,
            valor_arrecadado REAL,
            indicador_especial INTEGER,
            payload_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def listar_salvos(conn: sqlite3.Connection) -> set[int]:
    cursor = conn.execute("SELECT numero FROM concursos_raw")
    return {row[0] for row in cursor.fetchall()}


def salvar_lote(conn: sqlite3.Connection, registros: list[dict]) -> None:
    linhas = [
        (
            r["numero"],
            r.get("dataApuracao"),
            r.get("valorArrecadado"),
            r.get("indicadorConcursoEspecial"),
            json.dumps(r, ensure_ascii=False),
        )
        for r in registros
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO concursos_raw
        (numero, data_apuracao, valor_arrecadado, indicador_especial, payload_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        linhas,
    )
    conn.commit()


async def buscar_concurso(
    client: httpx.AsyncClient,
    semaforo: asyncio.Semaphore,
    numero: int | None = None,
    tentativas: int = 3,
) -> dict | None:
    url = BASE_URL if numero is None else f"{BASE_URL}/{numero}"
    async with semaforo:
        for tentativa in range(1, tentativas + 1):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    return None
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.5 * tentativa)
    return None


async def coletar(modo_teste: bool = False, concorrencia: int = 8) -> None:
    conn = inicializar_banco()
    semaforo = asyncio.Semaphore(concorrencia)

    async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
        ultimo = await buscar_concurso(client, semaforo, numero=None)
        if not ultimo:
            raise RuntimeError("Não foi possível consultar o último concurso na API da Caixa.")

        ultimo_num = int(ultimo["numero"])
        print(f"Último concurso disponível na Caixa: {ultimo_num} ({ultimo.get('dataApuracao')})")

        if modo_teste:
            alvos = [1, 2000, ultimo_num]
            print(f"Modo teste ativo. Baixando concursos: {alvos}")
        else:
            salvos = listar_salvos(conn)
            alvos = [n for n in range(1, ultimo_num + 1) if n not in salvos]
            print(f"Já salvos: {len(salvos)} | Faltam baixar: {len(alvos)}")

        if not alvos:
            print("Base já está atualizada!")
            conn.close()
            return

        baixados = 0
        falhas = []
        tamanho_lote = 50

        for i in range(0, len(alvos), tamanho_lote):
            lote_ids = alvos[i : i + tamanho_lote]
            tarefas = [buscar_concurso(client, semaforo, n) for n in lote_ids]
            resultados = await asyncio.gather(*tarefas)

            validos = []
            for num, res in zip(lote_ids, resultados):
                if res and "numero" in res:
                    validos.append(res)
                else:
                    falhas.append(num)

            if validos:
                salvar_lote(conn, validos)
                baixados += len(validos)

            print(f"Progresso: {min(i + tamanho_lote, len(alvos))}/{len(alvos)} verificados | Salvos: {baixados}")

        if modo_teste:
            print("\n--- Resumo dos concursos de teste ---")
            for row in conn.execute(
                "SELECT payload_json FROM concursos_raw WHERE numero IN (1, 2000, ?) ORDER BY numero",
                (ultimo_num,),
            ):
                d = json.loads(row[0])
                print(f"\nConcurso {d['numero']} ({d.get('dataApuracao')}) | Arrecadado: R$ {d.get('valorArrecadado')}")
                print(f"  Dezenas: {d.get('listaDezenas')}")
                for faixa in d.get("listaRateioPremio", []):
                    print(
                        f"  Faixa {faixa.get('faixa')} ({faixa.get('descricaoFaixa')}): "
                        f"{faixa.get('numeroDeGanhadores')} ganhadores | R$ {faixa.get('valorPremio')}"
                    )

        if falhas:
            print(f"\nConcursos com falha ({len(falhas)}): {falhas[:20]}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coletor incremental da Lotofácil (API Caixa).")
    parser.add_argument("--teste", action="store_true", help="Baixa apenas 3 concursos para inspeção.")
    args = parser.parse_args()
    asyncio.run(coletar(modo_teste=args.teste))