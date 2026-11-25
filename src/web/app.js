const COMB_15 = { 15: 1, 16: 16, 17: 136, 18: 816, 19: 3876, 20: 15504 };
const EXEMPLO_POPULAR = [1, 3, 5, 7, 9, 10, 11, 13, 15, 17, 19, 21, 23, 24, 25];

const state = {
  precoAposta: 3.5,
  ultimoConcurso: null,
  ultimasDezenas: [],
  // Mapa de 1..25 -> "neutra" | "fixa" | "excluida"
  filtrosSugerir: Object.fromEntries(Array.from({ length: 25 }, (_, i) => [i + 1, "neutra"])),
  selecionadasAvaliar: new Set(),
};

const fmtBRL = (val) =>
  val.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const fmtDez = (n) => String(n).padStart(2, "0");

// --- Inicialização ---

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  renderGridSugerir();
  renderGridAvaliar();
  bindEvents();
  carregarStatusInicial();
});

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

async function carregarStatusInicial() {
  const pills = document.getElementById("status-pills");
  try {
    const [healthResp, ultimoResp] = await Promise.all([
      fetch("/health"),
      fetch("/ultimo-concurso"),
    ]);
    const health = await healthResp.json();
    const ultimo = await ultimoResp.json();

    state.precoAposta = health.preco_aposta_simples_atual || 3.5;
    state.ultimoConcurso = ultimo.concurso;
    state.ultimasDezenas = ultimo.dezenas || [];

    const spearman = health.metricas_modelo_teste?.spearman;
    pills.innerHTML = `
      <span class="pill">Concurso ref.: <strong>#${health.ultimo_concurso_referencia}</strong></span>
      <span class="pill">Histórico: <strong>${health.total_combinacoes_bloqueadas}</strong> jogos</span>
      <span class="pill">Aposta 15d: <strong>${fmtBRL(state.precoAposta)}</strong></span>
      ${spearman ? `<span class="pill">Spearman: <strong>${spearman.toFixed(3)}</strong></span>` : ""}
    `;
    atualizarResumoCustoSugerir();
  } catch (err) {
    pills.innerHTML = `<span class="pill">Erro ao conectar na API</span>`;
  }
}

// --- Volante 5x5: Aba Sugerir ---

function renderGridSugerir() {
  const grid = document.getElementById("grid-sugerir");
  grid.innerHTML = "";
  for (let n = 1; n <= 25; n++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dez-btn";
    btn.textContent = fmtDez(n);
    btn.dataset.num = n;
    btn.addEventListener("click", () => {
      const atual = state.filtrosSugerir[n];
      const prox = atual === "neutra" ? "fixa" : atual === "fixa" ? "excluida" : "neutra";
      state.filtrosSugerir[n] = prox;
      atualizarVisualGridSugerir();
    });
    grid.appendChild(btn);
  }
}

function atualizarVisualGridSugerir() {
  document.querySelectorAll("#grid-sugerir .dez-btn").forEach((btn) => {
    const n = Number(btn.dataset.num);
    const st = state.filtrosSugerir[n];
    btn.classList.remove("state-fixa", "state-excluida");
    if (st === "fixa") btn.classList.add("state-fixa");
    if (st === "excluida") btn.classList.add("state-excluida");
  });
}

function obterFixasExcluidas() {
  const fixas = [];
  const excluidas = [];
  for (let n = 1; n <= 25; n++) {
    if (state.filtrosSugerir[n] === "fixa") fixas.push(n);
    if (state.filtrosSugerir[n] === "excluida") excluidas.push(n);
  }
  return { fixas, excluidas };
}

function atualizarResumoCustoSugerir() {
  const nJogos = Number(document.getElementById("sel-n-jogos").value);
  const k = Number(document.getElementById("sel-qtd-dezenas").value);
  const excluir = document.getElementById("chk-excluir-sorteados").checked;

  const total = nJogos * COMB_15[k] * state.precoAposta;
  document.getElementById("sugerir-custo-valor").textContent = fmtBRL(total);

  const elPol = document.getElementById("sugerir-politica-hist");
  if (!excluir) {
    elPol.textContent = "Checagem histórica desativada";
  } else if (k <= 17) {
    elPol.textContent = "Bloqueio rígido (0 sorteios antigos)";
  } else {
    elPol.textContent = "Minimização transparente de sobreposição";
  }
}

// --- Volante 5x5: Aba Avaliar ---

function renderGridAvaliar() {
  const grid = document.getElementById("grid-avaliar");
  grid.innerHTML = "";
  for (let n = 1; n <= 25; n++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dez-btn";
    btn.textContent = fmtDez(n);
    btn.dataset.num = n;
    btn.addEventListener("click", () => {
      if (state.selecionadasAvaliar.has(n)) {
        state.selecionadasAvaliar.delete(n);
      } else if (state.selecionadasAvaliar.size < 20) {
        state.selecionadasAvaliar.add(n);
      }
      atualizarVisualGridAvaliar();
    });
    grid.appendChild(btn);
  }
}

