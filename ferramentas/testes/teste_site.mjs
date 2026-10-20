// Testes do site público. Rode a partir de C:\Scopus:
//   python ferramentas/testes/criar_planilha_ficticia.py
//   python ferramentas/gerar_base_site.py ferramentas/testes/citescore_FICTICIO_2025.xlsx --saida ferramentas/testes/saida
//   node ferramentas/testes/teste_site.mjs            (inclui chamadas reais a Crossref/OpenAlex)
//   node ferramentas/testes/teste_site.mjs --offline  (só testes unitários)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  extrairDois, normalizarIssn, montarIndice, calcularEstrato, fatorAutores,
  melhorArea, avaliarDoi, avaliarRevista, consultarJcr,
} from "../../logica.js";

const aqui = dirname(fileURLToPath(import.meta.url));
const ler = (f) => JSON.parse(readFileSync(join(aqui, "saida", f), "utf8"));
const regras = ler("regras.json");
const base = ler("citescore.json");
const indice = montarIndice(base);
let falhas = 0;

async function teste(nome, fn) {
  try { await fn(); console.log(`ok   ${nome}`); }
  catch (e) { falhas++; console.log(`FALHA ${nome}\n     ${e.message}`); }
}

// ---------------- Unitários ----------------
await teste("extrairDois: formatos variados, duplicados e pontuação", () => {
  const txt = `10.1016/j.cej.2020.127573
    https://doi.org/10.1038/S41586-020-2649-2.
    doi:10.1016/S0140-6736(20)30183-5, (ver 10.1021/acs.est.0c01234)
    https://dx.doi.org/10.1016%2Fj.cej.2020.127573
    10.1016/J.CEJ.2020.127573;`;
  assert.deepEqual(extrairDois(txt), [
    "10.1016/j.cej.2020.127573",
    "10.1038/S41586-020-2649-2",
    "10.1016/S0140-6736(20)30183-5",
    "10.1021/acs.est.0c01234",
  ]);
});

await teste("normalizarIssn", () => {
  assert.equal(normalizarIssn("0028-0836"), "00280836");
  assert.equal(normalizarIssn("1234-567x"), "1234567X");
  assert.equal(normalizarIssn("123"), null);
  assert.equal(normalizarIssn(null), null);
});

await teste("regras.json reproduz calcular_estrato do avaliador", () => {
  const casos = [[100, "A1", 15], [99, "A1", 15], [88, "A1", 15], [87, "A2", 13], [75, "A2", 13], [74, "A3", 11],
    [62, "A4", 9], [50, "A4", 9], [49, "A5", 7], [37, "A6", 6], [25, "A6", 6], [24, "A7", 5], [12, "A8", 4], [0, "A8", 4]];
  for (const [p, e, pts] of casos) assert.deepEqual(calcularEstrato(p, regras), { estrato: e, pontos: pts }, `p=${p}`);
});

await teste("fatorAutores igual ao calcular_nota_fracionada", () => {
  assert.equal(fatorAutores(1), 1); assert.equal(fatorAutores(4), 1);
  assert.equal(fatorAutores(5), 0.8); assert.equal(fatorAutores(8), 0.5);
  assert.equal(fatorAutores(0), 1); assert.equal(fatorAutores("x"), 1);
});

await teste("consultarJcr: encontra JIF e quartil por ISSN e título", () => {
  const baseJcrFicticia = {
    issn: { "13858947": [12.5, "Q1"] },
    titulos: { "nature": [56.1, "Q1"] }
  };
  assert.deepEqual(consultarJcr(baseJcrFicticia, ["1385-8947"]), { jcr: 12.5, jcr_quartil: "Q1" });
  assert.deepEqual(consultarJcr(baseJcrFicticia, [], ["Nature"]), { jcr: 56.1, jcr_quartil: "Q1" });
  assert.deepEqual(consultarJcr(baseJcrFicticia, ["9999-9999"]), { jcr: null, jcr_quartil: null });
});

await teste("base fictícia: ISSN com zero perdido no Excel e aba/linha de cabeçalho detectadas", () => {
  assert.equal(base.meta.ano_citescore, 2025);
  assert.equal(base.meta.n_revistas, 3);
  assert.ok(indice.porIssn.get("00280836"), "Nature por ISSN impresso");
  assert.ok(indice.porIssn.get("18733212"), "CEJ por E-ISSN");
});

await teste("melhorArea: maior percentil entre áreas da Tabela 2", () => {
  const m = melhorArea(indice.porIssn.get("13858947"), regras);
  assert.equal(m.asjc, 1500); assert.equal(m.estrato, "A1");
  assert.equal(m.area_principal, "Engineering - Chemical");
  assert.equal(melhorArea(indice.porIssn.get("00280836"), regras), null, "Nature só tem 1000");
});

await teste("avaliarRevista: fallback por título e fracionamento", () => {
  const r = avaliarRevista({ issns: [], revista: "Revista Teste Baixo Percentil", n_autores: 8 }, indice, regras);
  assert.equal(r.status, "ok"); assert.equal(r.estrato, "A8");
  assert.equal(r.nota_final_calculada, 2); // 4 pts * 4/8
  assert.match(r.scopus_via, /título/);
});

// ---------------- Ponta a ponta (rede) ----------------
if (!process.argv.includes("--offline")) {
  const ctx = { indice, regras, email: "" };

  await teste("e2e: artigo do Chemical Engineering Journal -> A1", async () => {
    const r = await avaliarDoi("10.1016/j.cej.2020.127573", ctx);
    assert.equal(r.status, "ok", r.motivo);
    assert.equal(r.estrato, "A1");
    assert.ok(r.titulo && r.n_autores > 0 && r.ano >= 2020, JSON.stringify({ t: r.titulo, n: r.n_autores, a: r.ano }));
    assert.equal(r.nota_final_calculada, Math.round(15 * fatorAutores(r.n_autores) * 100) / 100);
    console.log(`     "${r.titulo.slice(0, 70)}…" | ${r.n_autores} autores | ${r.ano} | nota ${r.nota_final_calculada}`);
  });

  await teste("e2e: artigo na Nature -> fora das áreas", async () => {
    const r = await avaliarDoi("https://doi.org/10.1038/s41586-020-2649-2", ctx);
    assert.equal(r.status, "fora_areas", r.motivo);
    assert.ok(r.n_autores > 4);
  });

  await teste("e2e: revista fora da base -> sem_scopus (com metadados)", async () => {
    const r = await avaliarDoi("10.1021/acs.est.0c01234", ctx);
    assert.ok(["sem_scopus", "doi_nao_encontrado"].includes(r.status), r.status);
  });

  await teste("e2e: DOI inexistente", async () => {
    const r = await avaliarDoi("10.9999/nao-existe-123456789", ctx);
    assert.equal(r.status, "doi_nao_encontrado");
  });
}

console.log(falhas ? `\n${falhas} teste(s) falharam.` : "\nTodos os testes passaram.");
process.exit(falhas ? 1 : 0);
