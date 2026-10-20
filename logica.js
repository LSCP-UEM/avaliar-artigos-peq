// Lógica pura do avaliador público de DOIs (funciona no navegador e no Node 18+).
// Reproduz as regras do avaliador_scopus.py SEM usar a API da Scopus:
//   metadados  -> Crossref + OpenAlex (gratuitos, com CORS)
//   periódicos -> data/fontes_scopus.json (49.104 periódicos oficiais da Scopus)
//   percentis  -> data/citescore.json (quando disponível) OU consulta direta no link da Scopus
//   regras     -> data/regras.json (extraído do avaliador_scopus.py - 132 códigos ASJC)

// ----------------------------------------------------------------------------
// 1. DOIs e ISSNs
// ----------------------------------------------------------------------------
const PADRAO_DOI = /10\.\d{4,9}\/[^\s"'<>,]+/gi;

/** Extrai DOIs únicos de um texto livre. */
export function extrairDois(texto) {
  let fonte = String(texto || "");
  fonte = fonte.replace(/%2F/gi, "/");
  const vistos = new Map();
  for (const m of fonte.matchAll(PADRAO_DOI)) {
    let doi = m[0];
    // Remove query params e hash se veio de URL (?utm=..., #...)
    doi = doi.split(/[?#]/)[0];
    // Corta entidades HTML que possam ter ficado grudadas
    doi = doi.replace(/&(?:quot|apos|lt|gt|amp|#\d+|#x[0-9a-f]+);?.*$/i, "");
    while (/[.;:\]}'"\/]$/.test(doi) || (doi.endsWith(")") && contar(doi, ")") > contar(doi, "("))) {
      doi = doi.slice(0, -1);
    }
    try { if (doi.includes("%")) doi = decodeURIComponent(doi); } catch { /* mantém */ }
    if (!doi || !doi.startsWith("10.")) continue;
    const chave = doi.toLowerCase();
    if (!vistos.has(chave)) vistos.set(chave, doi);
  }
  return [...vistos.values()];
}

function contar(s, c) { return s.split(c).length - 1; }

export function normalizarIssn(valor) {
  const s = String(valor || "").toUpperCase().replace(/[^0-9X]/g, "");
  return /^\d{7}[\dX]$/.test(s) ? s : null;
}

export function formatarIssn(issn) {
  return issn && issn.length === 8 ? `${issn.slice(0, 4)}-${issn.slice(4)}` : issn || "";
}

function normalizarTitulo(t) {
  return String(t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ").replace(/^the\s+/, "").replace(/[^a-z0-9]+/g, " ").trim();
}

// ----------------------------------------------------------------------------
// 2. Base de periódicos e regras do edital
// ----------------------------------------------------------------------------
/** Monta índices ISSN -> revista e título -> revista. */
export function montarIndice(base) {
  const porIssn = new Map();
  const porTitulo = new Map();
  const ambiguos = new Set();
  for (const r of base?.revistas || []) {
    for (const i of r.issn || []) porIssn.set(i, r);
    const t = normalizarTitulo(r.t);
    if (!t) continue;
    if (porTitulo.has(t)) ambiguos.add(t); else porTitulo.set(t, r);
  }
  for (const t of ambiguos) porTitulo.delete(t);
  return { porIssn, porTitulo, meta: base?.meta || null };
}

/** Mesma tabela do calcular_estrato() do avaliador (percentil 0..100). */
export function calcularEstrato(percentil, regras) {
  const p = Math.max(0, Math.min(100, Math.floor(Number(percentil))));
  const [estrato, pontos] = regras.estrato_por_percentil[p];
  return { estrato, pontos };
}

/** Mesma regra do calcular_nota_fracionada(): até 4 autores = integral; acima, 4/n. */
export function fatorAutores(n) {
  const k = Math.max(1, parseInt(n, 10) || 1);
  return k <= 4 ? 1 : 4 / k;
}

export function nomeAsjc(code, regras) {
  return regras?.asjc_nomes?.[String(code)] || `Sub-área ${code}`;
}

/** Avalia as áreas da revista: identifica se tem percentis embutidos ou apenas códigos ASJC. */
export function melhorArea(revista, regras) {
  const analise = analisarAreas(revista, regras);
  return analise.melhor || null;
}

export function analisarAreas(revista, regras) {
  const areasBrutas = revista.a || [];
  const temPercentis = areasBrutas.length > 0 && Array.isArray(areasBrutas[0]);

  if (temPercentis) {
    // Modo com métricas embutidas (citescore.json)
    const todas = areasBrutas.map(([asjc, pct, rank, de]) => ({
      asjc,
      nome: nomeAsjc(asjc, regras),
      percentil: pct,
      rank,
      de,
      area_edital: regras?.asjc_edital?.[String(asjc)] || null,
    }));
    let melhor = null;
    for (const a of todas) {
      if (a.percentil == null || !a.area_edital) continue;
      if (!melhor || a.percentil > melhor.percentil) melhor = a;
    }
    if (melhor) {
      const calc = calcularEstrato(melhor.percentil, regras);
      melhor = {
        ...melhor,
        ...calc,
        area_detalhe: melhor.nome,
        area_principal: melhor.area_edital,
      };
    }
    return { temPercentis: true, todas, melhor, pontuavel: Boolean(melhor) };
  } else {
    // Modo lista mestra de fontes (fontes_scopus.json)
    const todas = areasBrutas.map((asjc) => ({
      asjc,
      nome: nomeAsjc(asjc, regras),
      percentil: null,
      area_edital: regras?.asjc_edital?.[String(asjc)] || null,
    }));
    const pontuaveis = todas.filter((a) => Boolean(a.area_edital));
    return { temPercentis: false, todas, pontuaveis, pontuavel: pontuaveis.length > 0 };
  }
}

export function localizarRevista(indice, issns, titulos) {
  for (const i of issns) {
    const r = indice.porIssn.get(i);
    if (r) return { revista: r, via: `ISSN ${formatarIssn(i)}` };
  }
  for (const t of titulos) {
    const r = indice.porTitulo.get(normalizarTitulo(t));
    if (r) return { revista: r, via: "título da revista" };
  }
  return null;
}

// ----------------------------------------------------------------------------
// 3. Fontes gratuitas (Crossref e OpenAlex)
// ----------------------------------------------------------------------------
const espera = (ms) => new Promise((ok) => setTimeout(ok, ms));
const caminhoDoi = (doi) => doi.split("/").map(encodeURIComponent).join("/");

async function buscarJson(url, tentativas = 4) {
  for (let i = 0; i < tentativas; i++) {
    let resp;
    try {
      resp = await fetch(url, { headers: { Accept: "application/json" } });
    } catch (e) {
      if (i === tentativas - 1) throw e;
      await espera(800 * 2 ** i);
      continue;
    }
    if (resp.ok) return resp.json();
    if (resp.status === 404) return null;
    if ((resp.status === 429 || resp.status >= 500) && i < tentativas - 1) {
      const retry = Number(resp.headers.get("Retry-After"));
      await espera(retry > 0 ? retry * 1000 : 1000 * 2 ** i);
      continue;
    }
    throw new Error(`HTTP ${resp.status}`);
  }
  return null;
}

export async function buscarCrossref(doi, email) {
  const q = email ? `?mailto=${encodeURIComponent(email)}` : "";
  const j = await buscarJson(`https://api.crossref.org/works/${caminhoDoi(doi)}${q}`);
  return j?.message || null;
}

const CAMPOS_OPENALEX = [
  "id", "doi", "title", "publication_year", "publication_date", "type", "language",
  "authorships", "primary_location", "cited_by_count", "open_access", "is_retracted",
  "biblio", "abstract_inverted_index", "primary_topic", "fwci",
].join(",");

export async function buscarOpenAlex(doi, email) {
  const q = `?select=${CAMPOS_OPENALEX}` + (email ? `&mailto=${encodeURIComponent(email)}` : "");
  return buscarJson(`https://api.openalex.org/works/doi:${caminhoDoi(doi)}${q}`);
}

// ----------------------------------------------------------------------------
// 4. Montagem do resultado
// ----------------------------------------------------------------------------
const primeiro = (v) => (Array.isArray(v) ? v.find((x) => x) : v) || null;

function anoCrossref(cr) {
  for (const k of ["published", "issued", "published-print", "published-online"]) {
    const ano = cr?.[k]?.["date-parts"]?.[0]?.[0];
    if (ano) return Number(ano);
  }
  return null;
}

function resumoOpenAlex(inv) {
  if (!inv) return null;
  const palavras = [];
  for (const [p, posicoes] of Object.entries(inv)) for (const i of posicoes) palavras[i] = p;
  return palavras.filter(Boolean).join(" ") || null;
}

function limparJats(s) {
  return s ? s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim() : null;
}

/** Junta Crossref + OpenAlex num objeto de metadados. */
export function combinarMetadados(doi, cr, oa) {
  const fonteOa = oa?.primary_location?.source || null;
  const autoresCr = (cr?.author || [])
    .map((a) => (a.family ? [a.family, a.given].filter(Boolean).join(", ") : a.name))
    .filter(Boolean);
  const autoresOa = (oa?.authorships || []).map((a) => a?.author?.display_name).filter(Boolean);
  const autores = autoresCr.length ? autoresCr : autoresOa;

  const issns = [...new Set([
    ...(cr?.["issn-type"] || []).map((x) => x.value),
    ...(cr?.ISSN || []),
    ...(fonteOa?.issn || []),
    fonteOa?.issn_l,
  ].map(normalizarIssn).filter(Boolean))];

  const pag = cr?.page || [oa?.biblio?.first_page, oa?.biblio?.last_page].filter(Boolean).join("-");
  const retratadoCr = (cr?.["updated-by"] || []).some((u) => /retract/i.test(u?.type || ""));

  return {
    doi,
    link_doi: `https://doi.org/${doi}`,
    titulo: primeiro(cr?.title) || oa?.title || null,
    autores,
    n_autores: autores.length || 1,
    ano: anoCrossref(cr) || oa?.publication_year || null,
    data_publicacao: oa?.publication_date || null,
    revista: primeiro(cr?.["container-title"]) || fonteOa?.display_name || null,
    revista_abrev: primeiro(cr?.["short-container-title"]) || null,
    editora: cr?.publisher || fonteOa?.host_organization_name || null,
    tipo: cr?.type || oa?.type || null,
    volume: cr?.volume || oa?.biblio?.volume || null,
    numero: cr?.issue || oa?.biblio?.issue || null,
    paginas: pag || cr?.["article-number"] || null,
    issns,
    idioma: oa?.language || cr?.language || null,
    citacoes_crossref: cr?.["is-referenced-by-count"] ?? null,
    citacoes_openalex: oa?.cited_by_count ?? null,
    fwci: oa?.fwci ?? null,
    acesso_aberto: oa?.open_access ? (oa.open_access.is_oa ? oa.open_access.oa_status : "fechado") : null,
    link_acesso_aberto: oa?.open_access?.oa_url || null,
    retratado: Boolean(oa?.is_retracted || retratadoCr),
    topico_openalex: oa?.primary_topic?.display_name || null,
    resumo: limparJats(cr?.abstract) || resumoOpenAlex(oa?.abstract_inverted_index),
    fontes_metadados: [cr && "Crossref", oa && "OpenAlex"].filter(Boolean),
  };
}

/** Avalia a revista contra a base Scopus e o edital. */
export function avaliarRevista(meta, indice, regras) {
  const achado = localizarRevista(indice, meta.issns, [meta.revista, meta.revista_abrev].filter(Boolean));
  if (!achado) {
    const issnPrincipal = meta.issns[0];
    const linkScopusFallback = issnPrincipal
      ? `https://www.scopus.com/sources.uri?issn=${issnPrincipal}`
      : "https://www.scopus.com/sources.uri";
    return {
      status: "sem_scopus",
      motivo: "Revista não localizada no catálogo oficial da Scopus",
      link_revista: linkScopusFallback,
    };
  }

  const r = achado.revista;
  const analise = analisarAreas(r, regras);
  const fator = fatorAutores(meta.n_autores);
  const linkRevista = `https://www.scopus.com/sourceid/${r.id}`;

  const baseScopus = {
    scopus_source_id: r.id,
    scopus_titulo: r.t,
    scopus_via: achado.via,
    scopus_ativa: r.act ?? true,
    link_revista: linkRevista,
    todas_areas: analise.todas,
    fator_divisao: fator,
  };

  if (!analise.pontuavel) {
    return {
      ...baseScopus,
      status: "fora_areas",
      motivo: "Revista indexada na Scopus, mas fora das áreas de avaliação do Edital (Tabela 2)",
    };
  }

  if (analise.temPercentis) {
    // Caso tenhamos o arquivo com métricas
    const m = analise.melhor;
    const { estrato, pontos } = calcularEstrato(m.percentil, regras);
    return {
      ...baseScopus,
      status: "ok",
      estrato,
      percentil: m.percentil,
      rank: m.rank,
      rank_de: m.de,
      quartil: m.percentil >= 75 ? "Q1" : m.percentil >= 50 ? "Q2" : m.percentil >= 25 ? "Q3" : "Q4",
      area_code: m.asjc,
      area_detalhe: m.nome,
      area_principal: m.area_edital,
      pontos_base: pontos,
      nota_final_calculada: Math.round(pontos * fator * 100) / 100,
      motivo: "Avaliado automaticamente via métricas Scopus",
    };
  } else {
    // Modo link direto: revista confirmada na Scopus e com áreas na Tabela 2!
    const areasNomes = analise.pontuaveis.map((a) => a.area_edital).filter((v, i, arr) => arr.indexOf(v) === i);
    return {
      ...baseScopus,
      status: "scopus_link",
      areas_edital: areasNomes.join(" / "),
      motivo: "Revista confirmada na Scopus. Clique no link para conferir o percentil oficial.",
    };
  }
}

/** Calcula nota fracionada para um percentil informado manualmente. */
export function calcularNotaManual(percentil, n_autores, regras) {
  if (percentil == null || percentil === "" || isNaN(percentil)) return null;
  const p = Number(percentil);
  const { estrato, pontos } = calcularEstrato(p, regras);
  const fator = fatorAutores(n_autores);
  const nota = Math.round(pontos * fator * 100) / 100;
  return {
    percentil: p,
    estrato,
    pontos_base: pontos,
    fator_divisao: fator,
    nota_final_calculada: nota,
  };
}

/** Pipeline completo de um DOI. */
export async function avaliarDoi(doi, { indice, regras, email } = {}) {
  try {
    const [cr, oa] = await Promise.all([
      buscarCrossref(doi, email).catch(() => null),
      buscarOpenAlex(doi, email).catch(() => null),
    ]);
    if (!cr && !oa) return { doi, link_doi: `https://doi.org/${doi}`, status: "doi_nao_encontrado", motivo: "DOI não localizado no Crossref nem no OpenAlex" };
    const meta = combinarMetadados(doi, cr, oa);
    if (!indice || !regras) return { ...meta, status: "sem_base", motivo: "Base de periódicos não carregada" };
    return { ...meta, ...avaliarRevista(meta, indice, regras) };
  } catch (e) {
    return { doi, link_doi: `https://doi.org/${doi}`, status: "erro", motivo: `Erro: ${e.message || e}` };
  }
}

/** Executa tarefas com concorrência limitada. */
export async function emParalelo(itens, limite, tarefa, aoTerminar) {
  let proximo = 0;
  const trabalhador = async () => {
    while (proximo < itens.length) {
      const i = proximo++;
      const r = await tarefa(itens[i], i);
      aoTerminar?.(r, i);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limite, itens.length) }, trabalhador));
}
