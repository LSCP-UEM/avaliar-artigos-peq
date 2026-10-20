import os
import configparser
import requests
import xml.etree.ElementTree as ET
import streamlit as st
from pybliometrics.scopus import AbstractRetrieval, SerialTitleISSN, SerialTitle, AuthorRetrieval
# ================= 1. SEGURANÇA E CONFIGURAÇÃO =================
def garantir_configuracao():
    """Garante que a configuração exista e inicializa a Scopus (somente quando chamada)."""
    
    # Importação LÁ DENTRO para não quebrar no carregamento do arquivo
    import pybliometrics.scopus

    # [SEU CÓDIGO DO CAMINHO]
    meu_caminho_cfg = os.path.join(os.getcwd(), "pybliometrics.cfg")

    if not os.path.exists(meu_caminho_cfg):
        config = configparser.ConfigParser()
        config['Authentication'] = {
            'APIKey': st.secrets["SCOPUS_API_KEY"],
            'InstToken': st.secrets["SCOPUS_INST_TOKEN"]
        }
        config['Directories'] = {'AbstractRetrieval': os.path.join(os.getcwd(), 'cache_scopus')}
        with open(meu_caminho_cfg, 'w') as f:
            config.write(f)

    os.environ['PYBLIOMETRICS_CONFIG_FILE'] = meu_caminho_cfg
    
    # Inicializa SOMENTE aqui dentro, depois de garantir o arquivo
    pybliometrics.scopus.init()

    # [O RESTO DA SUA FUNÇÃO DE CONFIGURAÇÃO]
    try:
        API_KEY = st.secrets["SCOPUS_API_KEY"]
        INST_TOKEN = st.secrets["SCOPUS_INST_TOKEN"]
    except Exception:
        raise Exception("Chaves da Scopus não encontradas no st.secrets!")

    config_dir = os.path.join(os.path.expanduser("~"), ".config")
    config_path = os.path.join(config_dir, "pybliometrics.cfg")
    base_scopus = os.path.join(os.path.expanduser("~"), ".scopus")
    
    diretorios = {
        'AbstractRetrieval': os.path.join(base_scopus, 'abstract_retrieval'),
        'AffiliationRetrieval': os.path.join(base_scopus, 'affiliation_retrieval'),
        'AuthorRetrieval': os.path.join(base_scopus, 'author_retrieval'),
        'CitationOverview': os.path.join(base_scopus, 'citation_overview'),
        'ContentAffiliationRetrieval': os.path.join(base_scopus, 'content_affiliation_retrieval'),
        'ContentAuthorRetrieval': os.path.join(base_scopus, 'content_author_retrieval'),
        'PlumXMetrics': os.path.join(base_scopus, 'plumx_metrics'),
        'Retrieval': os.path.join(base_scopus, 'retrieval'),
        'ScopusSearch': os.path.join(base_scopus, 'scopus_search'),
        'Search': os.path.join(base_scopus, 'search'),
        'SerialSearch': os.path.join(base_scopus, 'serial_search'),
        'SerialTitle': os.path.join(base_scopus, 'serial_title'),
        'SerialTitleISSN': os.path.join(base_scopus, 'serial_title_issn'),
        'SerialTitleSourceID': os.path.join(base_scopus, 'serial_title_source_id'),
        'SubjectClassifications': os.path.join(base_scopus, 'subject_classifications')
    }
    
    views = ['ENHANCED', 'STANDARD', 'Ex', 'B', 'META', 'FULL', 'REF', 'CITESCORE', 'COMPLETE']
    for pasta_raiz in diretorios.values():
        os.makedirs(pasta_raiz, exist_ok=True)
        for v in views: os.makedirs(os.path.join(pasta_raiz, v), exist_ok=True)
    
    os.makedirs(config_dir, exist_ok=True)
    config = configparser.ConfigParser()
    config.optionxform = str
    config['Authentication'] = {'APIKey': API_KEY, 'InstToken': INST_TOKEN}
    config['Directories'] = diretorios
    with open(config_path, 'w') as f: config.write(f)

# Roda a configuração assim que o módulo é importado
@st.cache_resource(show_spinner=False)
def ligar_motor_scopus():
    """Liga a API da Elsevier apenas 1x e salva na memória do PC"""
    garantir_configuracao()
    try:
        import pybliometrics
        pybliometrics.scopus.init()
    except: pass

# ================= 2. DICIONÁRIOS E REGRAS DA UEM =================
#VALID_ASJC_CODES = set()
#ranges_pontuaveis = [
#    (1500, 1600), (1600, 1700), (2500, 2600), (2300, 2400),
#    (1700, 1800), (3100, 3200), (2000, 2100), (1100, 1200),
#    (1300, 1400), (3000, 3100), (2100, 2200)
#]

