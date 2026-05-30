"""
Constrói a rede de coautoria a partir do species.json e exporta JSON
no formato Cytoscape.js para a aba 'Colaborações' do site.

Pipeline:
  1. Para cada ref única do banco, parsea a lista de autores em uma forma
     canônica `Lastname, F` (sobrenome + primeira inicial, normalizado
     sem acentos pra matching).
  2. Constrói grafo de coautoria (nó = autor; aresta = par de autores
     que compartilharam ≥1 paper; peso = nº de papers compartilhados).
  3. Calcula métricas (degree, betweenness, closeness, eigenvector,
     PageRank) e detecta comunidades via Louvain.
  4. Exporta `assets/data/coauthor_network.json` em formato
     Cytoscape.js: {nodes:[{data:{...}}], edges:[{data:{...}}]}.

Uso (a partir da raiz do projeto):
    python3 scripts/build_coauthor_network.py
"""
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations

import networkx as nx
from networkx.algorithms.community import louvain_communities

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JSON_IN  = os.path.join(PROJECT_ROOT, 'assets', 'data', 'species.json')
JSON_OUT = os.path.join(PROJECT_ROOT, 'assets', 'data', 'coauthor_network.json')

# Partículas comuns em sobrenomes compostos
PARTICLES = r'(?:de|da|do|dos|das|von|van|del|du|la|le|di|del|y)'

# Pattern 1: "Lastname, F.M." (formato dominante)
RE_LASTNAME_FIRST = re.compile(
    r"([A-ZÀ-Ý][a-zA-ZÀ-ÿ\-'’]+"
    r"(?:\s+(?:" + PARTICLES + r")\s+[A-ZÀ-Ý][a-zA-ZÀ-ÿ\-'’]+)*)"
    r"\s*,\s*"
    r"((?:[A-Z]\.?\s*)+)"
)
# Pattern 2: "F.M. Lastname" (fallback)
RE_FIRST_LAST = re.compile(
    r"((?:[A-Z]\.\s*){1,5})\s*"
    r"([A-ZÀ-Ý][a-zA-ZÀ-ÿ\-'’]+"
    r"(?:\s+(?:" + PARTICLES + r")\s+[A-ZÀ-Ý][a-zA-ZÀ-ÿ\-'’]+)*)"
)
# Pattern 3: "Lastname FM" (no comma between surname and initials)
RE_LASTNAME_NOCOMMA = re.compile(
    r"\b([A-ZÀ-Ý][a-zA-ZÀ-ÿ\-']+"
    r"(?:\s+(?:" + PARTICLES + r")\s+[A-ZÀ-Ý][a-zA-ZÀ-ÿ\-']+)*)"
    r"\s+([A-Z]{1,4})\b(?!\.)"
)


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def canonical_author(surname, initials):
    """Forma canônica: 'Lastname F' (sem acento, só primeira inicial)."""
    surname = strip_accents(surname).strip()
    # title case do sobrenome (ex.: SILVA -> Silva)
    parts = []
    for tok in surname.split():
        if tok.lower() in {'de','da','do','dos','das','von','van','del','du','la','le','di','y'}:
            parts.append(tok.lower())
        else:
            parts.append(tok.capitalize())
    surname = ' '.join(parts)
    initials = strip_accents(initials).replace('.', '').replace(' ', '').upper()
    first_initial = initials[:1] if initials else ''
    if not first_initial:
        return surname
    return f'{surname}, {first_initial}'


def parse_authors(author_str):
    """Parsea string de autores em lista de formas canônicas."""
    if not author_str:
        return []
    s = author_str.strip()
    # Normaliza separadores: & -> and; ', and ' / ' AND ' -> ' and '
    s = re.sub(r'\s*&\s*', ' and ', s)
    s = re.sub(r'\s+AND\s+', ' and ', s)
    s = re.sub(r'\s+And\s+', ' and ', s)
    # Drop "et al."
    s = re.sub(r'\bet\s*al\.?\b', '', s, flags=re.IGNORECASE).strip(' ,.')
    if not s:
        return []

    # Tenta padrão 1 (dominante: 'Lastname, F.M.')
    matches = RE_LASTNAME_FIRST.findall(s)
    if matches:
        out = []
        for sur, ini in matches:
            ca = canonical_author(sur, ini)
            if ca and ca not in out:
                out.append(ca)
        if out:
            return out

    # Padrão 2: 'F.M. Lastname'
    matches = RE_FIRST_LAST.findall(s)
    if matches:
        out = []
        for ini, sur in matches:
            ca = canonical_author(sur, ini)
            if ca and ca not in out:
                out.append(ca)
        if out:
            return out

    # Padrão 3: 'Lastname FM' (sem ponto, sem vírgula)
    matches = RE_LASTNAME_NOCOMMA.findall(s)
    if matches:
        out = []
        for sur, ini in matches:
            ca = canonical_author(sur, ini)
            if ca and ca not in out:
                out.append(ca)
        if out:
            return out

    return []


