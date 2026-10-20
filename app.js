import {
  extrairDois, montarIndice, avaliarDoi, calcularNotaManual,
  emParalelo, formatarIssn,
} from "./logica.js";

// ---------------------------------------------------------------------------
// Configurações
// ---------------------------------------------------------------------------
const EMAIL_CONTATO = "";
const CONCORRENCIA = 4;
const LIMITE_DOIS = 1500;

const $ = (id) => document.getElementById(id);
const el = {
  entrada: $("entrada"),
  btn: $("btnAvaliar"),
  btnParar: $("btnParar"),
  btnImportarLattes: $("btnImportarLattes"),
  arquivoLattes: $("arquivoLattes"),
  btnLimpar: $("btnLimpar"),
  btnToggleTodos: $("btnToggleTodos"),
  filtroTabela: $("filtroTabela"),
  csv: $("btnCsv"),
  status: $("status"),
  container: $("containerTabela"),
  corpo: document.querySelector("#tabela tbody"),
  placar: $("placar"),
  placarTotal: $("placarTotal"),
  placarScopus: $("placarScopus"),
  placarPontuaveis: $("placarPontuaveis"),
  placarNota: $("placarNota"),
};

let indice = null;
let regras = null;
let resultados = [];
let cancelando = false;

// ---------------------------------------------------------------------------
// Inicialização das Bases Estáticas
// ---------------------------------------------------------------------------
async function carregarBases() {
  try {
    const respRegras = await fetch("data/regras.json");
    if (respRegras.ok) regras = await respRegras.json();

    // Tenta primeiro o citescore com percentis embutidos; se não existir, usa a lista oficial de fontes
    let respFontes = await fetch("data/citescore.json");
    if (!respFontes.ok) {
      respFontes = await fetch("data/fontes_scopus.json");
    }
    if (respFontes.ok) {
      const dados = await respFontes.json();
      indice = montarIndice(dados);
    }
  } catch (err) {
    console.error("Erro ao carregar bases estáticas:", err);
  }
}

// ---------------------------------------------------------------------------
// Renderização
// ---------------------------------------------------------------------------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const fmt = (n, d = 2) => (n == null || n === "" || isNaN(n) ? "—" : Number(n).toLocaleString("pt-BR", {
  minimumFractionDigits: d, maximumFractionDigits: d,
}));

function badgeEstrato(estrato) {
  if (!estrato || estrato === "—") return '<span class="badge cinza">—</span>';
  return `<span class="badge ${estrato}">${esc(estrato)}</span>`;
}

function linhaPrincipal(r, i, aberta = false) {
  const autoresStr = r.n_autores
    ? `${r.n_autores} autor(es)${r.n_autores > 4 ? ` <small style="color:var(--suave);">(fator ${fmt(r.fator_divisao, 3)})</small>` : ""}`
    : "—";

  const btnScopus = r.link_revista
    ? `<a href="${esc(r.link_revista)}" target="_blank" rel="noopener" class="btn-scopus" title="Abrir perfil na Scopus">🔗 Scopus ↗</a>`
    : '<span style="color:var(--suave); font-size:12px;">Não indexada</span>';

  let areaEditalStr = "—";
  if (r.status === "fora_areas") {
    areaEditalStr = '<span class="alerta-fora">⚠️ Fora da Tabela 2</span>';
  } else if (r.area_principal) {
    areaEditalStr = `<span class="area-tag">${esc(r.area_principal)}</span>`;
  } else if (r.areas_edital) {
    areaEditalStr = r.areas_edital.split(" / ").map((a) => `<span class="area-tag">${esc(a)}</span>`).join(" ");
  }

  const valPerc = r.percentil != null ? r.percentil : "";
  const readonly = r.status === "ok" && r.ano_citescore ? "readonly" : "";

  return `
    <td class="col-indice">
      <button type="button" class="btn-exp-icone" title="${aberta ? "Ocultar detalhes" : "Expandir detalhes"}" aria-expanded="${aberta}">
        <span class="seta-exp">${aberta ? "▼" : "▶"}</span>
      </button>
      <span style="color:var(--suave); font-weight:600;">${i + 1}</span>
    </td>
    <td style="max-width: 380px;">
      <div class="tit">${esc(r.titulo || r.motivo || "Carregando...")}${r.retratado ? ' <span class="badge cinza" style="background:#cf222e;color:#fff;">RETRATADO</span>' : ""}</div>
      <div class="doi">
        <a href="${esc(r.link_doi)}" target="_blank">${esc(r.doi)}</a>
        <button type="button" class="btn-mais-info" title="${aberta ? "Ocultar ficha completa" : "Ver autores, ISSN, citações e áreas Scopus"}">
          <span class="seta-info">${aberta ? "➖" : "➕"}</span> ${aberta ? "Menos informações" : "Mais informações"}
        </button>
      </div>
    </td>
    <td class="num">${r.ano ?? "—"}</td>
    <td style="max-width: 240px;">
      <strong>${esc(r.revista || "—")}</strong>
      ${r.scopus_ativa === false ? ' <small style="color:#cf222e;">(Descontinuada)</small>' : ""}
    </td>
    <td>${autoresStr}</td>
    <td>${areaEditalStr}</td>
    <td style="text-align: center;">${btnScopus}</td>
    <td style="text-align: center;">
      <input type="number" min="0" max="100" step="0.1"
             class="inp-perc" placeholder="%"
             value="${valPerc}" data-i="${i}" ${readonly}
             title="Digite o percentil CiteScore visto na página da Scopus">
    </td>
    <td style="text-align: center;" id="colEstrato_${i}">${badgeEstrato(r.estrato)}</td>
    <td class="num" id="colNota_${i}"><strong>${r.nota_final_calculada != null ? fmt(r.nota_final_calculada) + " pts" : "—"}</strong></td>
  `;
}

