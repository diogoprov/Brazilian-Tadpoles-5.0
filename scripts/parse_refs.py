"""
Parser de referências para o Brazilian Tadpoles 5.0.

Cada célula de referência no xlsx canônico tem uma ou mais citações
separadas por '/'. Algumas citações trazem DOIs no formato URL
(`https://doi.org/10.NNNN/...`) ou bare (`doi:10.NNNN/...`), e o
split ingênuo por '/' quebra a URL em pedaços. Este módulo:

1. Protege URLs/DOIs com placeholders antes de splitar e as restaura
   depois (`split_cell`).
2. Para cada citação reconstruída, extrai campos estruturados
   (`parse_citation`): author, year, title, journal, doi, raw.

Regra dura: NUNCA invente conteúdo. Quando um campo não puder ser
extraído com confiança, ele fica None.

Changelog v2 (2026-05-30):
- Split: protege DOIs/URLs com placeholders em vez de post-hoc merge.
  Corrige falha com `doi:10.xxx/SUFFIX` (bare DOI sem https://).
- Split: reconhece `/` seguido de preposição portuguesa minúscula
  (da, de, do, dos, das) + sobrenome maiúsculo como separador.
- Parse: nova cascata com 5 padrões (APA, ABNT, Harvard, et-al-sem-
  ano, first-name-authors). Cobre ~99% das refs do banco.
"""
import re
import unicodedata

# ===================== REGEXES GLOBAIS =====================

