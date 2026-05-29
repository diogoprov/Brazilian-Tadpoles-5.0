"""
Poda a megatree (filogenia_jessyca_newNames.tre) pras spp do banco
Brazilian Tadpoles. Saidas:

  assets/data/phylogeny.json   -> arvore podada como JSON aninhado (D3-friendly)
  assets/data/phylogeny_unmatched.json -> lista de spp do banco SEM tip na arvore

A megatree tem ~5300 tips em Newick padrao (formato Genus_epithet).
Implemento um parser minimal de Newick + algoritmo de poda em pos-ordem.

Uso (a partir da raiz do projeto):
    python3 scripts/prune_phylogeny.py
"""
import json
import os
import re
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TREE_PATH = os.path.join(PROJECT_ROOT, 'data-raw', 'filogenia_jessyca_newNames.tre')
SPECIES_PATH = os.path.join(PROJECT_ROOT, 'assets', 'data', 'species.json')
TREE_OUT = os.path.join(PROJECT_ROOT, 'assets', 'data', 'phylogeny.json')
UNMATCHED_OUT = os.path.join(PROJECT_ROOT, 'assets', 'data', 'phylogeny_unmatched.json')


# ----- Newick parser minimal -----
class Node:
    __slots__ = ('name', 'length', 'children',
                 'counts', 'family', 'genus', 'epithet',
                 'family_set', 'genus_set',
                 'mrca_family', 'mrca_genus')
    def __init__(self, name='', length=0.0, children=None):
        self.name = name
        self.length = length
        self.children = children if children is not None else []
        self.counts = {'total': 0, 'ext': 0, 'oral': 0, 'cond': 0}
        self.family_set = set()
        self.genus_set = set()
        # demais campos populados durante label_mrcas (checados via hasattr)


