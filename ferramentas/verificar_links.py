import requests
import re
from bs4 import BeautifulSoup

url = 'https://www.elsevier.com/products/scopus/content'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
resp = requests.get(url, headers=headers, timeout=20)
print('Status:', resp.status_code)

soup = BeautifulSoup(resp.text, 'html.parser')

print('\n--- Links para download (.xlsx, .zip, etc.) ---')
for a in soup.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    if any(ext in href.lower() for ext in ['.xlsx', '.xls', '.zip', 'download', 'source-list', 'citescore']):
        print(f"Texto: '{text}' -> Link: {href}")

print('\n--- Seção 4 (Titles on Scopus) ---')
target = soup.find(id='4-titles-on-scopus') or soup.find(lambda tag: tag.has_attr('id') and 'titles' in tag['id'])
if target:
    print("Found ID:", target.get('id'))
    parent = target.find_parent() or target
    for a in parent.find_all('a', href=True):
        print(f"Texto: '{a.get_text(strip=True)}' -> {a['href']}")
else:
    # search text
    for tag in soup.find_all(['h2', 'h3', 'h4', 'p']):
        if 'title' in tag.get_text().lower() and 'scopus' in tag.get_text().lower():
            print(tag.get_text()[:100])
