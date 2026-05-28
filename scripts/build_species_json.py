"""
Pipeline xlsx -> species.json para o site Brazilian Tadpoles 5.0.

Le data-raw/Brazilian tadpoles database 4.1.0.xlsx e gera assets/data/species.json
com o esquema expandido (ext_morph, internal_oral, chondrocranium).

Aplica a regra de exclusao de familias do clade Brachycephaloidea
(Brachycephalidae, Caligophrynidae, Ceuthomantidae, Craugastoridae,
Eleutherodactylidae, Neblinaphrynidae) + Hemiphractidae, porque essas spp.
nao tem girino livre-natante.

Uso (a partir da raiz do projeto):
    python3 scripts/build_species_json.py
"""
import json
import openpyxl
import os
import re
import unicodedata
from datetime import date

EXCLUDE_FAMILIES = {
    'Brachycephalidae', 'Caligophrynidae', 'Ceuthomantidae',
    'Craugastoridae', 'Eleutherodactylidae', 'Neblinaphrynidae',
    'Hemiphractidae',
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
XLSX_PATH = os.path.join(PROJECT_ROOT, 'data-raw', 'Brazilian tadpoles database 4.1.0.xlsx')
JSON_PATH = os.path.join(PROJECT_ROOT, 'assets', 'data', 'species.json')


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()


def parse_refs(cell):
    """Retorna (status, refs[]). status in {described, not_described}.
    Divide em '/' que o banco usa como separador de multiplas refs."""
    if cell is None:
        return ('not_described', [])
    text = str(cell).strip()
    if not text or text.lower().startswith('not_described'):
        return ('not_described', [])
    refs = [r.strip() for r in text.split('/') if r.strip()]
    return ('described', refs)


def main():
    wb = openpyxl.load_workbook(XLSX_PATH, read_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    expected = ('SPECIES', 'Family', 'External Morphology',
                'Internal Oral Features', 'Chondrocranium')
    assert header[:5] == expected, f'Cabecalhos inesperados: {header}'

    species = []
    excluded = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        sp_name = str(r[0]).strip()
        family = str(r[1]).strip() if r[1] else ''
        if family in EXCLUDE_FAMILIES:
            excluded.append((sp_name, family))
            continue
        genus = sp_name.split()[0] if sp_name else ''
        ext_status, ext_refs = parse_refs(r[2])
        int_status, int_refs = parse_refs(r[3])
        cho_status, cho_refs = parse_refs(r[4])
        species.append({
            'id': slug(sp_name),
            'species': sp_name,
            'genus': genus,
            'family': family,
            'ext_morph': {'status': ext_status, 'refs': ext_refs},
            'internal_oral': {'status': int_status, 'refs': int_refs},
            'chondrocranium': {'status': cho_status, 'refs': cho_refs},
        })

    species.sort(key=lambda s: (s['family'], s['species']))

    out = {
        'schema_version': '5.0.0',
        'source': 'Brazilian tadpoles database v4.1.0 (Google Sheet, 27 mai 2026)',
        'generated': date.today().isoformat(),
        'excluded_families': sorted(EXCLUDE_FAMILIES),
        'excluded_count': len(excluded),
        'count': len(species),
        'characters': ['ext_morph', 'internal_oral', 'chondrocranium'],
        'species': species,
    }

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f'Geradas {len(species)} especies em {JSON_PATH}')
    print(f'Excluidas {len(excluded)} spp das familias sem girino livre-natante')
    from collections import Counter
    fam_counts = Counter(s['family'] for s in species)
    print(f'\nFamilias ({len(fam_counts)}):')
    for fam, n in sorted(fam_counts.items()):
        print(f'  {fam}: {n}')
    print('\nCompletude por caracter:')
    for c in ('ext_morph', 'internal_oral', 'chondrocranium'):
        d = sum(1 for s in species if s[c]['status'] == 'described')
        print(f'  {c}: {d}/{len(species)} = {round(d/len(species)*100)}%')


if __name__ == '__main__':
    main()