#for start, end in ranges_pontuaveis: VALID_ASJC_CODES.update(range(start, end))
#extras_pontuaveis = [2200, 2208, 1803, 2613, 2614]
#for code in extras_pontuaveis: VALID_ASJC_CODES.add(code)

# --- WHITELIST ATUALIZADA (TABELA 2 QS - EDITAL PEQ/UEM) ---
VALID_ASJC_CODES = set()

ASJC_MAP = {
    1000: "Multidisciplinary", 1100: "General Agricultural and Biological Sciences",
    1101: "Agricultural and Biological Sciences (miscellaneous)", 1102: "Agronomy and Crop Science",
    1103: "Animal Science and Zoology", 1104: "Aquatic Science",
    1105: "Ecology, Evolution, Behavior and Systematics", 1106: "Food Science",
    1107: "Forestry", 1108: "Horticulture", 1109: "Insect Science",
    1110: "Plant Science", 1111: "Soil Science", 1200: "General Arts and Humanities",
    1201: "Arts and Humanities (miscellaneous)", 1202: "History",
    1203: "Language and Linguistics", 1204: "Archeology (arts and humanities)",
    1205: "Classics", 1206: "Conservation", 1207: "History and Philosophy of Science",
    1208: "Literature and Literary Theory", 1209: "Museology", 1210: "Music",
    1211: "Philosophy", 1212: "Religious Studies", 1213: "Visual Arts and Performing Arts",
    1300: "General Biochemistry, Genetics and Molecular Biology",
    1301: "Biochemistry, Genetics and Molecular Biology (miscellaneous)",
    1302: "Aging", 1303: "Biochemistry", 1304: "Biophysics", 1305: "Biotechnology",
    1306: "Cancer Research", 1307: "Cell Biology", 1308: "Clinical Biochemistry",
    1309: "Developmental Biology", 1310: "Endocrinology", 1311: "Genetics",
    1312: "Molecular Biology", 1313: "Molecular Medicine", 1314: "Physiology",
    1315: "Structural Biology", 1400: "General Business, Management and Accounting",
    1401: "Business, Management and Accounting (miscellaneous)", 1402: "Accounting",
    1403: "Business and International Management", 1404: "Management Information Systems",
    1405: "Management of Technology and Innovation", 1406: "Marketing",
    1407: "Organizational Behavior and Human Resource Management",
    1408: "Strategy and Management", 1409: "Tourism, Leisure and Hospitality Management",
    1410: "Industrial Relations", 1500: "General Chemical Engineering",
    1501: "Chemical Engineering (miscellaneous)", 1502: "Bioengineering",
    1503: "Catalysis", 1504: "Chemical Health and Safety",
    1505: "Colloid and Surface Chemistry", 1506: "Filtration and Separation",
    1507: "Fluid Flow and Transfer Processes", 1508: "Process Chemistry and Technology",
    1600: "General Chemistry", 1601: "Chemistry (miscellaneous)",
    1602: "Analytical Chemistry", 1603: "Electrochemistry", 1604: "Inorganic Chemistry",
    1605: "Organic Chemistry", 1606: "Physical and Theoretical Chemistry",
    1607: "Spectroscopy", 1700: "General Computer Science",
    1701: "Computer Science (miscellaneous)", 1702: "Artificial Intelligence",
    1703: "Computational Theory and Mathematics",
    1704: "Computer Graphics and Computer-Aided Design",
    1705: "Computer Networks and Communications", 1706: "Computer Science Applications",
    1707: "Computer Vision and Pattern Recognition", 1708: "Hardware and Architecture",
    1709: "Human-Computer Interaction", 1710: "Information Systems",
    1711: "Signal Processing", 1712: "Software", 1800: "General Decision Sciences",
    1801: "Decision Sciences (miscellaneous)", 1802: "Information Systems and Management",
    1803: "Management Science and Operations Research",
    1804: "Statistics, Probability and Uncertainty", 1900: "General Earth and Planetary Sciences",
    1901: "Earth and Planetary Sciences (miscellaneous)", 1902: "Atmospheric Science",
    1903: "Computers in Earth Sciences", 1904: "Earth-Surface Processes",
    1905: "Economic Geology", 1906: "Geochemistry and Petrology", 1907: "Geology",
    1908: "Geophysics", 1909: "Geotechnical Engineering and Engineering Geology",
    1910: "Oceanography", 1911: "Paleontology", 1912: "Space and Planetary Science",
    1913: "Stratigraphy", 2000: "General Economics, Econometrics and Finance",
    2001: "Economics, Econometrics and Finance (miscellaneous)",
    2002: "Economics and Econometrics", 2003: "Finance", 2100: "General Energy",
    2101: "Energy (miscellaneous)", 2102: "Energy Engineering and Power Technology",
    2103: "Fuel Technology", 2104: "Nuclear Energy and Engineering",
    2105: "Renewable Energy, Sustainability and the Environment",
    2200: "General Engineering", 2201: "Engineering (miscellaneous)",
    2202: "Aerospace Engineering", 2203: "Automotive Engineering",
    2204: "Biomedical Engineering", 2205: "Civil and Structural Engineering",
    2206: "Computational Mechanics", 2207: "Control and Systems Engineering",
    2208: "Electrical and Electronic Engineering",
    2209: "Industrial and Manufacturing Engineering", 2210: "Mechanical Engineering",
    2211: "Mechanics of Materials", 2212: "Ocean Engineering",
    2213: "Safety, Risk, Reliability and Quality", 2214: "Media Technology",
    2215: "Building and Construction", 2216: "Architecture",
    2300: "General Environmental Science", 2301: "Environmental Science (miscellaneous)",
    2302: "Ecological Modeling", 2303: "Ecology", 2304: "Environmental Chemistry",
    2305: "Environmental Engineering", 2306: "Global and Planetary Change",
    2307: "Health, Toxicology and Mutagenesis",
    2308: "Management, Monitoring, Policy and Law",
    2309: "Nature and Landscape Conservation", 2310: "Pollution",
    2311: "Waste Management and Disposal", 2312: "Water Science and Technology",
    2400: "General Immunology and Microbiology",
    2401: "Immunology and Microbiology (miscellaneous)",
    2402: "Applied Microbiology and Biotechnology", 2403: "Immunology",
    2404: "Microbiology", 2405: "Parasitology", 2406: "Virology",
    2500: "General Materials Science", 2501: "Materials Science (miscellaneous)",
    2502: "Biomaterials", 2503: "Ceramics and Composites",
    2504: "Electronic, Optical and Magnetic Materials", 2505: "Materials Chemistry",
    2506: "Metals and Alloys", 2507: "Polymers and Plastics",
    2508: "Surfaces, Coatings and Films", 2600: "General Mathematics",
    2601: "Mathematics (miscellaneous)", 2602: "Algebra and Number Theory",
    2603: "Analysis", 2604: "Applied Mathematics", 2605: "Computational Mathematics",
    2606: "Control and Optimization", 2607: "Discrete Mathematics and Combinatorics",
    2608: "Geometry and Topology", 2609: "Logic", 2610: "Mathematical Physics",
    2611: "Modeling and Simulation", 2612: "Numerical Analysis",
    2613: "Statistics and Probability", 2614: "Theoretical Computer Science",
    2700: "General Medicine", 2701: "Medicine (miscellaneous)", 2702: "Anatomy",
    2703: "Anesthesiology and Pain Medicine", 2704: "Biochemistry (medical)",
    2705: "Cardiology and Cardiovascular Medicine",
    2706: "Critical Care and Intensive Care Medicine",
    2707: "Complementary and Alternative Medicine", 2708: "Dermatology",
    2709: "Drug Guides", 2710: "Embryology", 2711: "Emergency Medicine",
    2712: "Endocrinology, Diabetes and Metabolism", 2713: "Epidemiology",
    2714: "Family Practice", 2715: "Gastroenterology", 2716: "Genetics (clinical)",
    2717: "Geriatrics and Gerontology", 2718: "Health Informatics",
    2719: "Health Policy", 2720: "Hematology", 2721: "Hepatology",
    2722: "Histology", 2723: "Immunology and Allergy", 2724: "Internal Medicine",
    2725: "Infectious Diseases", 2726: "Microbiology (medical)", 2727: "Nephrology",
    2728: "Neurology (clinical)", 2729: "Obstetrics and Gynecology", 2730: "Oncology",
    2731: "Ophthalmology", 2732: "Orthopedics and Sports Medicine",
    2733: "Otorhinolaryngology", 2734: "Pathology and Forensic Medicine",
    2735: "Pediatrics, Perinatology and Child Health", 2736: "Pharmacology (medical)",
    2737: "Physiology (medical)", 2738: "Psychiatry and Mental Health",
    2739: "Public Health, Environmental and Occupational Health",
    2740: "Pulmonary and Respiratory Medicine",
    2741: "Radiology, Nuclear Medicine and Imaging", 2742: "Rehabilitation",
    2743: "Reproductive Medicine", 2744: "Reviews and References (medical)",
    2745: "Rheumatology", 2746: "Surgery", 2747: "Transplantation", 2748: "Urology",
    2800: "General Neuroscience", 2801: "Neuroscience (miscellaneous)",
    2802: "Behavioral Neuroscience", 2803: "Biological Psychiatry",
    2804: "Cellular and Molecular Neuroscience", 2805: "Cognitive Neuroscience",
    2806: "Developmental Neuroscience", 2807: "Endocrine and Autonomic Systems",
    2808: "Neurology", 2809: "Sensory Systems", 2900: "General Nursing",
    2901: "Nursing (miscellaneous)", 2902: "Advanced and Specialized Nursing",
    2903: "Assessment and Diagnosis", 2904: "Care Planning",
    2905: "Community and Home Care", 2906: "Critical Care Nursing",
    2907: "Emergency Nursing", 2908: "Fundamentals and Skills",
    2909: "Gerontology", 2910: "Issues, Ethics and Legal Aspects",
    2911: "Leadership and Management", 2912: "LPN and LVN",
    2913: "Maternity and Midwifery", 2914: "Medical and Surgical Nursing",
    2915: "Nurse Assisting", 2916: "Nutrition and Dietetics",
    2917: "Oncology (nursing)", 2918: "Pathophysiology", 2919: "Pediatrics",
    2920: "Pharmacology (nursing)", 2921: "Psychiatric Mental Health",
    2922: "Research and Theory", 2923: "Review and Exam Preparation",
    3000: "General Pharmacology, Toxicology and Pharmaceutics",
    3001: "Pharmacology, Toxicology and Pharmaceutics (miscellaneous)",
    3002: "Drug Discovery", 3003: "Pharmaceutical Science", 3004: "Pharmacology",
    3005: "Toxicology", 3100: "General Physics and Astronomy",
    3101: "Physics and Astronomy (miscellaneous)", 3102: "Acoustics and Ultrasonics",
    3103: "Astronomy and Astrophysics", 3104: "Condensed Matter Physics",
    3105: "Instrumentation", 3106: "Nuclear and High Energy Physics",
    3107: "Atomic and Molecular Physics, and Optics", 3108: "Radiation",
    3109: "Statistical and Nonlinear Physics", 3110: "Surfaces and Interfaces",
    3200: "General Psychology", 3201: "Psychology (miscellaneous)",
    3202: "Applied Psychology", 3203: "Clinical Psychology",
    3204: "Developmental and Educational Psychology",
    3205: "Experimental and Cognitive Psychology",
    3206: "Neuropsychology and Physiological Psychology", 3207: "Social Psychology",
    3300: "General Social Sciences", 3301: "Social Sciences (miscellaneous)",
    3302: "Archeology", 3303: "Development", 3304: "Education",
    3305: "Geography, Planning and Development", 3306: "Health (social science)",
    3307: "Human Factors and Ergonomics", 3308: "Law",
    3309: "Library and Information Sciences", 3310: "Linguistics and Language",
    3311: "Safety Research", 3312: "Sociology and Political Science",
    3313: "Transportation", 3314: "Anthropology", 3315: "Communication",
    3316: "Cultural Studies", 3317: "Demography", 3318: "Gender Studies",
    3319: "Life-span and Life-course Studies",
    3320: "Political Science and International Relations",
    3321: "Public Administration", 3322: "Urban Studies", 3400: "General Veterinary",
    3401: "Veterinary (miscellaneous)", 3402: "Equine", 3403: "Food Animals",
    3404: "Small Animals", 3500: "General Dentistry",
    3501: "Dentistry (miscellaneous)", 3502: "Dental Assisting",
    3503: "Dental Hygiene", 3504: "Oral Surgery", 3505: "Orthodontics",
    3506: "Periodontics", 3600: "General Health Professions",
    3601: "Health Professions (miscellaneous)", 3602: "Chiropractics",
    3603: "Complementary and Manual Therapy", 3604: "Emergency Medical Services",
    3605: "Health Information Management", 3606: "Medical Assisting and Transcription",
    3607: "Medical Laboratory Technology", 3608: "Medical Terminology",
    3609: "Occupational Therapy", 3610: "Optometry", 3611: "Pharmacy",
    3612: "Physical Therapy, Sports Therapy and Rehabilitation", 3613: "Podiatry",
    3614: "Radiological and Ultrasound Technology", 3615: "Respiratory Care",
    3616: "Speech and Hearing"
}