function atualizarVisualGridAvaliar() {
  document.querySelectorAll("#grid-avaliar .dez-btn").forEach((btn) => {
    const n = Number(btn.dataset.num);
    btn.classList.toggle("state-selected", state.selecionadasAvaliar.has(n));
  });

  const qtd = state.selecionadasAvaliar.size;
  document.getElementById("eval-count").textContent = qtd;

  const custo = qtd >= 15 && qtd <= 20 ? COMB_15[qtd] * state.precoAposta : 0;
  document.getElementById("eval-cost").textContent = fmtBRL(custo);
  document.getElementById("btn-avaliar").disabled = !(qtd >= 15 && qtd <= 20);
}

// --- Eventos ---

function bindEvents() {
  ["sel-n-jogos", "sel-qtd-dezenas", "chk-excluir-sorteados"].forEach((id) => {
    document.getElementById(id).addEventListener("change", atualizarResumoCustoSugerir);
  });

  document.getElementById("btn-preset-eda").addEventListener("click", () => {
    for (let n = 1; n <= 25; n++) state.filtrosSugerir[n] = "neutra";
    state.filtrosSugerir[6] = "fixa";
    state.filtrosSugerir[16] = "fixa";
    state.filtrosSugerir[13] = "excluida";
    atualizarVisualGridSugerir();
  });

  document.getElementById("btn-limpar-sugerir").addEventListener("click", () => {
    for (let n = 1; n <= 25; n++) state.filtrosSugerir[n] = "neutra";
    atualizarVisualGridSugerir();
    document.getElementById("msg-sugerir").textContent = "";
  });

  document.getElementById("btn-gerar").addEventListener("click", executarSugestao);

  document.getElementById("btn-carregar-ultimo").addEventListener("click", () => {
    state.selecionadasAvaliar = new Set(state.ultimasDezenas);
    atualizarVisualGridAvaliar();
  });

  document.getElementById("btn-carregar-popular").addEventListener("click", () => {
    state.selecionadasAvaliar = new Set(EXEMPLO_POPULAR);
    atualizarVisualGridAvaliar();
  });

  document.getElementById("btn-limpar-avaliar").addEventListener("click", () => {
    state.selecionadasAvaliar.clear();
    atualizarVisualGridAvaliar();
    document.getElementById("msg-avaliar").textContent = "";
  });

  document.getElementById("btn-avaliar").addEventListener("click", executarAvaliacao);
}

// --- Chamadas à API ---