def parse_newick(s):
    """Parser de Newick simples. Aceita o subconjunto da megatree:
    rotulos opcionais (alfanumerico + _ . -), comprimentos opcionais (':float'),
    aninhamento por parenteses."""
    s = s.strip()
    if s.endswith(';'):
        s = s[:-1]
    pos = [0]
    n = len(s)

    LABEL_RE = re.compile(r'[A-Za-z0-9_.\-\']+')
    NUM_RE = re.compile(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?')

    def parse_node():
        children = []
        if pos[0] < n and s[pos[0]] == '(':
            pos[0] += 1
            children.append(parse_node())
            while pos[0] < n and s[pos[0]] == ',':
                pos[0] += 1
                children.append(parse_node())
            assert pos[0] < n and s[pos[0]] == ')', \
                f'esperando ) em pos {pos[0]} (proximo: {s[pos[0]:pos[0]+20]!r})'
            pos[0] += 1
        # rotulo opcional
        name = ''
        m = LABEL_RE.match(s, pos[0])
        if m:
            name = m.group(0)
            pos[0] = m.end()
        # comprimento opcional
        length = 0.0
        if pos[0] < n and s[pos[0]] == ':':
            pos[0] += 1
            m = NUM_RE.match(s, pos[0])
            if m:
                length = float(m.group(0))
                pos[0] = m.end()
        return Node(name=name, length=length, children=children)

    return parse_node()


def collect_tips(node, out):
    if not node.children:
        if node.name:
            out.append(node)
    else:
        for c in node.children:
            collect_tips(c, out)


def prune(node, keep_set):
    """Retorna novo no podado, ou None se subarvore inteira foi removida.
    Pos-ordem: poda filhos primeiro, depois decide se descarta este no."""
    if not node.children:
        return node if node.name in keep_set else None
    pruned_children = [prune(c, keep_set) for c in node.children]
    pruned_children = [c for c in pruned_children if c is not None]
    if not pruned_children:
        return None
    # Colapsa nos internos com apenas 1 filho (mantem topologia limpa)
    if len(pruned_children) == 1:
        child = pruned_children[0]
        child.length += node.length
        return child
    new = Node(name=node.name, length=node.length, children=pruned_children)
    return new


def annotate_post(node, species_by_tip):
    """Pos-ordem. Em cada no anota family_set, genus_set e counts (agregado de descendentes).
    Em tips, anota family/genus/epithet."""
    if not node.children:
        sp = species_by_tip.get(node.name)
        if sp:
            node.family = sp['family']
            node.genus = sp['genus']
            node.epithet = sp['epithet']
            node.family_set = {sp['family']}
            node.genus_set = {sp['genus']}
            node.counts = {
                'total': 1,
                'ext': 1 if sp['ext_morph']['status'] == 'described' else 0,
                'oral': 1 if sp['internal_oral']['status'] == 'described' else 0,
                'cond': 1 if sp['chondrocranium']['status'] == 'described' else 0,
            }
        return node.family_set, node.genus_set
    fams, gens = set(), set()
    agg = {'total': 0, 'ext': 0, 'oral': 0, 'cond': 0}
    for c in node.children:
        cf, cg = annotate_post(c, species_by_tip)
        fams |= cf
        gens |= cg
        for k in agg:
            agg[k] += c.counts[k]
    node.family_set = fams
    node.genus_set = gens
    node.counts = agg
    return fams, gens


def label_mrcas_pre(node, parent_family_set=None, parent_genus_set=None):
    """Pre-ordem. Marca mrca_family apenas no NO MAIS ALTO de cada familia monofiletica
    (igual para genero). MRCA = singleton e pai NAO tem mesmo singleton."""
    if len(node.family_set) == 1:
        f = next(iter(node.family_set))
        if parent_family_set is None or parent_family_set != node.family_set:
            node.mrca_family = f
    if len(node.genus_set) == 1:
        g = next(iter(node.genus_set))
        if parent_genus_set is None or parent_genus_set != node.genus_set:
            node.mrca_genus = g
    for c in node.children:
        label_mrcas_pre(c, node.family_set, node.genus_set)


def node_to_dict(node):
    d = {'name': node.name, 'length': node.length, 'counts': node.counts}
    if hasattr(node, 'mrca_family'):
        d['mrca_family'] = node.mrca_family
    if hasattr(node, 'mrca_genus'):
        d['mrca_genus'] = node.mrca_genus
    if hasattr(node, 'family'):
        d['family'] = node.family
    if hasattr(node, 'genus'):
        d['genus'] = node.genus
    if hasattr(node, 'epithet'):
        d['epithet'] = node.epithet
    if node.children:
        d['children'] = [node_to_dict(c) for c in node.children]
    return d


def main():
    with open(TREE_PATH) as f:
        nwk = f.read()
    root = parse_newick(nwk)

    all_tips = []
    collect_tips(root, all_tips)
    print(f'Megatree: {len(all_tips)} tips')

    sp = json.load(open(SPECIES_PATH))
    by_tip = {s['tip_label']: s for s in sp['species']}
    keep_set = set(by_tip.keys())
    tree_tips = {t.name for t in all_tips}

    matched = keep_set & tree_tips
    unmatched = sorted(keep_set - tree_tips)
    print(f'Spp brasileiras: {len(keep_set)}')
    print(f'Casadas: {len(matched)} ({round(len(matched)/len(keep_set)*100)}%)')
    print(f'Nao casadas: {len(unmatched)}')

    pruned = prune(root, matched)
    # Pos-ordem: agrega counts/family_set/genus_set
    annotate_post(pruned, by_tip)
    # Pre-ordem: marca apenas o no MAIS ALTO de cada familia/genero monofiletico
    label_mrcas_pre(pruned)

    out = {
        'schema_version': '5.0.0',
        'source': 'filogenia_jessyca_newNames.tre podada para as spp do banco',
        'generated': date.today().isoformat(),
        'tip_count': len(matched),
        'tree': node_to_dict(pruned),
    }
    with open(TREE_OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    size_kb = os.path.getsize(TREE_OUT) / 1024
    print(f'Arvore podada gravada em {TREE_OUT} ({size_kb:.1f} KB)')

    # Lista de nao casadas
    unmatched_full = [{
        'species': by_tip[t]['species'],
        'tip_label': t,
        'family': by_tip[t]['family'],
        'genus': by_tip[t]['genus'],
    } for t in unmatched]

    # Agrupa por familia pra facilitar leitura
    from collections import Counter, defaultdict
    by_fam = defaultdict(list)
    for u in unmatched_full:
        by_fam[u['family']].append(u['species'])
    fam_counts = Counter({f: len(v) for f, v in by_fam.items()})

    with open(UNMATCHED_OUT, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': date.today().isoformat(),
            'count': len(unmatched_full),
            'by_family': {f: sorted(by_fam[f]) for f in sorted(by_fam)},
            'species': unmatched_full,
        }, f, ensure_ascii=False, indent=2)
    print(f'Nao casadas em {UNMATCHED_OUT}')
    print(f'\nTop familias com spp nao casadas:')
    for f, n in fam_counts.most_common(10):
        print(f'  {f}: {n}')


if __name__ == '__main__':
    main()