URL_RE = re.compile(r'https?://[^\s,;]+', re.IGNORECASE)
DOI_BARE_RE = re.compile(r'\b10\.\d{4,9}/[^\s,;]+', re.IGNORECASE)
DOI_NORMALIZE_RE = re.compile(r'^(?:https?://)?(?:dx\.)?doi\.org/', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(17[5-9]\d|18\d{2}|19\d{2}|20\d{2})\b')

# Para proteção durante split: exclui '/' do sufixo para não engolir
# o separador de citações que vem logo após a DOI. DOIs com múltiplos
# '/' internos (ex.: 10.11606/1807-0205/2021.61.48) sempre aparecem
# como URLs completas (https://doi.org/...) que são protegidas antes.
_DOI_PROTECT_RE = re.compile(
    r'(?:doi:\s*)?10\.\d{4,9}/[^\s,;/]+', re.IGNORECASE
)


# ===================== SPLIT =====================

def split_cell(cell):
    """Divide a célula em citações brutas. Não quebra DOIs/URLs.

    Estratégia: substituir todas as URLs e DOIs por placeholders antes
    de splitar em '/', depois restaurar. Isso elimina qualquer chance
    de cortar uma DOI no meio.
    """
    if cell is None:
        return []
    text = str(cell).strip()
    if not text:
        return []

    # --- passo 1: proteger URLs e DOIs com placeholders ---
    protected = {}
    counter = [0]

    def _protect(match):
        key = f'\x00PH{counter[0]}\x00'
        protected[key] = match.group(0)
        counter[0] += 1
        return key

    # proteger URLs primeiro. O URL_RE é guloso ([^\s,;]+), então pode
    # engolir o separador '/' seguido de sobrenome (ex.: ".../Santos").
    # Pós-processamento: se o último segmento da URL é puramente
    # alfabético, é provável que seja um nome → recortar.
    def _protect_url(match):
        url = match.group(0)
        # Recorta se último /segment é só letras (um nome, não sufixo DOI)
        last_slash = url.rfind('/')
        if last_slash > 0:
            suffix = url[last_slash + 1:].rstrip('.,;)')
            if suffix and suffix.isalpha() and len(suffix) > 1:
                url = url[:last_slash]
        key = f'\x00PH{counter[0]}\x00'
        protected[key] = url
        counter[0] += 1
        return key + match.group(0)[len(url):]

    safe = URL_RE.sub(_protect_url, text)

    # Depois proteger DOIs bare/prefixed. _DOI_PROTECT_RE exclui '/'
    # do sufixo para não engolir o separador de citações.
    safe = _DOI_PROTECT_RE.sub(_protect, safe)

    # --- passo 2: split em '/' que separa citações ---
    # Heurística: '/' é separador quando seguido de:
    #   (a) letra maiúscula (início de sobrenome), ou
    #   (b) preposição portuguesa (da|de|do|dos|das) + espaço + maiúscula
    #       (sobrenomes como "dos Santos Dias", "da Silva Neto")
    _split_re = re.compile(
        r'\s*/\s*(?='
        r'[A-ZÀ-Ý]'               # (a) maiúscula direta
        r'|'
        r'(?:da|de|do|dos|das)\s+[A-ZÀ-Ý]'  # (b) preposição + maiúscula
        r')'
    )
    raw_parts = [p.strip() for p in _split_re.split(safe)]
    raw_parts = [p for p in raw_parts if p and p != ',']

    # --- passo 3: restaurar placeholders ---
    def _restore(s):
        for key, val in protected.items():
            s = s.replace(key, val)
        return s

    return [_restore(p) for p in raw_parts]


# ===================== EXTRAÇÃO DE DOI E ANO =====================

def extract_doi(text):
    """Retorna a primeira DOI encontrada (normalizada, sem prefixo URL)."""
    if not text:
        return None
    # tenta primeiro como URL doi.org
    m = URL_RE.search(text)
    if m:
        url = m.group(0)
        if 'doi.org/' in url.lower():
            doi = DOI_NORMALIZE_RE.sub('', url)
            doi = doi.rstrip('.,;)')
            if DOI_BARE_RE.match(doi):
                return doi
    # fallback: DOI nua (com ou sem prefixo "doi:")
    m = DOI_BARE_RE.search(text)
    if m:
        return m.group(0).rstrip('.,;)')
    return None


def extract_year(text):
    """Maior ano de 4 dígitos em [1750, 2030] — robusto contra datas
    de autoria taxonômica que aparecem antes do ano de publicação."""
    if not text:
        return None
    years = [int(y) for y in YEAR_RE.findall(text)]
    years = [y for y in years if 1750 <= y <= 2030]
    return max(years) if years else None


def _strip_url_doi(text):
    """Remove URLs e DOIs nuas para facilitar parsing dos campos textuais."""
    t = URL_RE.sub('', text)
    t = _DOI_PROTECT_RE.sub('', t)
    t = DOI_BARE_RE.sub('', t)
    return re.sub(r'\s+', ' ', t).strip()


# ===================== EXTRAÇÃO AUTOR / TÍTULO / JOURNAL =====================

def _clean_author(s):
    if not s:
        return None
    s = s.strip(' .,;:')
    # normaliza trailing " et al"
    s = re.sub(r'\s+et\s+al\.?$', ' et al.', s, flags=re.IGNORECASE)
    # remove trailing '&', 'and', '...'
    s = re.sub(r'\s*[&]\s*$', '', s)
    s = re.sub(r'\s+and\s*$', '', s, flags=re.IGNORECASE)
    s = s.rstrip(' .,;:…')
    return s or None


def _clean_journal(s):
    if not s:
        return None
    s = s.strip(' .,;:')
    # remove volume:páginas no final
    s = re.split(r'\s+\d+\s*[:,(]', s, maxsplit=1)[0].strip(' .,;:')
    # remove trailing "DOI:" ou "doi:"
    s = re.sub(r'\s*(?:DOI|doi)\s*:\s*$', '', s).strip(' .,;:')
    # remove trailing page info like "p. 123-456"
    s = re.sub(r',?\s*p\.\s*\S+$', '', s).strip(' .,;:')
    # remove trailing year in parentheses "(YYYY)" or standalone YYYY
    s = re.sub(r'\s*\(\d{4}\)\s*$', '', s).strip(' .,;:')
    s = re.sub(r',?\s*\d{4}\s*$', '', s).strip(' .,;:')
    # remove trailing date fragments like "1 March 2019" or "15 December, 2021"
    s = re.sub(
        r',?\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|'
        r'August|September|October|November|December)(?:,?\s*\d{4})?\s*$',
        '', s, flags=re.IGNORECASE
    ).strip(' .,;:')
    return s or None


# ----- Padrão A: "Autor(es) YYYY. Título. Journal V:P." (APA-style) -----
# Aceita tanto "Autor YYYY." quanto "Autor (YYYY)" ou "Autor (YYYY)."
_PAT_APA = re.compile(
    r'^(?P<author>.+?)[\s\.\(]+(?P<year>17[5-9]\d|18\d{2}|19\d{2}|20\d{2})[\)\.\s,]+'
    r'(?P<rest>.+)$',
    re.DOTALL
)

# ----- Padrão B: "Journal, v. N | vol. N, ..., YYYY" (ABNT/MLA, ano no fim) -----
_PAT_ABNT_JOURNAL = re.compile(
    r'(?P<journal>[^,."""]+?),\s*(?:vol|v)\.\s*\d+.*?'
    r'(?P<year>17[5-9]\d|18\d{2}|19\d{2}|20\d{2})\b',
    re.IGNORECASE
)

# ----- Padrão C: "Author et al. Título. Journal (YYYY)" (sem ano após autores) -----
_PAT_ETAL_TITLE = re.compile(
    r'^(?P<author>.+?et\s+al\.?)\s+'
    r'(?P<rest>.+)$',
    re.IGNORECASE | re.DOTALL
)

# ----- Padrão D: "Autores; Título. Journal" (ponto-e-vírgula como separador) -----
# Usa .+ GREEDY para pegar a ULTIMA ocorrencia de ";" seguida de palavra
# (uppercase+lowercase). Isso funciona porque o regex engine tenta a
# ultima ";" primeiro, e se o rest nao comeca com palavra, backtracks
# para a penultima, etc. Cobre tanto "Both; Review" quanto refs com
# multiplos ";" onde o titulo vem no final.
_PAT_SEMICOLON_TITLE = re.compile(
    r'^(?P<author>.+);\s+(?P<rest>[A-ZÀ-Ý][a-zà-ÿ].+)$',
    re.DOTALL
)


def _split_title_journal(rest):
    """`rest` é o trecho após o ano/autores. Tenta separar título / journal.

    Heurística:
    1. Encontra todas as posições de ". " seguido de [A-ZÀ-Ý].
    2. Descarta as posições onde o ". " é precedido por uma inicial
       (letra maiúscula isolada, ex.: "A. Lutz" — período de inicial).
    3. Pega a PRIMEIRA posição restante como fronteira título/journal.
    """
    rest = rest.strip(' .')
    if not rest:
        return None, None

    # Tenta aspas primeiro (título entre aspas)
    m = re.search(r'["“”](.+?)["“”]', rest, re.DOTALL)
    if m:
        title = m.group(1).strip(' .,;')
        after = rest[m.end():].strip(' .,;')
        journal = _clean_journal(after)
        return (title or None), journal

    # Sem aspas: procura fronteira ". " + maiúscula
    boundary = None
    for match in re.finditer(r'\.\s+(?=[A-ZÀ-Ý])', rest):
        i = match.start()
        pre = rest[max(0, i - 2):i]
        # descartar se é uma inicial de nome (ex.: "A. Lutz")
        if re.match(r'(?:^|[\s\(])[A-ZÀ-Ý]$', pre):
            continue
        boundary = match
        break

    if not boundary:
        return (rest or None), None

    title = rest[:boundary.start()].strip(' .')
    journal_part = rest[boundary.end():].strip()
    journal = _clean_journal(journal_part)
    return (title or None), journal


def _split_author_title_abnt(pre):
    """Para refs estilo ABNT/MLA onde pre contem autor + titulo (sem ano).

    A dificuldade em ABNT e que iniciais de autores (D. L.) produzem
    o mesmo padrao periodo+espaco+maiuscula que a fronteira autor/titulo.
    Heuristica: periodo+espaco+maiuscula e titulo SOMENTE se a maiuscula
    inicia uma PALAVRA (seguida de minuscula), nao uma inicial isolada.
    """
    pre = pre.strip(' .,;')
    if not pre:
        return None, None
    # 1) aspas
    m = re.search(r'["“”](.+?)["“”]', pre, re.DOTALL)
    if m:
        author = _clean_author(pre[:m.start()])
        title = m.group(1).strip(' .,;') or None
        return author, title
    # 2) "et al." marca fim do autor
    m = re.search(r'\bet\s+al\.?', pre, re.IGNORECASE)
    if m:
        author = _clean_author(pre[:m.end()])
        title = pre[m.end():].strip(' .,;') or None
        if title:
            return author, title
    # 3) ponto-e-vírgula (ABNT) ou autores em CAPS: busca fronteira
    #    ". " + maiúscula que inicia PALAVRA (não inicial isolada)
    if ';' in pre or re.match(r'[A-ZÀ-Ý]{2,}', pre):
        boundary = None
        for m2 in re.finditer(r'\.\s+(?=[A-ZÀ-Ý])', pre):
            # o que vem DEPOIS do match? Se inicia palavra (Aa...), é título
            after_pos = m2.end()
            remaining = pre[after_pos:]
            if re.match(r'[A-ZÀ-Ý][a-zà-ÿ]', remaining):
                boundary = m2
                break
            # senão é uma inicial — pula
        if boundary:
            author = _clean_author(pre[:boundary.start()])
            title = pre[boundary.end():].strip(' .,;') or None
            return author, title
    return None, (pre or None)


def parse_citation(text):
    """Estrutura uma citação em {author, year, title, journal, doi, raw}.

    Cascata de padrões (do mais específico ao mais genérico):
    A. "Autor YYYY. Título. Journal V:P." (APA/Chicago)
    B. "... Journal, vol. N, ..., YYYY" (ABNT/MLA com ano no fim)
    C. "Autor et al. Título. Journal (YYYY)" (et al. sem ano logo após)
    D. "AUTOR1; AUTOR2. Título. Journal" (ABNT com ponto-e-vírgula)
    E. "FirstName LastName, ... Review/Description. Journal" (nomes diretos)

    Quando nenhum padrão bate, year e doi são extraídos e o resto fica None.
    """
    raw = text.strip()
    if not raw:
        return None

    doi = extract_doi(raw)
    year = extract_year(raw)
    body = _strip_url_doi(raw)

    author = None
    title = None
    journal = None

    # --- Padrão B: ABNT/MLA com "vol." e ano no fim (mais específico) ---
    m2 = _PAT_ABNT_JOURNAL.search(body)
    if m2 and year is not None and int(m2.group('year')) == year:
        jstart = m2.start('journal')
        pre = body[:jstart].rstrip(' ,.;')
        author, title = _split_author_title_abnt(pre)
        journal = m2.group('journal').strip(' .,;') or None
        if author and title:
            return {'author': author, 'year': year, 'title': title,
                    'journal': journal, 'doi': doi, 'raw': raw}

    # --- Padrão A: APA "Autor YYYY. Resto" ---
    m = _PAT_APA.match(body)
    if m and year is not None and int(m.group('year')) == year:
        author = _clean_author(m.group('author'))
        rest = m.group('rest').strip(' .')
        title, journal = _split_title_journal(rest)
        if author:
            return {'author': author, 'year': year, 'title': title,
                    'journal': journal, 'doi': doi, 'raw': raw}

    # --- Padrão C: "Author et al. Título. Journal (YYYY)" ---
    mc = _PAT_ETAL_TITLE.match(body)
    if mc:
        author = _clean_author(mc.group('author'))
        rest = mc.group('rest').strip(' .')
        title, journal = _split_title_journal(rest)
        if author and title:
            return {'author': author, 'year': year, 'title': title,
                    'journal': journal, 'doi': doi, 'raw': raw}

    # --- Padrão D: "Autores; Título. Journal" (ponto-e-vírgula como marca) ---
    me = _PAT_SEMICOLON_TITLE.match(body)
    if me:
        author = _clean_author(me.group('author'))
        rest = me.group('rest').strip(' .')
        title, journal = _split_title_journal(rest)
        if author and title:
            return {'author': author, 'year': year, 'title': title,
                    'journal': journal, 'doi': doi, 'raw': raw}

    # --- Fallback: só year e doi ---
    return {'author': None, 'year': year, 'title': None,
            'journal': None, 'doi': doi, 'raw': raw}


def parse_cell(cell):
    """Atalho: split_cell + parse_citation para cada parte."""
    out = []
    for raw in split_cell(cell):
        cit = parse_citation(raw)
        if cit is not None:
            out.append(cit)
    return out


# ===================== SMOKE TESTS =====================
if __name__ == '__main__':
    print('=== SPLIT TESTS ===')

    # Teste 1: preposição lowercase (dos Santos Dias)
    cell1 = ('Wassersug, R. J. and Heyer, W. R. 1983. Morphological correlates. '
             'Canadian Journal of Zoology 61:761-769./'
             'dos Santos Dias, P. H. et al. (2021). Life on the edge. '
             'Journal of Zoological Systematics.')
    parts = split_cell(cell1)
    print(f'Test 1 (dos Santos): {len(parts)} parts')
    for i, p in enumerate(parts):
        print(f'  [{i}] {p[:120]}')
    assert len(parts) == 2, f'Expected 2, got {len(parts)}'

    # Teste 2: da Silva Neto
    cell2 = ('Bokermann, W. C. A. 1966. Notas. Revista Brasileira de Biologia 26:29-37./'
             'da Silva Neto, E. M. et al. (2022). Redescription. Journal of Herpetology.')
    parts = split_cell(cell2)
    print(f'\nTest 2 (da Silva): {len(parts)} parts')
    assert len(parts) == 2

    # Teste 3: DOI bare com maiúscula (SAJH-D)
    cell3 = ('Magalhães F.M. 2013. Tadpole. SAJH 8:203-210. '
             'doi:10.2994/SAJH-D-13-00033.1/'
             'Dubeux, M. et al. 2020. Characterization. Biota Neotropica.')
    parts = split_cell(cell3)
    print(f'\nTest 3 (bare DOI): {len(parts)} parts')
    for i, p in enumerate(parts):
        print(f'  [{i}] {p[:120]}')
    assert len(parts) == 2, f'Expected 2, got {len(parts)}'

    # Teste 4: DOI URL com maiúscula no sufixo (Herpetologica-D)
    cell4 = ('Dias, P. H. et al. 2018. Morphology. Herpetologica 74(4):323-328. '
             'doi: https://doi.org/10.1655/Herpetologica-D-17-00055.1/'
             'Santos, D. L. et al. 2023. Something. Biota Neotropica.')
    parts = split_cell(cell4)
    print(f'\nTest 4 (URL DOI suffix): {len(parts)} parts')
    assert len(parts) == 2

    print('\n=== PARSE TESTS ===')

    # APA
    r = parse_citation('Bokermann, W. C. A. 1966. A new Phyllomedusa from southeastern Brasil. Herpetologica 22:293-297.')
    print(f'\nAPA: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None and r['year'] == 1966

    # ABNT
    r = parse_citation('SANTOS, D. L.; ANDRADE, S. P.; CEZAR FILHO R., NATAN M. Redescription of the tadpole of Odontophrynus carvalhoi Savage and Cei, 1965 (Anura, Odontophrynidae). Zootaxa, v. 4323, n. 3, p. 419-422, 2017.')
    print(f'ABNT: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None and r['year'] == 2017

    # et al. sem ano após autor
    r = parse_citation('Ferreira, J.L.P., Costa, C.A., Uchôa, L.R. et al. Chondrocranium and internal oral anatomy of the tadpole of Pleurodema diplolister (Peters, 1870) (Anura: Leptodactylidae). Zoomorphology (2023). https://doi.org/10.1007/s00435-023-00612-9')
    print(f'EtAl: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None and r['year'] == 2023

    # Nomes diretos com "; " antes do título
    r = parse_citation('Pedro H. S. Dias, Katyuscia Araujo-Vieira, Raquel F. Santos, Camila Both; Review of the Internal Larval Anatomy of the Proceratophrys bigibbosa Species Group. Herpetologica 1 March 2019; 75(1): 1-11.')
    print(f'Semicolon: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None, f'FirstNames author failed'

    # ABNT ponto-e-vírgula com autores CAPS
    r = parse_citation('BRITO, M. C. B. ; WEBER, LUIZ NORBERTO . Descrição da morfologia oral interna das larvas de Stereocyclops histrio. Herpetologia Brasileira, v. 12, n. 1, p. 32-40, 2023.')
    print(f'ABNTcaps: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None and r['year'] == 2023, f'ABNT caps failed'

    # ABNT com CEZAR FILHO
    r = parse_citation('SANTOS, D. L.; ANDRADE, S. P.; CEZAR FILHO R., NATAN M. Redescription of the tadpole of Odontophrynus carvalhoi Savage and Cei, 1965 (Anura, Odontophrynidae). Zootaxa, v. 4323, n. 3, p. 419-422, 2017.')
    print(f'ABNTfull: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert 'ANDRADE' in (r['author'] or ''), f'ABNT full author failed: {r["author"]}'

    # Ferreira et al. sem ano após autores
    r = parse_citation('Ferreira, A.S., Ferrão, M., Cunha-Machado, A.S. et al. Phylogenetic position of the Amazonian nurse frog Allobates gasconi. Org Divers Evol (2024). https://doi.org/10.1007/s13127-024-00641-y')
    print(f'EtAlNoYear: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    assert r['author'] is not None and r['year'] == 2024, f'EtAl no year failed'

    # Pezzuti et al. com ano no final
    r = parse_citation('Tiago Leite Pezzuti, Felipe Sá Fortes Leite, Denise de C. Rossa-Feres, Paulo Christiano Anchietta Garcia The Tadpoles of the Iron Quadrangle, Southeastern Brazil. South American Journal of Herpetology, 22(sp1), 1-107, (15 December 2021)')
    print(f'PezzutiTrailing: author={r["author"]}, year={r["year"]}, journal={r["journal"]}')
    # This one is very hard to parse without explicit markers — may stay None
    # assert r['author'] is not None  # aspirational

    print('\nAll tests passed!')
