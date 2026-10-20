"""Cria uma planilha FICTÍCIA no formato da 'CiteScore metrics' da Scopus, só para testes.

Os percentis abaixo são inventados. NUNCA publique o JSON gerado a partir deste arquivo.
"""
from pathlib import Path

import openpyxl

DESTINO = Path(__file__).with_name("citescore_FICTICIO_2025.xlsx")

CABECALHO = [
    "Scopus Source ID", "Title", "CiteScore 2025", "Highest percentile", "2022-25 Citations",
    "2022-25 Documents", "% Cited", "SNIP", "SJR", "Scopus ASJC Code (Sub-subject Area)",
    "Scopus Sub-Subject Area", "Percentile", "RANK", "Rank Out Of", "Publisher", "Type",
    "Open Access", "Quartile", "URL Scopus Source ID", "Print ISSN", "E-ISSN",
]

# (source_id, título, citescore, snip, sjr, asjc, nome, percentil, rank, de, editora, oa, print, eissn)
LINHAS = [
    (16399, "Chemical Engineering Journal", 21.7, 2.1, 2.9, 1500, "General Chemical Engineering", 99, 2, 300, "Elsevier", "NO", "13858947", "18733212"),
    (16399, "Chemical Engineering Journal", 21.7, 2.1, 2.9, 1600, "General Chemistry", 97, 12, 400, "Elsevier", "NO", "13858947", "18733212"),
    (16399, "Chemical Engineering Journal", 21.7, 2.1, 2.9, 2304, "Environmental Chemistry", 60, 50, 125, "Elsevier", "NO", "13858947", "18733212"),
    # Nature: ISSN numérico (Excel perde o zero à esquerda) e só área Multidisciplinary -> fora da Tabela 2
    (21206, "Nature", 90.0, 11.0, 18.0, 1000, "Multidisciplinary", 99, 1, 150, "Nature Portfolio", "NO", 280836, "14764687"),
    # Revista com uma área pontuável de percentil baixo (A8)
    (99999, "Revista Teste Baixo Percentil", 0.5, 0.1, 0.1, 1700, "General Computer Science", 10, 900, 1000, "Editora X", "YES", "12345679", None),
]


def main():
    wb = openpyxl.Workbook()
    sobre = wb.active
    sobre.title = "About CiteScore"
    sobre["A1"] = "Arquivo fictício para testes."
    ws = wb.create_sheet("CiteScore 2025")
    ws.append(["CiteScore 2025 - dados FICTÍCIOS"])
    ws.append([])
    ws.append(CABECALHO)
    for (sid, t, cs, snip, sjr, asjc, nome, pct, rank, de, pub, oa, p_issn, e_issn) in LINHAS:
        q = "Q1" if pct >= 75 else "Q2" if pct >= 50 else "Q3" if pct >= 25 else "Q4"
        ws.append([sid, t, cs, pct, 0, 0, 0, snip, sjr, asjc, nome, pct, rank, de, pub, "Journal", oa, q,
                   f"https://www.scopus.com/sourceid/{sid}", p_issn, e_issn])
    wb.save(DESTINO)
    print(f"Planilha fictícia criada: {DESTINO}")


if __name__ == "__main__":
    main()
