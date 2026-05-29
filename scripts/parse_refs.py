"""
Parser de referências para o Brazilian Tadpoles 5.0.

Cada célula de referência no xlsx canônico tem uma ou mais citações
separadas por '/'. Algumas citações trazem DOIs no formato URL
(`https://doi.org/10.NNNN/...`), e o split ingênuo por '/' quebra a
URL em pedaços. Este módulo:

1. Protege URLs antes de splitar e as restaura depois (`split_cell`).
2. Para cada citação reconstruída, extrai campos estruturados
   (`parse_citation`): author, year, title, journal, doi, raw.

Regra dura: NUNCA invente conteúdo. Quando um campo não puder ser
extraído com confiança, ele fica None.
"""
import re
import unicodedata

# Regex para detectar URLs em geral e DOIs específicos.
URL_RE = re.compile(r'https?://[^\s,;]+', re.IGNORECASE)
DOI_BARE_RE = re.compile(r'\b10\.\d{4,9}/[^\s,;]+', re.IGNORECASE)
DOI_NORMALIZE_RE = re.compile(r'^(?:https?://)?(?:dx\.)?doi\.org/', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(17[5-9]\d|18\d{2}|19\d{2}|20\d{2})\b')

# Regex de split: '/' seguido de espaço opcional e letra maiúscula
# (ou de início de uma URL — ou seja, evitamos quebrar `https://` que
# tem '/' seguido de '/').
#
# Esta heurística aproveita que:
# - Início de uma nova referência começa com sobrenome capitalizado.
# - DOIs (`10.NNNN/...`) têm caracteres minúsculos ou dígitos após
#   cada '/' interno.
# - `https://` tem '/' seguido de '/', que também falha o lookahead.
#
# Testado contra ambos os casos do banco: refs com DOI completo
# preservada, refs sem DOI separadas corretamente.
_SPLIT_RE = re.compile(r'\s*/\s*(?=[A-ZÀ-Ý])')


# Token "DOI-suffix-like": uma sequência sem espaços contendo só
# letras/dígitos/`.-_`. Usado para detectar quando um fragmento depois
# do split é, na verdade, continuação de uma DOI cuja parte final
# começa com letra maiúscula (ex.: `10.1655/Herpetologica-D-17-00055.1`).
_DOI_SUFFIX_TOKEN_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


def split_cell(cell):
    """Divide a célula em citações brutas. Não quebra DOIs/URLs.

    Passo 1: split em '/' seguido de letra maiúscula.
    Passo 2: refunde fragmentos que sejam, na verdade, sufixo de DOI:
    fragmento N começa com token DOI-like e o fragmento N-1 contém uma
    URL não terminada (`https?://` sem ter atingido whitespace ainda).
    """
    if cell is None:
        return []
    text = str(cell).strip()
    if not text:
        return []
    raw_parts = [p.strip() for p in _SPLIT_RE.split(text)]
    raw_parts = [p for p in raw_parts if p and p != ',']

    # passo 2: merge de continuações de DOI
    merged = []
    for p in raw_parts:
        if merged and _looks_like_doi_suffix(p) and _has_open_url(merged[-1]):
            merged[-1] = merged[-1] + '/' + p
        else:
            merged.append(p)
    return merged


def _looks_like_doi_suffix(s):
    """Token sem espaços e composto só por chars válidos de DOI."""
    if ' ' in s or ',' in s or ';' in s:
        return False
    return bool(_DOI_SUFFIX_TOKEN_RE.match(s))


def _has_open_url(s):
    """Última URL do fragmento parece interrompida (terminou em chars
    típicos de DOI, sem pontuação de fim de frase nem espaço)."""
    m = list(URL_RE.finditer(s))
    if not m:
        return False
    url = m[-1].group(0)
    # se a URL terminou em char típico de DOI (letra/dígito/`-_`),
    # provavelmente foi cortada
    return bool(re.search(r'[A-Za-z0-9_\-]$', url))


# ------------------ extração estruturada ------------------

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
    # fallback: DOI nua no meio do texto
    m = DOI_BARE_RE.search(text)
    if m:
        return m.group(0).rstrip('.,;)')
    return None


def extract_year(text):
    """Maior ano de 4 dígitos em [1850, 2030] — robusto contra datas
    de autoria taxonômica que aparecem antes do ano de publicação."""
    if not text:
        return None
    years = [int(y) for y in YEAR_RE.findall(text)]
    years = [y for y in years if 1750 <= y <= 2030]
    return max(years) if years else None


def _strip_url(text):
    """Remove URLs e DOIs nuas para facilitar parsing dos campos textuais."""
    t = URL_RE.sub('', text)
    t = DOI_BARE_RE.sub('', t)
    return re.sub(r'\s+', ' ', t).strip()


# Heurísticas de autor e título.
# Padrões comuns observados:
#   "Autor1, X. and Autor2, Y. YYYY. Título. Journal V:P."
#   "Autor1, Autor2 YYYY Título. Journal V:P"
#   "Autor1, X. (YYYY) Título. Journal V, P"
#   "AUTOR1, X.; AUTOR2, Y. Título... Journal, v. N, n. M, p. P-Q, YYYY."

# Captura: tudo antes do ano (com ou sem parênteses) -> author block.
# Cobre tanto "Autor YYYY." quanto "Autor (YYYY)" — APA-style.
_AUTHOR_YEAR_RE = re.compile(
    r'^(?P<author>.+?)[\s\.\(]+(?P<year>17[5-9]\d|18\d{2}|19\d{2}|20\d{2})[\)\.\s]'
)

# Captura no padrão "Journal, v. N | vol. N, ..., YYYY" (ABNT/MLA).
# Aceita `v.`, `vol.`, `Vol.`, etc., e ano em qualquer lugar à direita.
_TRAILING_YEAR_RE = re.compile(
    r'(?P<journal>[^,.“”"]+?),\s*(?:vol|v)\.\s*\d+.*?'
    r'(?P<year>17[5-9]\d|18\d{2}|19\d{2}|20\d{2})\b',
    re.IGNORECASE
)



def _clean_author(s):
    s = s.strip(' .,;')
    # remove trailing " et al"
    s = re.sub(r'\s+et\s+al\.?$', ' et al.', s, flags=re.IGNORECASE)
    return s or None


def _split_author_title(pre):
    """No padrão "Journal, vol. N, …, YYYY", o `pre` contém autor + título.
    Heurísticas (em ordem):
    1. Aspas curvas ou retas em volta do título → split na 1ª aspa.
    2. ``et al.`` indica fim do autor → split aí.
    3. Se nenhuma marca clara, autor=None, title=pre (não fabrica).
    """
    pre = pre.strip(' .,;')
    if not pre:
        return None, None
    # 1) aspas curvas ou retas que cercam o título
    m = re.search(r'[“"](.+?)[”"]', pre, re.DOTALL)
    if m:
        author = _clean_author(pre[:m.start()].rstrip(' .,;'))
        title = m.group(1).strip(' .,;') or None
        return author, title
    # 2) "et al." marca fim do bloco de autores
    m = re.search(r'\bet\s+al\.?', pre, re.IGNORECASE)
    if m:
        author = _clean_author(pre[:m.end()])
        title = pre[m.end():].strip(' .,;') or None
        if title:
            return author, title
    return None, (pre or None)


def _split_title_journal(rest):
    """`rest` é o trecho após o ano. Tenta separar título / journal.

    Heurística:
    1. Encontra todas as posições de ". " seguido de [A-ZÀ-Ý].
    2. Descarta as posições onde o ". " é precedido por uma inicial
       (letra maiúscula isolada, ex.: "A. Lutz" — período de inicial).
    3. Pega a PRIMEIRA posição restante como fronteira título/journal.
    Se nada bate, retorna (rest, None).
    """
    rest = rest.strip(' .')
    if not rest:
        return None, None
    boundary = None
    for m in re.finditer(r'\.\s+(?=[A-ZÀ-Ý])', rest):
        # caractere ANTES do '.'? Se for letra maiúscula sozinha
        # (precedida por espaço/início), é inicial — ignora.
        i = m.start()
        # janela: até 3 chars antes do '.'
        pre = rest[max(0, i - 2):i]
        # padrão de inicial: " X" ou início da string + "X"
        if re.match(r'(?:^|[\s\(])[A-ZÀ-Ý]$', pre):
            continue
        boundary = m
        break
    if not boundary:
        return rest or None, None
    title = rest[:boundary.start()].strip(' .')
    journal_part = rest[boundary.end():].strip()
    # remove volume:páginas no final do journal
    journal = re.split(r'\d+\s*[:,(]', journal_part, maxsplit=1)[0].strip(' .,')
    return (title or None), (journal or None)


def parse_citation(text):
    """Estrutura uma citação em {author, year, title, journal, doi, raw}.

    Política conservadora (consistente com a regra "nunca fabricar"):

    - ``year`` e ``doi`` são extraídos com alta confiança e podem aparecer
      mesmo em refs com múltiplas datas (de autoria taxonômica, etc.).
    - ``author``, ``title`` e ``journal`` só são preenchidos quando a
      citação contém UM ÚNICO ano de 4 dígitos (caso "fácil") OU quando
      o padrão Brasileiro `Journal, v. N, n. M, p. P-Q, YYYY` é
      reconhecido. Em qualquer outro caso ficam None — a string completa
      em ``raw`` ainda permite curadoria manual posterior.
    """
    raw = text.strip()
    if not raw:
        return None

    doi = extract_doi(raw)
    year = extract_year(raw)
    body = _strip_url(raw)

    author = None
    title = None
    journal = None

    # Caso A: padrão "Journal, vol. N | v. N, ..., YYYY" (ABNT/MLA com
    # ano no final). Tem PRIORIDADE porque é específico — se bate,
    # `journal` é confiável. Funciona pra refs estilo PeerJ/Zootaxa/
    # Biota Neotropica/ABNT.
    m2 = _TRAILING_YEAR_RE.search(body)
    if m2 and year is not None and int(m2.group('year')) == year:
        jstart = m2.start('journal')
        pre = body[:jstart].rstrip(' ,.;')
        author, title = _split_author_title(pre)
        journal = m2.group('journal').strip(' .,;') or None
    else:
        # Caso B: padrão "Autor YYYY. Resto" no INÍCIO do texto. Só
        # válido se o YYYY capturado é o maior ano da string (evita
        # contaminação por datas de autoria taxonômica).
        m = _AUTHOR_YEAR_RE.match(body)
        if m and year is not None and int(m.group('year')) == year:
            author = _clean_author(m.group('author'))
            rest = body[m.end():].strip(' .')
            title, journal = _split_title_journal(rest)
        # se nenhum padrão bate, autor/título/journal ficam None.

    return {
        'author': author,
        'year': year,
        'title': title,
        'journal': journal,
        'doi': doi,
        'raw': raw,
    }


def parse_cell(cell):
    """Atalho: split_cell + parse_citation para cada parte."""
    out = []
    for raw in split_cell(cell):
        cit = parse_citation(raw)
        if cit is not None:
            out.append(cit)
    return out


# ------------------ smoke tests ------------------
if __name__ == '__main__':
    samples = [
        'dos Santos Dias, P.H., Delia, J., Taboada, C. et al. 2024. A hundred-year-old mystery. Sci Nat 111, 21 (2024). https://doi.org/10.1007/s00114-024-01910-y',
        'Bokermann, W. C. A. 1966. A new Phyllomedusa from southeastern Brasil. Herpetologica 22:293-297.',
        'SANTOS, D. L.; ANDRADE, S. P.; CEZAR FILHO R., NATAN M. Redescription of the tadpole of Odontophrynus carvalhoi Savage and Cei, 1965 (Anura, Odontophrynidae). Zootaxa, v. 4323, n. 3, p. 419-422, 2017.',
        'Faivovich, J. (1996) La larva de Hyla semiguttata A. Lutz, 1925 (Anura, Hylidae). Cuadernos de Herpetología, 9, 61-67.',
        # PeerJ-style com vol. + aspas curvas
        'Ferrão, Miquéias, et al. “A New Nurse Frog of the Allobates Tapajos Species Complex (Anura: Aromobatidae) from the Upper Madeira River”. PeerJ, vol. 10, agosto de 2022, p. e13751. https://doi.org/10.7717/peerj.13751.',
        # Pre-1850 (Hutchinson 1796)
        'Hutchinson, T  1796  The natural history of the frog fish of Surinam  8 p, G. Peacock, York',
    ]
    for s in samples:
        print('---')
        print(parse_citation(s))

    print('\n--- split_cell smoke (cell com 2 refs + DOI URL) ---')
    cell = ('dos Santos Dias, P.H. et al. 2024. Um trabalho. Sci Nat 111, 21 (2024). '
            'https://doi.org/10.1007/s00114-024-01910-y/'
            'Bokermann, W. C. A. 1966. Outro. Herpetologica 22:293-297.')
    for i, p in enumerate(split_cell(cell), 1):
        print(f'  [{i}]', p[:150])

    print('\n--- split_cell smoke (DOI suffix com maiuscula) ---')
    cell3 = ('Pedro Henrique dos Santos Dias, et al. Buccopharyngeal Morphology. '
             'Herpetologica 1 December 2018; 74 (4): 323-328. '
             'doi: https://doi.org/10.1655/Herpetologica-D-17-00055.1/'
             'Santos, Danusy Lopes, et al. Morphological. Biota Neotropica, 2023.')
    for i, p in enumerate(split_cell(cell3), 1):
        print(f'  [{i}]', p[:160])

    print('\n--- split_cell smoke (cell com DOI SciELO no meio) ---')
    cell2 = ('Heyer, W. R. 1983. Variation... Arquivos de Zoologia 30:235-339./'
             'Colaço, Gustavo, et al. The Tadpole... Papéis Avulsos de Zoologia, '
             'vol. 61, julho de 2021, p. e20216148. SciELO, '
             'https://doi.org/10.11606/1807-0205/2021.61.48./'
             'Pedrozo M, Botelho LM. 2022. Outra coisa. Zootaxa 1234:1-10.')
    for i, p in enumerate(split_cell(cell2), 1):
        print(f'  [{i}]', p[:150])
