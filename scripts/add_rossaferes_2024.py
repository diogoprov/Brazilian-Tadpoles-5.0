"""
Injeta a referência Rossa-Feres (Ed.) 2024 "Girinos do Brasil" em `ext_morph`
de todas as espécies tratadas no livro.

- Lê a lista transcrita do sumário em: outputs/rossaferes_2024_species.txt
  (ou o caminho passado como --list). Uma espécie por linha; `#` = comentário.
- Aplica o mapping de nomes que decidimos com o Diogo:
    Allobates olfersioides           -> Dryadobates olfersioides
    Bokermannohyla izechsohni        -> Bokermannohyla izecksohni
    Julianus pinima                  -> Julianus pinimus
    Lysapsus bolivianus              -> Pseudis bolivianus         (ADD se ausente)
    Lysapsus limellum                -> Pseudis limellum
    Sphaenorhynchus pauloalvini      -> Gabohyla pauloalvini
    Leptodactylus flavipictus        -> Leptodactylus flavopictus
    Chiasmocleis carvalhoi           -> Chiasmocleis carvalhoi     (ADD se ausente)
    Scinax cruentomma                -> Scinax cruentomma          (ADD se ausente)
- Adiciona a ref em `ext_morph` da espécie (dedup por DOI/raw).
- Se a espécie não existe no banco E está na lista NEW_SPECIES abaixo,
  cria a espécie nova (schema idêntico ao add_species do issue_to_pr).
- Salva `assets/data/species.json` in-place. Atualiza `generated` e `count`.

Uso (a partir da raiz do repo Brazilian-Tadpoles-5.0):
    python3 scripts/add_rossaferes_2024.py \\
        --list ../"path"/rossaferes_2024_species.txt \\
        [--dry-run]

Sai com código 0 em sucesso, 1 em erro de validação.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date

# ---- Constantes -------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JSON_PATH    = os.path.join(PROJECT_ROOT, 'assets', 'data', 'species.json')

REF = {
    'author':  'Rossa-Feres, D. C. (Ed.)',
    'year':    2024,
    'title':   'Girinos do Brasil',
    'journal': None,
    'doi':     None,
    'raw':     ('Rossa-Feres, D. C. (Ed.). 2024. Girinos do Brasil. '
                'São Paulo: Anolis Books, 828 p. ISBN 978-65-992458-3-1.'),
}

# livro -> nome no banco (ou nome canônico para criar)
RENAMES = {
    'Allobates olfersioides':      'Dryadobates olfersioides',
    'Bokermannohyla izechsohni':   'Bokermannohyla izecksohni',
    'Julianus pinima':             'Julianus pinimus',
    'Lysapsus bolivianus':         'Pseudis bolivianus',
    'Lysapsus limellum':           'Pseudis limellum',
    'Sphaenorhynchus pauloalvini': 'Gabohyla pauloalvini',
    'Leptodactylus flavipictus':   'Leptodactylus flavopictus',
}

# Espécies que precisam ser criadas no banco (não existem e o Diogo confirmou
# que devem entrar). Todas entram já com ext_morph = described (via a ref REF).
NEW_SPECIES = {
    'Pseudis bolivianus':    'Hylidae',
    'Scinax cruentomma':     'Hylidae',
    'Chiasmocleis carvalhoi':'Microhylidae',
}

VALID_FAMILIES = {
    'Allophrynidae', 'Alsodidae', 'Aromobatidae', 'Bufonidae',
    'Centrolenidae', 'Ceratophryidae', 'Cycloramphidae', 'Dendrobatidae',
    'Hylidae', 'Hylodidae', 'Leptodactylidae', 'Microhylidae',
    'Odontophrynidae', 'Phyllomedusidae', 'Pipidae', 'Ranidae',
}


# ---- Helpers ---------------------------------------------------------------
def slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()


def read_book_list(path: str) -> list[str]:
    """Uma espécie por linha; ignora `#` e vazios."""
    out = []
    with open(path, encoding='utf-8') as f:
        for ln in f:
            ln = ln.split('#', 1)[0].strip()
            if ln:
                out.append(ln)
    return out


def ref_is_same(a: dict, b: dict) -> bool:
    """Dedup: mesmo DOI OU mesma raw."""
    if a.get('doi') and b.get('doi') and a['doi'] == b['doi']:
        return True
    if a.get('raw') and b.get('raw') and a['raw'].strip() == b['raw'].strip():
        return True
    return False


def add_ref_to(sp: dict, char: str, ref: dict) -> str:
    """Adiciona ref em sp[char].refs se não existir. Retorna 'added'|'dup'."""
    block = sp.setdefault(char, {'status': 'not_described', 'refs': []})
    block.setdefault('refs', [])
    for r in block['refs']:
        if isinstance(r, dict) and ref_is_same(r, ref):
            return 'dup'
    block['refs'].append(ref)
    if block.get('status') != 'described':
        block['status'] = 'described'
    return 'added'


def build_new_species(name: str, family: str) -> dict:
    """Objeto de espécie nova (schema idêntico ao usado em issue_to_pr.py)."""
    parts = name.split()
    if len(parts) != 2:
        raise ValueError(f'Nome binomial inválido: {name!r}')
    genus, epithet = parts
    if family not in VALID_FAMILIES:
        raise ValueError(f'Família inválida para {name}: {family!r}')
    return {
        'id':        slugify(name),
        'species':   name,
        'genus':     genus,
        'epithet':   epithet,
        'tip_label': f'{genus}_{epithet}',
        'family':    family,
        'ext_morph':     {'status': 'not_described', 'refs': []},
        'internal_oral': {'status': 'not_described', 'refs': []},
        'chondrocranium':{'status': 'not_described', 'refs': []},
    }


def insert_species_ordered(data: dict, new_sp: dict) -> int:
    """Insere new_sp em `data['species']` em ordem (family, species). Retorna
    o índice 1-based da inserção."""
    key = (new_sp['family'], new_sp['species'])
    insert_at = len(data['species'])
    for i, sp in enumerate(data['species']):
        if (sp['family'], sp['species']) > key:
            insert_at = i
            break
    data['species'].insert(insert_at, new_sp)
    return insert_at + 1


# ---- Main ------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', required=True,
                    help='Caminho pro rossaferes_2024_species.txt')
    ap.add_argument('--dry-run', action='store_true',
                    help='Não escreve nada; só reporta o que faria.')
    args = ap.parse_args()

    book = read_book_list(args.list)
    print(f'>> Livro: {len(book)} espécies transcritas do sumário')

    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    print(f'>> Banco: {data["count"]} spp ({data["generated"]}, '
          f'schema {data["schema_version"]})')

    by_name = {s['species']: s for s in data['species']}

    added_ref, dup_ref, mapped, created, unresolved = 0, 0, 0, 0, []
    log_created = []
    log_mapped  = []

    for raw_name in book:
        book_name = raw_name
        canonical = RENAMES.get(book_name, book_name)
        if canonical != book_name:
            log_mapped.append((book_name, canonical))
            mapped += 1

        sp = by_name.get(canonical)

        # espécie ausente — só criamos se estiver na whitelist
        if sp is None:
            if canonical in NEW_SPECIES:
                new_sp = build_new_species(canonical, NEW_SPECIES[canonical])
                # já entra com a ref em ext_morph
                add_ref_to(new_sp, 'ext_morph', REF)
                pos = insert_species_ordered(data, new_sp)
                by_name[canonical] = new_sp
                created += 1
                log_created.append((canonical, NEW_SPECIES[canonical], pos))
                added_ref += 1
                continue
            unresolved.append(book_name)
            continue

        # espécie existente — adiciona ref em ext_morph
        status = add_ref_to(sp, 'ext_morph', REF)
        if status == 'added':
            added_ref += 1
        else:
            dup_ref += 1

    # meta
    data['count'] = len(data['species'])
    data['generated'] = date.today().isoformat()

    # ---- Relatório --------------------------------------------------------
    print()
    print('==================== RELATÓRIO ====================')
    print(f'  Ref adicionada:    {added_ref}')
    print(f'  Ref já existia:    {dup_ref}')
    print(f'  Nomes mapeados:    {mapped}')
    print(f'  Spp novas criadas: {created}')
    print(f'  Não resolvidas:    {len(unresolved)}')
    print(f'  Banco agora:       {data["count"]} spp (era {data["count"] - created})')
    if log_mapped:
        print()
        print('  --- Renomeações aplicadas ---')
        for a, b in log_mapped:
            print(f'    "{a}"  ->  "{b}"')
    if log_created:
        print()
        print('  --- Espécies criadas ---')
        for name, fam, pos in log_created:
            print(f'    {name}  ({fam})  @posição {pos}')
    if unresolved:
        print()
        print('  --- NÃO RESOLVIDAS ---')
        for x in unresolved:
            print(f'    - {x}')
        print()
        print('  ATENÇÃO: as spp acima não estão no banco nem na whitelist')
        print('  NEW_SPECIES. Adicione-as manualmente ou revise o mapping.')
        return 1

    if args.dry_run:
        print()
        print('>> --dry-run: species.json NÃO foi escrito.')
        return 0

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print()
    print(f'>> species.json atualizado (generated={data["generated"]}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