async function executarSugestao() {
  const msg = document.getElementById("msg-sugerir");
  const btn = document.getElementById("btn-gerar");
  const container = document.getElementById("resultados-sugerir");
  msg.textContent = "";

  const nJogos = Number(document.getElementById("sel-n-jogos").value);
  const qtdDezenas = Number(document.getElementById("sel-qtd-dezenas").value);
  const diversidade = Number(document.getElementById("sel-diversidade").value);
  const excluirSorteados = document.getElementById("chk-excluir-sorteados").checked;
  const { fixas, excluidas } = obterFixasExcluidas();

  if (fixas.length >= qtdDezenas) {
    msg.textContent = `Selecione no máximo ${qtdDezenas - 1} dezenas fixas para jogos de ${qtdDezenas} dezenas.`;
    return;
  }
  if (25 - excluidas.length < qtdDezenas) {
    msg.textContent = `Você excluiu dezenas demais para formar jogos de ${qtdDezenas} dezenas.`;
    return;
  }

  btn.disabled = true;
  btn.textContent = "Otimizando combinações...";

  try {
    const resp = await fetch("/sugerir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        n_jogos: nJogos,
        qtd_dezenas: qtdDezenas,
        fixas,
        excluidas,
        diversidade_minima: diversidade,
        excluir_ja_sorteados: excluirSorteados,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Erro ao gerar sugestões.");

    const polTexto = {
      bloqueio_rigido: "Bloqueio rígido ativo",
      minimizacao_transparente: "Minimização transparente ativa",
      desativado: "Filtro histórico desativado",
    }[data.filtros_aplicados.politica_bloqueio_historico];

    const banner = `
      <div class="summary-banner">
        <div>
          <strong>${data.total_retornado} jogo(s)</strong> de <strong>${qtdDezenas} dezenas</strong>
          • Ref. concurso #${data.concurso_referencia} • ${polTexto}
        </div>
        <div>Total estimado: <strong>${fmtBRL(data.custo_total_estimado)}</strong></div>
      </div>
    `;

    container.innerHTML =
      banner + data.jogos.map((jogo, i) => renderGameCard(jogo, `Sugestão #${i + 1}`)).join("");
    bindCopyButtons(container);
  } catch (err) {
    msg.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Gerar Jogos Anti-Rateio";
  }
}

async function executarAvaliacao() {
  const msg = document.getElementById("msg-avaliar");
  const btn = document.getElementById("btn-avaliar");
  const container = document.getElementById("resultados-avaliar");
  msg.textContent = "";

  const dezenas = Array.from(state.selecionadasAvaliar).sort((a, b) => a - b);
  btn.disabled = true;
  btn.textContent = "Calculando SHAP...";

  try {
    const resp = await fetch("/avaliar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dezenas, top_fatores: 4 }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Erro ao avaliar jogo.");

    container.innerHTML = renderGameCard(
      data.avaliacao,
      `Avaliação (${dezenas.length} dezenas • Ref. #${data.concurso_referencia})`
    );
    bindCopyButtons(container);
  } catch (err) {
    msg.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Avaliar Jogo";
  }
}

// --- Renderização dos Cartões ---

function renderGameCard(jogo, titulo) {
  const conj = new Set(jogo.dezenas);
  const nota = jogo.nota_anti_rateio;
  const badgeClass = nota >= 70 ? "score-high" : nota >= 40 ? "score-mid" : "score-low";

  const miniCells = Array.from({ length: 25 }, (_, i) => {
    const n = i + 1;
    return `<div class="mini-cell ${conj.has(n) ? "on" : ""}">${fmtDez(n)}</div>`;
  }).join("");

  let histHtml = "";
  if (jogo.qtd_sorteios_historicos_cobertos === 0) {
    histHtml = `<div class="history-alert history-ok">✓ Combinação inédita — nenhum sorteio oficial anterior contido neste jogo.</div>`;
  } else if (jogo.qtd_dezenas === 15) {
    histHtml = `<div class="history-alert history-warn">⚠ Atenção: esta combinação exata já foi sorteada no concurso #${jogo.concurso_ja_sorteado}.</div>`;
  } else {
    const lista = jogo.concursos_historicos_cobertos.slice(0, 5).map((c) => `#${c}`).join(", ");
    histHtml = `<div class="history-alert history-warn">⚠ Este desdobramento cobre ${jogo.qtd_sorteios_historicos_cobertos} sorteio(s) anterior(es) (ex.: ${lista}).</div>`;
  }

  const renderShapList = (items, cls) => {
    if (!items || items.length === 0) return `<p class="muted">Sem fatores relevantes.</p>`;
    const maxAbs = Math.max(...items.map((x) => Math.abs(x.impacto_shap)), 0.05);
    return items
      .map((f) => {
        const pct = Math.min(100, (Math.abs(f.impacto_shap) / maxAbs) * 100);
        return `
          <div class="shap-item">
            <div>${f.texto}</div>
            <div class="shap-bar-track">
              <div class="shap-bar-fill ${cls}" style="width:${pct.toFixed(0)}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
  };

  const dezStr = jogo.dezenas.map(fmtDez).join(" - ");

  return `
    <article class="card game-card">
      <div class="game-header">
        <div class="game-title">
          <h3>${titulo}</h3>
          <span class="score-badge ${badgeClass}">Nota ${nota.toFixed(1)}/100 • ${jogo.classificacao}</span>
        </div>
        <span class="muted">${jogo.combinacoes_equivalentes.toLocaleString("pt-BR")} aposta(s) • ${fmtBRL(jogo.custo_estimado)}</span>
      </div>

      <div class="game-body">
        <div class="mini-volante">${miniCells}</div>

        <div>
          <div class="metrics-row">
            <div class="metric-chip"><span>Popularidade</span><strong>${jogo.indice_popularidade_previsto.toFixed(3)}x</strong></div>
            <div class="metric-chip"><span>Soma</span><strong>${jogo.resumo_features.soma}</strong></div>
            <div class="metric-chip"><span>Pares</span><strong>${jogo.resumo_features.qtd_pares}</strong></div>
            <div class="metric-chip"><span>Desvio linhas</span><strong>${jogo.resumo_features.std_linhas}</strong></div>
            <div class="metric-chip"><span>Maior seq.</span><strong>${jogo.resumo_features.maior_sequencia}</strong></div>
            <div class="metric-chip"><span>Repetidas</span><strong>${jogo.resumo_features.repetidas_anterior}</strong></div>
          </div>

          ${histHtml}

          <div class="shap-section">
            <div class="shap-group">
              <h4>Reduzem o rateio (SHAP)</h4>
              ${renderShapList(jogo.fatores_favoraveis, "good")}
            </div>
            <div class="shap-group">
              <h4>Aumentam o rateio (SHAP)</h4>
              ${renderShapList(jogo.fatores_desfavoraveis, "bad")}
            </div>
          </div>
        </div>
      </div>

      <div class="dezenas-line">
        <span>${dezStr}</span>
        <button type="button" class="btn btn-ghost btn-copy" data-copy="${dezStr}">Copiar dezenas</button>
      </div>
    </article>
  `;
}

function bindCopyButtons(root) {
  root.querySelectorAll(".btn-copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await navigator.clipboard.writeText(btn.dataset.copy);
      const orig = btn.textContent;
      btn.textContent = "Copiado!";
      setTimeout(() => (btn.textContent = orig), 1400);
    });
  });
}