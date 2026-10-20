import { extrairDois } from "../../logica.js";

const testCases = [
  {
    input: '<a href="http://dx.doi.org/10.1016/j.cej.2020.127573"></a>',
    esperado: ["10.1016/j.cej.2020.127573"]
  },
  {
    input: '<a href="https://doi.org/10.1016/j.jcis.2021.05.042?utm_source=lattes#secao"></a>',
    esperado: ["10.1016/j.jcis.2021.05.042"]
  },
  {
    input: '<a href="http://dx.doi.org/10.1021/acs.est.0c05876&quot; target=&quot;_blank&quot;">',
    esperado: ["10.1021/acs.est.0c05876"]
  },
  {
    input: '<DADOS-BASICOS-DO-ARTIGO DOI="10.1038/s41586-020-2649-2" />',
    esperado: ["10.1038/s41586-020-2649-2"]
  },
  {
    input: 'Texto puro com DOI: 10.1002/anie.202008432.',
    esperado: ["10.1002/anie.202008432"]
  }
];

let falhas = 0;
for (const tc of testCases) {
  const obtido = extrairDois(tc.input);
  const ok = JSON.stringify(obtido) === JSON.stringify(tc.esperado);
  console.log(`Input: ${tc.input.slice(0, 50)}... -> Obtido: ${JSON.stringify(obtido)} [${ok ? "OK" : "FALHA"}]`);
  if (!ok) falhas++;
}

if (falhas > 0) {
  console.log(`\n${falhas} testes falharam.`);
  process.exit(1);
} else {
  console.log("\nTodos os testes passaram com sucesso!");
}
