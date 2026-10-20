"""
Gera os dados estáticos do site público de consulta de DOIs (pasta ``site/``).

O site NÃO usa a API da Scopus. Em vez disso, ele consulta:
  * Crossref / OpenAlex (gratuitos, direto do navegador) para os metadados do artigo;
  * ``site/data/citescore.json`` (gerado por este script) para o percentil CiteScore
    da revista em cada área ASJC;
  * ``site/data/regras.json`` (gerado por este script) com as regras do edital,
    extraídas diretamente do ``avaliador_scopus.py`` (fonte única da verdade).

Uso (uma vez por ano, quando a Scopus publicar o CiteScore novo, ~junho):

    1. Baixe a planilha "CiteScore metrics" em https://www.scopus.com/sources
       (botão "Download Scopus Source List" / "CiteScore metrics" -> .xlsx).
    2. Rode:
           python ferramentas/gerar_base_site.py caminho/para/CiteScore_2025.xlsx

Opções:
    --ano 2025        Força o ano do CiteScore (se não der para detectar no cabeçalho).
    --saida DIR       Pasta de saída (padrão: site/data).
    --so-regras       Regera apenas o regras.json (não precisa da planilha).
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AVALIADOR = RAIZ / "avaliador_scopus.py"
SAIDA_PADRAO = RAIZ / "data"


# =====================================================================
# 1. REGRAS DO EDITAL (extraídas do avaliador_scopus.py, sem importá-lo)
# =====================================================================
def _ler_fonte(caminho: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return caminho.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Não consegui ler {caminho}")


def extrair_regras(caminho: Path = AVALIADOR) -> dict:
    """Lê ASJC_MAP, ASJC_TO_QS_EDITAL e as funções de pontuação do avaliador via AST.

    Usar AST evita importar o módulo (que depende de streamlit/pybliometrics).
    """
    fonte = _ler_fonte(caminho)
    arvore = ast.parse(fonte)

    dicionarios = {}
    funcoes = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            nome = no.targets[0].id
            if nome in ("ASJC_MAP", "ASJC_TO_QS_EDITAL"):
                dicionarios[nome] = ast.literal_eval(no.value)
        elif isinstance(no, ast.FunctionDef) and no.name in ("calcular_estrato", "calcular_nota_fracionada"):
            funcoes[no.name] = ast.get_source_segment(fonte, no)

    faltando = {"ASJC_MAP", "ASJC_TO_QS_EDITAL"} - dicionarios.keys()
    faltando |= {"calcular_estrato", "calcular_nota_fracionada"} - funcoes.keys()
    if faltando:
        raise SystemExit(f"Não encontrei no avaliador_scopus.py: {sorted(faltando)}")

    # Executa só as duas funções puras, isoladas, para reproduzir o comportamento exato.
    ns: dict = {}
    for codigo in funcoes.values():
        exec(codigo, {}, ns)  # noqa: S102 - código local e confiável (o próprio repo)
    calcular_estrato = ns["calcular_estrato"]
    calcular_nota_fracionada = ns["calcular_nota_fracionada"]

    # Percentis CiteScore são inteiros de 0 a 99 -> tabela exata 0..100.
    estrato_por_percentil = [list(calcular_estrato(float(p))) for p in range(101)]

    # O site implementa o fracionamento como: n <= 4 -> 1 ; n > 4 -> 4/n.
    # Se a regra mudar no avaliador, falhamos aqui para não publicar algo divergente.
    for n in range(1, 101):
        esperado = 1.0 if n <= 4 else 4.0 / n
        obtido = calcular_nota_fracionada(1.0, n)
        if not math.isclose(obtido, esperado):
            raise SystemExit(
                f"A regra de fracionamento do avaliador mudou (n={n}: {obtido} != {esperado}). "
                "Atualize fatorAutores() em site/logica.js."
            )

    return {
        "fonte": "avaliador_scopus.py",
        "gerado_em": dt.datetime.now().isoformat(timespec="seconds"),
        "asjc_nomes": {str(k): v for k, v in sorted(dicionarios["ASJC_MAP"].items())},
        "asjc_edital": {str(k): v for k, v in sorted(dicionarios["ASJC_TO_QS_EDITAL"].items())},
        "estrato_por_percentil": estrato_por_percentil,
    }


# =====================================================================
# 2. PLANILHA CITESCORE -> JSON COMPACTO
# =====================================================================
def _norm(texto) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", str(texto).lower()).strip()


# Cada coluna lógica -> função que reconhece o cabeçalho normalizado.
COLUNAS = {
    "source_id": lambda n: n in ("scopus source id", "sourcerecord id", "source id"),
    "titulo": lambda n: n in ("title", "source title"),
    "citescore": lambda n: re.fullmatch(r"citescore( \d{4})?", n) is not None,
    "sjr": lambda n: n.startswith("sjr"),
    "snip": lambda n: n.startswith("snip"),
    "asjc": lambda n: "asjc" in n and "code" in n,
    "percentil": lambda n: n == "percentile",
    "rank": lambda n: n == "rank",
    "rank_de": lambda n: n == "rank out of",
    "editora": lambda n: n == "publisher",
    "tipo": lambda n: n in ("type", "source type"),
    "oa": lambda n: n == "open access",
    "issn_print": lambda n: n in ("print issn", "issn"),
    "issn_e": lambda n: n in ("e issn", "eissn", "electronic issn"),
}
OBRIGATORIAS = ("source_id", "titulo", "asjc", "percentil")


def normalizar_issn(valor) -> str | None:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    s = str(valor).strip().upper()
    if s.endswith(".0"):
        s = s[:-2]
    s = re.sub(r"[^0-9X]", "", s)
    if not s:
        return None
    if s.isdigit() and len(s) < 8:  # Excel come zeros à esquerda
        s = s.zfill(8)
    return s if re.fullmatch(r"\d{7}[\dX]", s) else None


def _num(valor, tipo=float):
    try:
        if valor is None or (isinstance(valor, float) and math.isnan(valor)):
            return None
        return tipo(float(str(valor).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _mapear_cabecalho(cabecalho: list) -> dict:
    mapa = {}
    for i, bruto in enumerate(cabecalho):
        n = _norm(bruto)
        for chave, reconhece in COLUNAS.items():
            if chave not in mapa and reconhece(n):
                mapa[chave] = i
                break
    return mapa


def _localizar_tabela(caminho: Path):
    """Acha a aba e a linha de cabeçalho que contêm ASJC + Percentile."""
    import openpyxl

    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    for ws in wb.worksheets:
        for idx, linha in enumerate(ws.iter_rows(min_row=1, max_row=30, values_only=True)):
            mapa = _mapear_cabecalho(list(linha))
            if all(c in mapa for c in OBRIGATORIAS) and ("issn_print" in mapa or "issn_e" in mapa):
                return wb, ws, idx + 1, list(linha), mapa
    raise SystemExit(
        "Não encontrei uma aba com as colunas 'Scopus Source ID', 'Title', "
        "'Scopus ASJC Code', 'Percentile' e 'Print ISSN'/'E-ISSN'.\n"
        "Confirme que baixou a planilha de *CiteScore metrics* (não a 'Source title list')."
    )


def converter_planilha(caminho: Path, ano_forcado: int | None = None) -> dict:
    wb, ws, linha_cab, cabecalho, mapa = _localizar_tabela(caminho)

    ano = ano_forcado
    if ano is None and "citescore" in mapa:
        m = re.search(r"(20\d{2})", str(cabecalho[mapa["citescore"]]))
        ano = int(m.group(1)) if m else None
    if ano is None:
        m = re.search(r"(20\d{2})", caminho.name)
        ano = int(m.group(1)) if m else None
    if ano is None:
        raise SystemExit("Não consegui detectar o ano do CiteScore. Use --ano 2025.")

    def pega(linha, chave):
        i = mapa.get(chave)
        return linha[i] if i is not None and i < len(linha) else None

    revistas: dict[str, dict] = {}
    n_linhas = 0
    for linha in ws.iter_rows(min_row=linha_cab + 1, values_only=True):
        sid = pega(linha, "source_id")
        asjc = _num(pega(linha, "asjc"), int)
        if sid in (None, "") or asjc is None:
            continue
        n_linhas += 1
        sid = str(_num(sid, int) or sid).strip()
        r = revistas.get(sid)
        if r is None:
            issns = [x for x in (normalizar_issn(pega(linha, "issn_print")),
                                 normalizar_issn(pega(linha, "issn_e"))) if x]
            oa = str(pega(linha, "oa") or "").strip().upper()
            r = revistas[sid] = {
                "id": sid,
                "t": str(pega(linha, "titulo") or "").strip(),
                "p": str(pega(linha, "editora") or "").strip() or None,
                "tp": str(pega(linha, "tipo") or "").strip() or None,
                "cs": _num(pega(linha, "citescore")),
                "sjr": _num(pega(linha, "sjr")),
                "snip": _num(pega(linha, "snip")),
                "oa": True if oa in ("YES", "Y", "SIM", "TRUE") else (False if oa else None),
                "issn": issns,
                "a": [],
            }
        if any(a[0] == asjc for a in r["a"]):
            continue
        r["a"].append([asjc, _num(pega(linha, "percentil"), int),
                       _num(pega(linha, "rank"), int), _num(pega(linha, "rank_de"), int)])
    wb.close()

    lista = []
    for r in revistas.values():
        r["a"].sort(key=lambda a: -(a[1] if a[1] is not None else -1))
        lista.append({k: v for k, v in r.items() if v not in (None, "")})

    sem_issn = sum(1 for r in lista if not r.get("issn"))
    return {
        "meta": {
            "ano_citescore": ano,
            "arquivo_origem": caminho.name,
            "aba": ws.title,
            "gerado_em": dt.datetime.now().isoformat(timespec="seconds"),
            "n_revistas": len(lista),
            "n_linhas_area": n_linhas,
            "n_revistas_sem_issn": sem_issn,
        },
        "revistas": lista,
    }


# =====================================================================
# 3. CLI
# =====================================================================
def _gravar(obj: dict, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  -> {destino} ({destino.stat().st_size / 1024:.0f} KB)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("planilha", nargs="?", type=Path, help="Planilha .xlsx de CiteScore metrics da Scopus")
    ap.add_argument("--ano", type=int, default=None)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    ap.add_argument("--so-regras", action="store_true")
    args = ap.parse_args(argv)

    print("Regras do edital (avaliador_scopus.py):")
    regras = extrair_regras()
    _gravar(regras, args.saida / "regras.json")
    print(f"  {len(regras['asjc_edital'])} códigos ASJC pontuáveis, {len(regras['asjc_nomes'])} nomes.")

    if args.so_regras:
        return 0
    if not args.planilha:
        ap.error("informe a planilha .xlsx (ou use --so-regras)")
    if not args.planilha.exists():
        ap.error(f"arquivo não encontrado: {args.planilha}")

    print(f"Base CiteScore ({args.planilha.name}):")
    base = converter_planilha(args.planilha, args.ano)
    _gravar(base, args.saida / "citescore.json")
    m = base["meta"]
    print(f"  CiteScore {m['ano_citescore']}: {m['n_revistas']} revistas, "
          f"{m['n_linhas_area']} linhas revista×área, {m['n_revistas_sem_issn']} sem ISSN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