def get_specific_name(code): return ASJC_MAP.get(code, f"Sub-área {code}")

""" 
def get_categoria_principal(code):
    c = int(code)
    if 1500 <= c < 1600: return "Chemical Engineering"
    if 1600 <= c < 1700: return "Chemistry"
    if 2100 <= c < 2200: return "Energy"
    if 2200 <= c < 2300: return "Engineering"
    if 2300 <= c < 2400: return "Environmental Science"
    if 2500 <= c < 2600: return "Materials Science"
    if 1700 <= c < 1800: return "Computer Science"
    if 3100 <= c < 3200: return "Physics and Astronomy"
    if 1100 <= c < 1200: return "Agricultural & Bio Sciences"
    if 1300 <= c < 1400: return "Biochemistry, Genetics & Mol. Bio"
    if 3000 <= c < 3100: return "Pharmacology, Toxicology"
    if 2000 <= c < 2100: return "Economics, Econometrics"
    if c == 1803: return "Management/Operations"
    if c in [2613, 2614]: return "Math/Statistics"
    return "Outra Área Pontuável"
"""

# =========================================================================
# DICIONÁRIO OFICIAL EXTRAÍDO DIRETAMENTE DA METODOLOGIA QS (asjc.csv)
# Contém apenas os mapeamentos válidos para as áreas da Tabela 2 do Edital
# =========================================================================
ASJC_TO_QS_EDITAL = {
    1100: 'Agriculture and Forestry', 1101: 'Agriculture and Forestry', 1102: 'Agriculture and Forestry',
    1103: 'Agriculture and Forestry', 1104: 'Agriculture and Forestry', 1105: 'Agriculture and Forestry',
    1106: 'Agriculture and Forestry', 1107: 'Agriculture and Forestry', 1108: 'Agriculture and Forestry',
    1109: 'Agriculture and Forestry', 1110: 'Agriculture and Forestry', 1111: 'Agriculture and Forestry',
    1300: 'Biological Sciences', 1301: 'Biological Sciences', 1302: 'Biological Sciences',
    1303: 'Biological Sciences', 1304: 'Biological Sciences', 1305: 'Biological Sciences',
    1306: 'Biological Sciences', 1307: 'Biological Sciences', 1308: 'Biological Sciences',
    1309: 'Biological Sciences', 1310: 'Biological Sciences', 1311: 'Biological Sciences',
    1312: 'Biological Sciences', 1315: 'Biological Sciences', 1500: 'Engineering - Chemical',
    1501: 'Engineering - Chemical', 1502: 'Engineering - Chemical', 
    1503: 'Engineering - Chemical / Petroleum Engineering',
    1504: 'Engineering - Chemical / Petroleum Engineering', 1505: 'Engineering - Chemical',
    1506: 'Engineering - Chemical / Petroleum Engineering',
    1507: 'Engineering - Chemical / Petroleum Engineering',
    1508: 'Engineering - Chemical / Petroleum Engineering',
    1600: 'Chemistry', 1601: 'Chemistry', 1602: 'Chemistry', 1603: 'Chemistry',
    1604: 'Chemistry', 1605: 'Chemistry / Petroleum Engineering',
    1606: 'Chemistry / Petroleum Engineering', 1607: 'Chemistry',
    1700: 'Computer Science', 1701: 'Computer Science', 
    1702: 'Artificial Intelligence / Computer Science',
    1703: 'Computer Science', 1704: 'Computer Science', 1705: 'Computer Science',
    1706: 'Computer Science', 1707: 'Computer Science', 1708: 'Computer Science',
    1709: 'Computer Science', 1710: 'Computer Science', 1711: 'Computer Science',
    1712: 'Computer Science', 1802: 'Computer Science', 
    1803: 'Statistics and Operational Research', 1804: 'Statistics and Operational Research',
    1900: 'Petroleum Engineering', 1901: 'Petroleum Engineering', 1905: 'Petroleum Engineering',
    1906: 'Petroleum Engineering', 1909: 'Petroleum Engineering', 
    2000: 'Economics and Econometrics', 2001: 'Economics and Econometrics', 2002: 'Economics and Econometrics',
    2100: 'Engineering - Electrical and Electronic / Petroleum Engineering',
    2101: 'Engineering - Electrical and Electronic / Petroleum Engineering',
    2102: 'Engineering - Electrical and Electronic / Petroleum Engineering',
    2103: 'Engineering - Electrical and Electronic / Petroleum Engineering',
    2104: 'Engineering - Electrical and Electronic', 2105: 'Engineering - Electrical and Electronic',
    2200: 'Engineering - General', 2201: 'Engineering - General', 2204: 'Biological Sciences',
    2207: 'Computer Science', 2208: 'Engineering - Electrical and Electronic / Petroleum Engineering',
    2211: 'Materials Science', 2212: 'Petroleum Engineering', 
    2213: 'Engineering - General / Petroleum Engineering',
    2300: 'Environmental Sciences', 2301: 'Environmental Sciences', 2302: 'Environmental Sciences',
    2303: 'Environmental Sciences', 2304: 'Environmental Sciences / Petroleum Engineering',
    2305: 'Environmental Sciences', 2306: 'Environmental Sciences', 2307: 'Environmental Sciences',
    2308: 'Environmental Sciences', 2309: 'Environmental Sciences', 2310: 'Environmental Sciences',
    2311: 'Environmental Sciences', 2312: 'Environmental Sciences', 
    2400: 'Biological Sciences', 2401: 'Biological Sciences', 2402: 'Biological Sciences',
    2403: 'Biological Sciences', 2404: 'Biological Sciences', 2405: 'Biological Sciences',
    2406: 'Biological Sciences', 2500: 'Materials Science', 2501: 'Materials Science',
    2502: 'Materials Science', 2503: 'Materials Science', 2504: 'Materials Science',
    2505: 'Materials Science', 2506: 'Materials Science', 2507: 'Materials Science',
    2508: 'Materials Science', 2610: 'Physics and Astronomy', 
    2613: 'Statistics and Operational Research', 2614: 'Computer Science',
    2736: 'Pharmacy and Pharmacology', 3000: 'Pharmacy and Pharmacology', 
    3001: 'Pharmacy and Pharmacology', 3002: 'Pharmacy and Pharmacology',
    3003: 'Pharmacy and Pharmacology', 3004: 'Pharmacy and Pharmacology',
    3005: 'Pharmacy and Pharmacology', 3100: 'Physics and Astronomy', 
    3101: 'Physics and Astronomy', 3102: 'Physics and Astronomy', 3103: 'Physics and Astronomy',
    3104: 'Physics and Astronomy', 3105: 'Physics and Astronomy', 3106: 'Physics and Astronomy',
    3107: 'Physics and Astronomy', 3108: 'Physics and Astronomy', 3109: 'Physics and Astronomy',
    3110: 'Physics and Astronomy', 3611: 'Pharmacy and Pharmacology'
}

