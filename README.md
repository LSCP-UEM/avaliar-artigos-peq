# Avaliador de Artigos por DOI — PEQ / UEM 🎓

Aplicação web pública e gratuita para consulta de metadados, indexação na Scopus e cálculo de pontuação curricular para o processo seletivo do **Programa de Pós-Graduação em Engenharia Química da Universidade Estadual de Maringá (PEQ/UEM)**.

🌐 **Acesse online:** [https://lscp-uem.github.io/avaliar-artigos-peq/](https://lscp-uem.github.io/avaliar-artigos-peq/)

---

## 🎯 Funcionalidades

1. **Consulta em Lote por DOI:** Cole uma lista com dezenas de DOIs e obtenha instantaneamente o título, ano de publicação, lista completa de autores, ISSN e nome da revista via Crossref e OpenAlex.
2. **Checagem de Indexação Oficial na Scopus:** Cruza o ISSN/título do periódico com o catálogo oficial da Scopus (**49.104 fontes cadastradas**), identificando se a revista está ativa ou descontinuada.
3. **Enquadramento na Tabela 2 do Edital (QS):** Verifica se as subáreas ASJC da revista pertencem às **132 áreas pontuáveis** definidas no Edital de Seleção do PEQ/UEM (Engenharia Química, Química, Ciências Ambientais, etc.).
4. **Link Oficial para Consulta de Percentil:** Cada artigo possui um botão direto para a página pública da revista na Scopus (`https://www.scopus.com/sourceid/{id}`), sem necessidade de login.
5. **Calculadora Dinâmica de Estrato e Coautoria:**
   * Ao informar o percentil CiteScore visto na Scopus, calcula o estrato oficial (**A1 a A8**, de 15 a 4 pontos).
   * Aplica a fórmula oficial de fracionamento por autoria: integral até 4 autores; fator de $4/n$ quando $n > 4$.
6. **Exportação para Excel:** Baixe a planilha consolidada em formato `.csv` compatível com Excel em português.

---

## 💻 Como Rodar Localmente

A aplicação é puramente estática (*client-side*), sem necessidade de banco de dados ou servidor backend complexo:

```bash
# Clone o repositório
git clone https://github.com/LSCP-UEM/avaliar-artigos-peq.git
cd avaliar-artigos-peq

# Inicie um servidor local simples
python -m http.server 8000
```

Abra o navegador em `http://localhost:8000`.

---

## 🛠️ Estrutura do Repositório

```text
├── index.html              # Interface do usuário (responsiva e leve)
├── app.js                  # Orquestração da interface e eventos
├── logica.js               # Motor de regras, cálculo e consulta a APIs públicas
├── data/
│   ├── regras.json         # 132 códigos ASJC e tabela de estratos do Edital
│   └── fontes_scopus.json  # Catálogo oficial com 49.104 fontes da Scopus
├── ferramentas/
│   ├── gerar_base_site.py  # Script CLI para atualizar regras e converter planilhas Scopus
│   └── testes/             # Suíte de testes automatizados unitários e e2e
├── avaliador_scopus.py     # Código de referência com regras do PEQ/UEM
└── README.md
```

---

## ⚖️ Critérios do Edital PEQ/UEM

| Percentil Scopus | Estrato | Pontos Base |
| :---: | :---: | :---: |
| $\ge 87{,}5\%$ | **A1** | 15,0 pts |
| $\ge 75{,}0\%$ a $< 87{,}5\%$ | **A2** | 13,0 pts |
| $\ge 62{,}5\%$ a $< 75{,}0\%$ | **A3** | 11,0 pts |
| $\ge 50{,}0\%$ a $< 62{,}5\%$ | **A4** | 9,0 pts |
| $\ge 37{,}5\%$ a $< 50{,}0\%$ | **A5** | 7,0 pts |
| $\ge 25{,}0\%$ a $< 37{,}5\%$ | **A6** | 6,0 pts |
| $\ge 12{,}5\%$ a $< 25{,}0\%$ | **A7** | 5,0 pts |
| $< 12{,}5\%$ | **A8** | 4,0 pts |

*Fator de Autores:* $1{,}0$ para até 4 autores; $\frac{4}{n}$ para mais de 4 autores.