function detalhe(r) {
  if (r.status === "carregando") return '<td colspan="10">Carregando dados...</td>';

  const linhas = [
    ["DOI", `<a href="${esc(r.link_doi)}" target="_blank">${esc(r.doi)}</a>`],
    ["Título completo", esc(r.titulo || "—")],
    ["Lista de autores", esc((r.autores || []).join("; ") || "—")],
    ["Revista oficial", `${esc(r.revista || "—")} ${r.scopus_source_id ? `(Scopus Source ID: ${esc(r.scopus_source_id)})` : ""}`],
    ["ISSN(s)", (r.issns || []).map(formatarIssn).join(", ") || "—"],
    ["Publicação", [r.data_publicacao || r.ano, r.volume && `Vol. ${r.volume}`, r.numero && `Nº ${r.numero}`, r.paginas && `Págs. ${r.paginas}`].filter(Boolean).map(esc).join(" · ") || "—"],
    ["Citações do artigo", `Crossref: ${fmt(r.citacoes_crossref, 0)} · OpenAlex: ${fmt(r.citacoes_openalex, 0)}${r.fwci != null ? ` · FWCI: ${fmt(r.fwci)}` : ""}`],
    ["Acesso Aberto", r.acesso_aberto ? `${esc(r.acesso_aberto)}${r.link_acesso_aberto ? ` (<a href="${esc(r.link_acesso_aberto)}" target="_blank">PDF disponível</a>)` : ""}` : "Não informado"],
    ["Link direto Scopus", r.link_revista ? `<a href="${esc(r.link_revista)}" target="_blank">${esc(r.link_revista)}</a>` : "Não indexada"],
  ];

  let areasTabela = "";
  if (r.todas_areas?.length) {
    areasTabela = `
      <div style="margin-top: 10px;">
        <strong style="font-size: 12px; color: var(--suave);">Classificação ASJC da Scopus para esta revista:</strong>
        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">
          ${r.todas_areas.map((a) => `
            <span class="area-tag" style="${a.area_edital ? 'background:#e7f3fe; border-color:#93c5fd; font-weight:600;' : 'background:#f3f4f6; color:#6b7280; border-color:#e5e7eb;'}">
              ${esc(a.nome)} (${a.asjc})${a.area_edital ? ` ➔ ${esc(a.area_edital)}` : " (não pontua)"}
            </span>
          `).join("")}
        </div>
      </div>
    `;
  }

  return `
    <td colspan="10">
      <dl class="grade">${linhas.map(([k, v]) => `<dt>${esc(k)}:</dt><dd>${v}</dd>`).join("")}</dl>
      ${areasTabela}
    </td>
  `;
}

function desenharLinha(i) {
  const r = resultados[i];
  const tr = el.corpo.querySelector(`tr.linha[data-i="${i}"]`);
  if (!tr) return;
  const aberta = tr.classList.contains("aberta");
  tr.innerHTML = linhaPrincipal(r, i, aberta);
  const det = tr.nextElementSibling;
  if (det && det.classList.contains("detalhe")) {
    det.innerHTML = detalhe(r);
  }
}