# O robô agora usa automaticamente as chaves do dicionário oficial perfeito como Lista VIP
VALID_ASJC_CODES = set(ASJC_TO_QS_EDITAL.keys())

def get_categoria_principal(code):
    c = int(code)
    # Consulta diretamente a fonte da verdade. Sem "chutes" ou ranges.
    return ASJC_TO_QS_EDITAL.get(c, "Outra Área (Não listada na Tabela 2)")

def get_enquadramento_logico(code):
    c = int(code)
    
    # 1. Extrai o nome exato da sub-área (daquela sua lista gigantesca ASJC_MAP)
    nome_especifico = ASJC_MAP.get(c, f"Sub-área {c}")
    
    # 2. Extrai a categoria do Edital usando a sua lógica de ranges
    nome_edital = get_categoria_principal(c)
    
    # 3. Monta a string explicativa
    if nome_edital == "Outra Área (Tabela 2)":
        return f"{nome_especifico} (Não enquadrada no Edital)"
        
    return f"📄 {nome_especifico} que pertence a {nome_edital}"

def calcular_estrato(p):
    if p >= 87.5: return 'A1', 15.0
    elif p >= 75.0: return 'A2', 13.0
    elif p >= 62.5: return 'A3', 11.0
    elif p >= 50.0: return 'A4', 9.0
    elif p >= 37.5: return 'A5', 7.0
    elif p >= 25.0: return 'A6', 6.0
    elif p >= 12.5: return 'A7', 5.0
    else: return 'A8', 4.0

