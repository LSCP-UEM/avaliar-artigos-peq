import openpyxl
import json
import re
import os

def norm_issn(s):
    if not s:
        return None
    s = str(s).replace('-', '').strip().upper()
    return s if len(s) == 8 and re.match(r'^\d{7}[\dX]$', s) else None

def norm_title(t):
    if not t:
        return ""
    t = str(t).lower()
    t = re.sub(r'[\u0300-\u036f]', '', t)
    t = t.replace('&', ' and ')
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    return t

file_path = 'C:/Scopus/JCR  Impact Factor 2026.xlsx'
wb = openpyxl.load_workbook(file_path, read_only=True)
ws = wb['JCR_Journal Res']

# Headers
header = None
por_issn = {}
por_titulo = {}

ordem_q = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:
        header = [str(c).strip() for c in row]
        continue
    
    nome = str(row[0] or "").strip()
    issn1 = norm_issn(row[4])
    issn2 = norm_issn(row[5])
    disc = str(row[6] or "").strip()
    raw_jif = row[8]
    quartil = str(row[9] or "").strip().upper()
    
    if quartil not in ordem_q:
        quartil = ""
        
    try:
        jif = round(float(raw_jif), 3) if raw_jif is not None and str(raw_jif).strip() != '' else None
    except ValueError:
        jif = None
        
    if jif is None:
        continue
        
    registro = {
        "jif": jif,
        "q": quartil or None,
        "d": disc if disc and disc != '["Multiple"]' else None
    }
    
    # Atualiza ou melhora se já existe (prefere Q1 sobre Q2)
    def atualizar(chave, mapa):
        if chave not in mapa:
            mapa[chave] = registro
        else:
            atual = mapa[chave]
            q_atual = ordem_q.get(atual.get("q"), 99)
            q_novo = ordem_q.get(registro.get("q"), 99)
            if q_novo < q_atual:
                mapa[chave] = registro

    if issn1:
        atualizar(issn1, por_issn)
    if issn2:
        atualizar(issn2, por_issn)
    if nome:
        t_norm = norm_title(nome)
        if t_norm:
            atualizar(t_norm, por_titulo)

print(f"Total de ISSNs mapeados: {len(por_issn)}")
print(f"Total de títulos mapeados: {len(por_titulo)}")

# Compactando para o JSON final
# { "issn": { "13858947": [15.1, "Q1"], ... }, "titulos": { ... } }
dados_finais = {
    "ano": 2026,
    "total_issn": len(por_issn),
    "issn": {k: [v["jif"], v["q"]] for k, v in por_issn.items()},
    # Apenas títulos únicos para fallback
    "titulos": {k: [v["jif"], v["q"]] for k, v in por_titulo.items() if len(k) > 5}
}

os.makedirs('C:/Scopus/data', exist_ok=True)
out_path = 'C:/Scopus/data/jcr.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(dados_finais, f, separators=(',', ':'))

tamanho_kb = os.path.getsize(out_path) / 1024
print(f"Arquivo gerado: {out_path} ({tamanho_kb:.1f} KB)")

# Teste com algumas revistas conhecidas
testes = [
    ("Chemical Engineering Journal", "1385-8947"),
    ("Journal of Colloid and Interface Science", "0021-9797"),
    ("Nature", "0028-0836"),
    ("Desalination", "0011-9164"),
    ("Sensors and Actuators B: Chemical", "0925-4005")
]
for nome, issn in testes:
    i_norm = norm_issn(issn)
    res = dados_finais["issn"].get(i_norm) or dados_finais["titulos"].get(norm_title(nome))
    print(f"  {nome} ({issn}): JIF = {res[0] if res else 'N/A'}, Quartil = {res[1] if res else 'N/A'}")