function atualizarPlacar() {
  const total = resultados.length;
  const scopus = resultados.filter((r) => Boolean(r.scopus_source_id)).length;
  const pontuaveis = resultados.filter((r) => r.status !== "fora_areas" && r.scopus_source_id).length;
  const soma = resultados.reduce((acc, r) => acc + (Number(r.nota_final_calculada) || 0), 0);

  el.placarTotal.textContent = total;
  el.placarScopus.textContent = scopus;
  el.placarPontuaveis.textContent = pontuaveis;
  el.placarNota.textContent = `${fmt(soma)} pts`;
  el.placar.style.display = total > 0 ? "flex" : "none";
}

// ---------------------------------------------------------------------------
// Execução Principal
// ---------------------------------------------------------------------------
async function avaliar() {
  let dois = extrairDois(el.entrada.value);
  if (!dois.length) {
    el.status.textContent = "Nenhum DOI identificado no texto inserido.";
    return;
  }
  if (dois.length > LIMITE_DOIS) {
    el.status.textContent = `Limite máximo de ${LIMITE_DOIS} DOIs por lote. Processando os primeiros ${LIMITE_DOIS}...`;
    dois = dois.slice(0, LIMITE_DOIS);
  }

  cancelando = false;
  el.btn.disabled = true;
  if (el.btnParar) el.btnParar.hidden = false;
  el.csv.disabled = true;
  todosAbertos = false;
  if (el.btnToggleTodos) el.btnToggleTodos.textContent = "➕ Expandir Todos";
  if (el.filtroTabela) el.filtroTabela.value = "";
  resultados = dois.map((doi) => ({ doi, status: "carregando" }));

  el.corpo.innerHTML = resultados.map((_, i) => `
    <tr class="linha" data-i="${i}"></tr>
    <tr class="detalhe" hidden></tr>
  `).join("");

  el.container.hidden = false;
  resultados.forEach((_, i) => desenharLinha(i));

  let feitos = 0;
  const t0 = performance.now();
  const atualizarProgresso = () => {
    const decorrido = (performance.now() - t0) / 1000;
    const taxa = feitos > 0 ? (decorrido / feitos) : 0.25;
    const restantes = dois.length - feitos;
    const etaSeg = Math.round((restantes * taxa) / CONCORRENCIA);
    const etaStr = etaSeg > 5 ? ` (tempo restante est.: ~${etaSeg}s)` : "";
    el.status.textContent = `Processando ${feitos} de ${dois.length} DOIs via Crossref e Scopus...${etaStr}`;
  };
  atualizarProgresso();

  try {
    await emParalelo(
      dois,
      CONCORRENCIA,
      (doi) => avaliarDoi(doi, { indice, regras, email: EMAIL_CONTATO }),
      (r, i) => {
        resultados[i] = r;
        feitos++;
        desenharLinha(i);
        atualizarProgresso();
        atualizarPlacar();
      },
      () => cancelando
    );
  } finally {
    el.btn.disabled = false;
    if (el.btnParar) el.btnParar.hidden = true;
    el.csv.disabled = false;
  }

  if (cancelando) {
    el.status.textContent = `⏹️ Consulta interrompida pelo usuário em ${feitos} de ${dois.length} artigos.`;
  } else {
    el.status.textContent = `Concluído: ${feitos} artigos consultados. Clique na linha ou em [▶] para ver detalhes.`;
  }
  atualizarPlacar();
}

// ---------------------------------------------------------------------------
// Interatividade da Tabela (Input Manual e Expansão)
// ---------------------------------------------------------------------------
el.corpo.addEventListener("input", (ev) => {
  if (ev.target.classList.contains("inp-perc")) {
    const idx = Number(ev.target.dataset.i);
    const val = ev.target.value.trim();
    const r = resultados[idx];
    if (!r) return;

    if (val === "" || isNaN(val)) {
      r.percentil = null;
      r.estrato = null;
      r.pontos_base = null;
      r.nota_final_calculada = null;
    } else {
      const calc = calcularNotaManual(val, r.n_autores, regras);
      if (calc) {
        Object.assign(r, calc);
      }
    }

    const colEst = $(`colEstrato_${idx}`);
    const colNot = $(`colNota_${idx}`);
    if (colEst) colEst.innerHTML = badgeEstrato(r.estrato);
    if (colNot) colNot.innerHTML = `<strong>${r.nota_final_calculada != null ? fmt(r.nota_final_calculada) + " pts" : "—"}</strong>`;
    atualizarPlacar();
  }
});