def extrair_issn_limpo(objeto_issn):
    valor = None
    if hasattr(objeto_issn, 'print') and objeto_issn.print: valor = objeto_issn.print
    elif hasattr(objeto_issn, 'electronic') and objeto_issn.electronic: valor = objeto_issn.electronic
    elif hasattr(objeto_issn, 'value'): valor = objeto_issn.value
    else: valor = str(objeto_issn)
    return str(valor).replace('-', '').replace(' ', '').strip() if valor else None

def obter_link_revista_scopus(ab):
    """Gera o link direto para a página de métricas da revista na Scopus."""
    if hasattr(ab, 'source_id') and ab.source_id:
        return f"https://www.scopus.com/sourceid/{ab.source_id}"
    else:
        # Tenta pelo ISSN se não tiver o source_id
        issn_limpo = extrair_issn_limpo(ab.issn if hasattr(ab, 'issn') else None)
        if issn_limpo:
            return f"https://www.scopus.com/sources.uri?issn={issn_limpo}"
        return "https://www.scopus.com/sources.uri"
# ================= 3. MOTORES DE BUSCA SCOPUS E CROSSREF =================
def verificar_doi_externo(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            msg = resp.json()['message']
            autores_crossref = []
            for a in msg.get('author', []):
                family = a.get('family', '')
                given = a.get('given', '')
                if family or given: autores_crossref.append(f"{family}, {given}".strip(', '))
            if not autores_crossref: autores_crossref = ["Autor Desconhecido"]

            return {
                "titulo": msg.get('title', ['Desconhecido'])[0],
                "revista": msg.get('container-title', [''])[0],
                "ano": msg.get('created', {}).get('date-parts', [[2026]])[0][0],
                "issn": msg.get('ISSN', [None])[0],
                "autores": autores_crossref
            }
    except: pass
    return None

def obter_dados_por_revista(identificador):
    try:
        revista = SerialTitle(identificador, view='CITESCORE',refresh=True)
        ranks = revista._entry.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', [])[0]
        rank_list = ranks.get('citeScoreInformationList', [{}])[0].get('citeScoreInfo', [{}])[0].get('citeScoreSubjectRank', [])
        
        candidatos = []
        for r in rank_list:
            c_code = int(r.get('subjectCode'))
            p_perc = float(r.get('percentile'))
            if c_code in VALID_ASJC_CODES:
                estr, pts = calcular_estrato(p_perc)
                candidatos.append({'code': c_code, 'percentile': p_perc, 'estrato': estr, 'pontos': pts})
        
        if not candidatos: return None, None, "Fora das Áreas de Avaliação do Programa"
        melhor = max(candidatos, key=lambda x: x['percentile'])
        return melhor['percentile'], {
            'estrato': melhor['estrato'], 'base': melhor['pontos'],
            'area_principal': get_categoria_principal(melhor['code']),
            'area_detalhe': get_specific_name(melhor['code']), 'area_code': melhor['code']
        }, None
    except Exception as e: 
        erro_msg = str(e)
        if "500" in erro_msg or "Cache Service" in erro_msg or "GENERAL_SYSTEM" in erro_msg:
            return None, None, "API_METRICAS_DOWN"
        return None, None, f"Erro interno: {erro_msg}"

def obter_dados_revista(issn_code):
    try:
        issn_clean = extrair_issn_limpo(issn_code)
        # refresh=True obriga a buscar o dado mais fresco que a API tiver hoje
        revista = SerialTitleISSN(issn_clean, view='CITESCORE', refresh=True)
        historico = revista.citescoreyearinfolist
        if not historico: return None, None, "Sem histórico"
        
        # Ordena do maior ano para o menor (garante que o topo da lista é o mais recente)
        historico_ordenado = sorted(historico, key=lambda x: int(x.year), reverse=True)
        metrica_escolhida, ranks_encontrados = None, []
        
        for m in historico_ordenado:
            import datetime
        ano_atual = datetime.datetime.now().year # Descobre que estamos em 2026
        
        # Ordena do maior ano para o menor
        historico_ordenado = sorted(historico, key=lambda x: int(x.year), reverse=True)
        metrica_escolhida, ranks_encontrados = None, []
        
        for m in historico_ordenado:
            # --- NOVA TRAVA: Ignora o CiteScore Tracker (ano em curso) ---
            if int(m.year) >= ano_atual:
                continue 
            # -------------------------------------------------------------
            
            raw_metrics = revista._entry.get('citeScoreYearInfoList', {}).get('citeScoreYearInfo', [])
            if isinstance(raw_metrics, dict): raw_metrics = [raw_metrics]
            raw_year_data = next((x for x in raw_metrics if str(x.get('@year')) == str(m.year)), None)
            if not raw_year_data: continue
            
            level_1 = raw_year_data.get('citeScoreInformationList')
            if isinstance(level_1, list) and len(level_1) > 0: level_1 = level_1[0]
            level_2 = level_1.get('citeScoreInfo') if isinstance(level_1, dict) else None
            if isinstance(level_2, list) and len(level_2) > 0: level_2 = level_2[0]
            ranks = level_2.get('citeScoreSubjectRank') if isinstance(level_2, dict) else None
            
            if isinstance(ranks, dict): ranks = [ranks]
            if ranks:
                # O SEGREDO ESTÁ AQUI: Pegar o primeiro (mais recente) que tenha dados e PARAR.
                metrica_escolhida = m
                ranks_encontrados = ranks
                break 
                
        if not metrica_escolhida: return None, None, "Sem ranking de áreas"
        
        candidatos = []
        for r in ranks_encontrados:
            raw_code = r.get('subjectCode') or r.get('code') or r.get('@subjectCode')
            raw_perc = r.get('percentile') or r.get('@percentile')
            if raw_code and raw_perc:
                try:
                    c_int = int(raw_code); p_float = float(raw_perc)
                    if c_int in VALID_ASJC_CODES:
                        estr, pts = calcular_estrato(p_float)
                        candidatos.append({'code':c_int, 'name':get_specific_name(c_int), 'percentile':p_float, 'estrato':estr, 'pontos':pts})
                except: continue
                
        if not candidatos: return None, None, "Fora das Áreas de Avaliação do Programa"
        
        melhor = max(candidatos, key=lambda x: x['percentile'])
        return melhor['percentile'], {
            'estrato': melhor['estrato'], 'base': melhor['pontos'], 
            'ano_metrica': metrica_escolhida.year,  # <-- CAPTURAMOS O ANO REAL DA API AQUI
            'area_principal': get_categoria_principal(melhor['code']), 
            'area_detalhe': melhor['name'], 'area_code': melhor['code']
        }, None
    except Exception as e: return None, None, f"Erro interno: {str(e)}"

def calcular_nota_fracionada(pontos_base, n_autores):
    """Calculadora Oficial da UEM para divisão por autores"""
    try: n = int(n_autores)
    except: n = 1
    if n < 1: n = 1
    fator = 1.0 if n <= 4 else (4.0 / n)
    return pontos_base * fator

# ================= 4. A CAIXA PRETA PRINCIPAL =================
# ================= 4. A CAIXA PRETA PRINCIPAL =================
def avaliar_artigo_scopus(doi, ano_ini=2021, ano_fim=2026):
    """
    Função principal que a comissão.py vai chamar.
    """
    try:
        obs_artigo = ""
        link_direto = "https://www.scopus.com/sources.uri"
        
        try:
            artigo = AbstractRetrieval(doi, view='FULL')
            nome_revista = artigo.publicationName
            titulo_artigo = artigo.title
            ano_str = str(artigo.coverDate[:4])
            
            # Pega o link antes da API da Elsevier dar piti
            link_direto = obter_link_revista_scopus(artigo)
            
            if not (ano_ini <= int(ano_str) <= ano_fim): 
                return {"sucesso": False, "erro": f"Ano {ano_str} fora do período ({ano_ini}-{ano_fim})"}
            
            issn_obj = artigo.issn if artigo.issn else artigo.eIssn
            issn_str = extrair_issn_limpo(issn_obj)
            if not issn_str: raise Exception("Revista sem ISSN registrado")
            
            # Salva os autores (se a Scopus cair na revista, a gente já garantiu os nomes!)
            autores = [f"{a.surname}, {a.given_name}" for a in artigo.authors] if artigo.authors else ["Desconhecido"]
            
            percentil, dados_nota, erro = obter_dados_revista(issn_str)
            if erro: raise Exception(erro)
            
        except Exception as e_scopus:
            erro_scopus_str = str(e_scopus)
            if "fora do período" in erro_scopus_str: 
                return {"sucesso": False, "erro": erro_scopus_str}
            
            # A ROTA DE FUGA: Elsevier Caiu!
            if erro_scopus_str == "API_METRICAS_DOWN":
                string_autores = "; ".join(autores)
                return {
                    "sucesso": False,
                    "erro": "API_METRICAS_DOWN",
                    "revista": nome_revista,
                    "titulo_artigo": titulo_artigo,
                    "ano": int(ano_str),
                    "n_autores": len(autores),
                    "lista_autores": autores,
                    "autores": string_autores,
                    "link_revista": link_direto
                }
            
            # PLANO B (Crossref + SerialTitle Direto)
            info = verificar_doi_externo(doi)
            if not info: return {"sucesso": False, "erro": f"Não encontrado via Scopus ou Crossref. ({erro_scopus_str})"}
            
            if not (ano_ini <= int(info['ano']) <= ano_fim):
                return {"sucesso": False, "erro": f"Ano {info['ano']} (via Crossref) fora do período."}
            
            nome_revista, titulo_artigo, ano_str = info['revista'], info['titulo'], str(info['ano'])
            autores = info['autores']
            obs_artigo = "Não indexado diretamente na Scopus. Avaliado via Crossref/SerialTitle."
            link_direto = f"https://www.scopus.com/sources.uri?issn={info['issn']}" if info['issn'] else "https://www.scopus.com/sources.uri"
            
            percentil, dados_nota, err = obter_dados_por_revista(info['issn'] if info['issn'] else info['revista'])
            
            # Rota de fuga no Plano B
            if err == "API_METRICAS_DOWN":
                string_autores = "; ".join(autores)
                return {
                    "sucesso": False,
                    "erro": "API_METRICAS_DOWN",
                    "revista": nome_revista,
                    "titulo_artigo": titulo_artigo,
                    "ano": int(ano_str),
                    "n_autores": len(autores),
                    "lista_autores": autores,
                    "autores": string_autores,
                    "link_revista": link_direto
                }
            elif err: 
                return {"sucesso": False, "erro": f"Revista não pontuável/encontrada. ({err})"}

        # Conta final de Autores
        n_autores = len(autores)
        fator = 1.0 if n_autores <= 4 else (4.0 / n_autores)
        nota_final = calcular_nota_fracionada(dados_nota['base'], n_autores)
        string_autores = "; ".join(autores)

        return {
            "sucesso": True,
            "revista": nome_revista,
            "titulo": titulo_artigo,
            "titulo_artigo": titulo_artigo,
            "ano": int(ano_str),
            "ano_metrica": dados_nota['ano_metrica'],
            "estrato": dados_nota['estrato'],
            "percentil": percentil,
            "area_principal": dados_nota['area_principal'],
            "area_detalhe": dados_nota['area_detalhe'],
            "n_autores": n_autores,
            "lista_autores": autores,
            "autores": string_autores,
            "fator_divisao": fator,
            "nota_final_calculada": nota_final,
            "obs": obs_artigo,
            "link_revista": link_direto  # <--- A PEÇA QUE FALTAVA!
        }
        
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro crítico na varredura: {str(e)}"}
