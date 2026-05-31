"""
DEPRECATED desde 31 mai 2026 — mantido apenas para reprodutibilidade
histórica.

A fonte canônica do banco passou a ser `assets/data/species.json`
diretamente (mantido via GitHub Issues/PRs, ver `.github/ISSUE_TEMPLATE/`).
O Google Sheet foi privatizado e o xlsx em `data-raw/` é um snapshot
congelado do estado em 27 mai 2026. NÃO regere o species.json a partir
deste script — você perderia todas as contribuições feitas via PR.

Pipeline original (preservado por histórico):
  Le data-raw/Brazilian tadpoles database 4.1.0.xlsx e gera
  assets/data/species.json com o esquema expandido (ext_morph,
  internal_oral, chondrocranium).

  Aplica a regra de exclusao de familias do clade Brachycephaloidea
  (Brachycephalidae, Caligophrynidae, Ceuthomantidae, Craugastoridae,
  Eleutherodactylidae, Neblinaphrynidae) + Hemiphractidae, porque essas
  spp. nao tem girino livre-natante.

Caso ABSOLUTAMENTE precise re-rodar (e perder contribuições):
    python3 scripts/build_species_json.py --force
"""
import sys
if '--force' not in sys.argv:
    print('=' * 70)
    print('DEPRECATED: este script não deve mais ser executado.')
    print('A fonte canônica agora é assets/data/species.json (mantido via PRs).')
    print('Re-rodar perderia todas as contribuições feitas via GitHub Issues.')
    print('Se você TEM CERTEZA, use --force.')
    print('=' * 70)
    sys.exit(1)

import json
import openpyxl
import os
import re
import sys
import unicodedata
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_refs import parse_cell  # noqa: E402

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
    """Retorna (status, refs[]) onde cada ref é
    {author, year, title, journal, doi, raw}.

    Status in {described, not_described}. O split é feito por
    `parse_refs.split_cell`, que reconhece '/' como separador entre
    citações sem quebrar DOIs (`https://doi.org/10.NNNN/...`).
    """
    if cell is None:
        return ('not_described', [])
    text = str(cell).strip()
    if not text or text.lower().startswith('not_described'):
        return ('not_described', [])
    refs = parse_cell(cell)
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
        parts = sp_name.split()
        genus = parts[0] if parts else ''
        epithet = parts[1] if len(parts) >= 2 else ''
        tip_label = f'{genus}_{epithet}' if epithet else genus
        ext_status, ext_refs = parse_refs(r[2])
        int_status, int_refs = parse_refs(r[3])
        cho_status, cho_refs = parse_refs(r[4])
        species.append({
            'id': slug(sp_name),
            'species': sp_name,
            'genus': genus,
            'epithet': epithet,
            'tip_label': tip_label,
            'family': family,
            'ext_morph': {'status': ext_status, 'refs': ext_refs},
            'internal_oral': {'status': int_status, 'refs': int_refs},
            'chondrocranium': {'status': cho_status, 'refs': cho_refs},
        })

    species.sort(key=lambda s: (s['family'], s['species']))

    # Deduplica espécies por id (merge refs quando há linhas duplicadas
    # na planilha, ex.: typo corrigido que gerou duas linhas iguais)
    seen = {}
    deduped = []
    dup_count = 0
    for s in species:
        sid = s['id']
        if sid in seen:
            existing = seen[sid]
            dup_count += 1
            for c in ('ext_morph', 'internal_oral', 'chondrocranium'):
                existing_raws = set(r['raw'] for r in existing[c]['refs'])
                for r in s[c]['refs']:
                    if r['raw'] not in existing_raws:
                        existing[c]['refs'].append(r)
                if s[c]['status'] == 'described':
                    existing[c]['status'] = 'described'
        else:
            seen[sid] = s
            deduped.append(s)
    if dup_count:
        print(f'Deduplicadas {dup_count} linhas duplicadas na planilha')
    species = deduped

    out = {
        'schema_version': '5.1.0',
        'source': 'Brazilian tadpoles database v4.1.0 (Google Sheet, 30 mai 2026)',
        'generated': date.today().isoformat(),
        'excluded_families': sorted(EXCLUDE_FAMILIES),
        'excluded_count': len(excluded),
        'count': len(species),
        'characters': ['ext_morph', 'internal_oral', 'chondrocranium'],
        'ref_schema': ['author', 'year', 'title', 'journal', 'doi', 'raw'],
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

    # Estatisticas de parsing de refs
    seen = {}
    for s in species:
        for c in ('ext_morph', 'internal_oral', 'chondrocranium'):
            for r in s[c]['refs']:
                seen[r['raw']] = r
    total = len(seen)
    with_year = sum(1 for r in seen.values() if r['year'] is not None)
    with_doi = sum(1 for r in seen.values() if r['doi'] is not None)
    with_author = sum(1 for r in seen.values() if r['author'] is not None)
    with_title = sum(1 for r in seen.values() if r['title'] is not None)
    with_journal = sum(1 for r in seen.values() if r['journal'] is not None)
    print(f'\nRefs unicas: {total}')
    print(f'  com ano:     {with_year} ({round(100*with_year/total)}%)')
    print(f'  com DOI:     {with_doi} ({round(100*with_doi/total)}%)')
    print(f'  com author:  {with_author} ({round(100*with_author/total)}%)')
    print(f'  com title:   {with_title} ({round(100*with_title/total)}%)')
    print(f'  com journal: {with_journal} ({round(100*with_journal/total)}%)')


if __name__ == '__main__':
    main()