function alternarLinha(tr) {
  if (!tr) return;
  const det = tr.nextElementSibling;
  if (!det || !det.classList.contains("detalhe")) return;
  const abrir = det.hidden;
  det.hidden = !abrir;
  tr.classList.toggle("aberta", abrir);

  const setaExp = tr.querySelector(".seta-exp");
  if (setaExp) setaExp.textContent = abrir ? "▼" : "▶";

  const btnExp = tr.querySelector(".btn-exp-icone");
  if (btnExp) {
    btnExp.setAttribute("aria-expanded", String(abrir));
    btnExp.title = abrir ? "Ocultar detalhes" : "Expandir detalhes";
  }

  const btnMais = tr.querySelector(".btn-mais-info");
  if (btnMais) {
    btnMais.innerHTML = `<span class="seta-info">${abrir ? "➖" : "➕"}</span> ${abrir ? "Menos informações" : "Mais informações"}`;
    btnMais.title = abrir ? "Ocultar ficha completa" : "Ver autores, ISSN, citações e áreas Scopus";
  }
}

el.corpo.addEventListener("click", (ev) => {
  if (ev.target.closest("a") || ev.target.closest("input")) return;
  const tr = ev.target.closest("tr.linha");
  if (tr) alternarLinha(tr);
});

let todosAbertos = false;
el.btnToggleTodos?.addEventListener("click", () => {
  todosAbertos = !todosAbertos;
  const linhas = el.corpo.querySelectorAll("tr.linha");
  linhas.forEach((tr) => {
    const det = tr.nextElementSibling;
    if (det && det.classList.contains("detalhe") && det.hidden === todosAbertos) {
      alternarLinha(tr);
    }
  });
  el.btnToggleTodos.textContent = todosAbertos ? "➖ Recolher Todos" : "➕ Expandir Todos";
});

// Botão de Interromper Consulta em Lote
el.btnParar?.addEventListener("click", () => {
  cancelando = true;
  el.status.textContent = "Interrompendo consulta em lote...";
});

// Filtro rápido de pesquisa em tempo real na tabela (ano, título, revista, estrato)
el.filtroTabela?.addEventListener("input", (ev) => {
  const termo = ev.target.value.toLowerCase().trim();
  const linhas = el.corpo.querySelectorAll("tr.linha");
  let visiveis = 0;
  linhas.forEach((tr) => {
    const idx = Number(tr.dataset.i);
    const r = resultados[idx];
    const det = tr.nextElementSibling;
    if (!r) return;
    const textoCompleto = `${r.doi || ""} ${r.titulo || ""} ${r.revista || ""} ${r.ano || ""} ${(r.autores || []).join(" ")} ${r.estrato || ""} ${r.area_principal || r.areas_edital || ""}`.toLowerCase();
    const bate = !termo || textoCompleto.includes(termo);
    tr.style.display = bate ? "" : "none";
    if (det && det.classList.contains("detalhe")) {
      if (!bate) det.hidden = true;
      else if (tr.classList.contains("aberta")) det.hidden = false;
    }
    if (bate) visiveis++;
  });
});

// ---------------------------------------------------------------------------
// Exportação CSV
// ---------------------------------------------------------------------------
const COLUNAS_CSV = [
  ["DOI", (r) => r.doi],
  ["Título", (r) => r.titulo],
  ["Revista", (r) => r.revista],
  ["Ano", (r) => r.ano],
  ["Autores", (r) => (r.autores || []).join("; ")],
  ["Nº Autores", (r) => r.n_autores],
  ["Fator Divisão", (r) => r.fator_divisao],
  ["Indexada Scopus", (r) => (r.scopus_source_id ? "SIM" : "NÃO")],
  ["Status Scopus", (r) => (r.scopus_ativa === false ? "Descontinuada" : (r.scopus_source_id ? "Ativa" : ""))],
  ["Área Edital", (r) => r.area_principal || r.areas_edital || ""],
  ["Percentil Informado", (r) => r.percentil ?? ""],
  ["Estrato", (r) => r.estrato ?? ""],
  ["Pontos Base", (r) => r.pontos_base ?? ""],
  ["Nota Final Calculada", (r) => r.nota_final_calculada ?? ""],
  ["Link Scopus", (r) => r.link_revista ?? ""],
  ["Link DOI", (r) => r.link_doi ?? ""],
];