def build_graph(species_data):
    """Constrói grafo de coautoria a partir do species.json."""
    seen_refs = {}  # ref_key -> {'authors': [...], 'year': int}
    chars = ['ext_morph', 'internal_oral', 'chondrocranium']
    for sp in species_data['species']:
        for ch in chars:
            for r in sp[ch].get('refs', []):
                if not isinstance(r, dict): continue
                key = ('doi:' + r['doi']) if r.get('doi') else ('raw:' + (r.get('raw') or ''))
                if key in seen_refs: continue
                authors = parse_authors(r.get('author') or '')
                if not authors: continue
                seen_refs[key] = {'authors': authors, 'year': r.get('year')}

    print(f'Refs únicas com >=1 autor parseado: {len(seen_refs)}')
    # contagem por autor
    paper_count = Counter()
    for info in seen_refs.values():
        for a in info['authors']:
            paper_count[a] += 1
    print(f'Autores únicos: {len(paper_count)}')
    print(f'Distribuição de papers/autor: 1 paper = {sum(1 for v in paper_count.values() if v==1)}, '
          f'2-5 = {sum(1 for v in paper_count.values() if 2<=v<=5)}, '
          f'6+ = {sum(1 for v in paper_count.values() if v>=6)}')

    G = nx.Graph()
    for author, n in paper_count.items():
        G.add_node(author, papers=n)
    # arestas: par de autores que coassinaram ao menos um paper
    edge_weight = Counter()
    edge_years = defaultdict(list)
    for info in seen_refs.values():
        a_set = sorted(set(info['authors']))
        for a, b in combinations(a_set, 2):
            edge_weight[(a, b)] += 1
            if info['year']:
                edge_years[(a, b)].append(info['year'])
    for (a, b), w in edge_weight.items():
        years = edge_years[(a, b)]
        G.add_edge(a, b, weight=w,
                   first_year=min(years) if years else None,
                   last_year=max(years) if years else None)
    print(f'Grafo: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas')
    return G, seen_refs


def compute_metrics(G):
    print('Calculando métricas de centralidade...')
    deg = dict(G.degree())
    # Para grafo grande, betweenness exato é O(VE). 1300 nós ainda dá.
    btw = nx.betweenness_centrality(G, normalized=True, weight=None)
    try:
        eig = nx.eigenvector_centrality(G, max_iter=1000, tol=1e-6)
    except nx.PowerIterationFailedConvergence:
        eig = {n: 0 for n in G.nodes()}
    pr = nx.pagerank(G, alpha=0.85)
    return {'degree': deg, 'betweenness': btw, 'eigenvector': eig, 'pagerank': pr}


def detect_communities(G):
    print('Detectando comunidades (Louvain)...')
    comms = louvain_communities(G, weight='weight', seed=42)
    comm_id = {}
    for i, comm in enumerate(comms):
        for n in comm:
            comm_id[n] = i
    print(f'  {len(comms)} comunidades; maior com {max(len(c) for c in comms)} autores')
    return comm_id, len(comms)


def export_cytoscape(G, metrics, comm_id, n_comms, out_path):
    nodes = []
    for n, d in G.nodes(data=True):
        nodes.append({'data': {
            'id': n,
            'name': n,
            'papers': d.get('papers', 1),
            'degree': metrics['degree'][n],
            'betweenness': round(metrics['betweenness'][n], 6),
            'eigenvector': round(metrics['eigenvector'][n], 6),
            'pagerank':   round(metrics['pagerank'][n],   6),
            'community': comm_id.get(n, -1),
        }})
    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({'data': {
            'id': f'{u}__{v}',
            'source': u, 'target': v,
            'weight': d.get('weight', 1),
            'first_year': d.get('first_year'),
            'last_year':  d.get('last_year'),
        }})
    payload = {
        'schema_version': '1.0',
        'generated': __import__('datetime').date.today().isoformat(),
        'n_nodes': len(nodes),
        'n_edges': len(edges),
        'n_communities': n_comms,
        'nodes': nodes,
        'edges': edges,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\nSaved -> {out_path}  ({os.path.getsize(out_path)//1024} KB)')


def main():
    d = json.load(open(JSON_IN, encoding='utf-8'))
    G, refs = build_graph(d)
    metrics = compute_metrics(G)
    comm_id, n_comms = detect_communities(G)
    export_cytoscape(G, metrics, comm_id, n_comms, JSON_OUT)

    # Top-10 por métrica (sanity check)
    print('\n--- Top 10 por nº de papers ---')
    by_papers = sorted(G.nodes(data=True), key=lambda x: -x[1].get('papers', 0))[:10]
    for n, d in by_papers:
        print(f'  {d["papers"]:3d}  {n}')

    print('\n--- Top 10 por degree centrality (nº de coautores únicos) ---')
    top_deg = sorted(metrics['degree'].items(), key=lambda x: -x[1])[:10]
    for n, k in top_deg:
        print(f'  {k:3d}  {n}')

    print('\n--- Top 10 por betweenness (pontes entre subcomunidades) ---')
    top_btw = sorted(metrics['betweenness'].items(), key=lambda x: -x[1])[:10]
    for n, b in top_btw:
        print(f'  {b:.4f}  {n}')


if __name__ == '__main__':
    main()