function baixarCsv() {
  const cel = (v) => {
    if (v == null) return "";
    const s = typeof v === "number" ? String(v).replace(".", ",") : String(v);
    return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const cabecalho = COLUNAS_CSV.map(([n]) => n).join(";");
  const linhas = resultados.map((r) => COLUNAS_CSV.map(([, f]) => cel(f(r))).join(";"));
  const conteudo = "\ufeff" + [cabecalho, ...linhas].join("\r\n");

  const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `avaliacao_artigos_peq_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

el.btn.addEventListener("click", avaliar);
el.csv.addEventListener("click", baixarCsv);
el.entrada.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) avaliar();
});

// ---------------------------------------------------------------------------
// Extração e Importação do Lattes (Paste Inteligente, Upload e Drag & Drop)
// ---------------------------------------------------------------------------
function mesclarDoisNaEntrada(novosDois, substituir = false) {
  if (!novosDois || !novosDois.length) return 0;
  let final = novosDois;
  if (!substituir && el.entrada.value.trim()) {
    const existentes = extrairDois(el.entrada.value);
    const unicosNovos = novosDois.filter(
      (d) => !existentes.some((x) => x.toLowerCase() === d.toLowerCase())
    );
    final = [...existentes, ...unicosNovos];
  }
  el.entrada.value = final.join("\n");
  return novosDois.length;
}

// 1. Interceptador de Paste: Lê HTML copiado do Lattes (com DOIs nas tags <a>/<img>)
el.entrada.addEventListener("paste", (ev) => {
  const html = ev.clipboardData?.getData("text/html");
  const texto = ev.clipboardData?.getData("text/plain");

  if (html) {
    const doisHtml = extrairDois(html);
    const doisTexto = extrairDois(texto);

    // Se o HTML capturou DOIs que o texto puro do navegador perdeu (caso típico do Lattes!):
    if (doisHtml.length > doisTexto.length) {
      ev.preventDefault();
      const n = mesclarDoisNaEntrada(doisHtml, !el.entrada.value.trim());
      el.status.textContent = `✨ ${n} DOI(s) extraído(s) automaticamente dos links/ícones do Lattes colado!`;
    }
  }
});

// 2. Leitura de Arquivo (curriculo.xml ou lattes.html)
function processarArquivo(arquivo) {
  if (!arquivo) return;
  const leitor = new FileReader();
  leitor.onload = (e) => {
    const conteudo = String(e.target?.result || "");
    const dois = extrairDois(conteudo);
    if (!dois.length) {
      el.status.textContent = `⚠️ Nenhum DOI identificado no arquivo "${arquivo.name}".`;
      return;
    }
    const n = mesclarDoisNaEntrada(dois, !el.entrada.value.trim());
    el.status.textContent = `✅ ${n} DOI(s) extraído(s) com sucesso de "${arquivo.name}"!`;
  };
  leitor.onerror = () => {
    el.status.textContent = `❌ Erro ao ler o arquivo "${arquivo.name}".`;
  };
  leitor.readAsText(arquivo);
}

el.btnImportarLattes?.addEventListener("click", () => el.arquivoLattes.click());
el.arquivoLattes?.addEventListener("change", (ev) => {
  const file = ev.target.files?.[0];
  if (file) processarArquivo(file);
  ev.target.value = "";
});

// 3. Drag & Drop sobre a caixa de texto
el.entrada.addEventListener("dragover", (ev) => {
  ev.preventDefault();
  el.entrada.style.borderColor = "var(--azul)";
  el.entrada.style.background = "#f0f7ff";
});
el.entrada.addEventListener("dragleave", () => {
  el.entrada.style.borderColor = "";
  el.entrada.style.background = "";
});
el.entrada.addEventListener("drop", (ev) => {
  ev.preventDefault();
  el.entrada.style.borderColor = "";
  el.entrada.style.background = "";
  const files = ev.dataTransfer?.files;
  if (files && files.length > 0) {
    processarArquivo(files[0]);
  }
});

// 4. Botão Limpar
el.btnLimpar?.addEventListener("click", () => {
  cancelando = true;
  if (el.btnParar) el.btnParar.hidden = true;
  el.entrada.value = "";
  el.container.hidden = true;
  el.corpo.innerHTML = "";
  el.placar.style.display = "none";
  el.status.textContent = "";
  el.csv.disabled = true;
  resultados = [];
  todosAbertos = false;
  if (el.btnToggleTodos) el.btnToggleTodos.textContent = "➕ Expandir Todos";
  if (el.filtroTabela) el.filtroTabela.value = "";
});

carregarBases();
