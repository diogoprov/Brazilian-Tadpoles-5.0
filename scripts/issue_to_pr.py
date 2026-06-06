"""
Lê o corpo de uma issue do GitHub (formato gerado pelos Issue Forms YAML)
e aplica a alteração correspondente em assets/data/species.json.

Hoje suporta apenas o template `add_reference.yml` (label = `add-reference`).
Outros tipos voltam código 0 com mensagem informativa pra que o Action
deixe o issue passar sem abrir PR.

Uso (dentro do GitHub Action):
    python3 scripts/issue_to_pr.py \
        --body-file issue_body.md \
        --labels 'add-reference,contribution' \
        --issue-number 42

Saída:
    - Modifica assets/data/species.json IN-PLACE se aplicável
    - Imprime um resumo da mudança em stdout (capturado pelo Action)
    - Exit 0 = sucesso (com ou sem mudança); exit 1 = erro de validação
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JSON_PATH = os.path.join(PROJECT_ROOT, 'assets', 'data', 'species.json')

CHARACTER_MAP = {
    'External morphology (ext_morph)':       'ext_morph',
    'Internal oral cavity (internal_oral)':  'internal_oral',
    'Chondrocranium (chondrocranium)':       'chondrocranium',
}

# Famílias aceitas no banco (com girino livre-natante). Lista alinhada
# com Drummond et al. 2026 e o filtro `EXCLUDE_FAMILIES` do builder
# original (xlsx → json).
VALID_FAMILIES = {
    'Allophrynidae', 'Alsodidae', 'Aromobatidae', 'Bufonidae',
    'Centrolenidae', 'Ceratophryidae', 'Cycloramphidae', 'Dendrobatidae',
    'Hylidae', 'Hylodidae', 'Leptodactylidae', 'Microhylidae',
    'Odontophrynidae', 'Phyllomedusidae', 'Pipidae', 'Ranidae',
}


def parse_issue_body(body):
    """GitHub Issue Forms renderizam o YAML como markdown:

        ### Espécie (binomial completo)

        Boana faber

        ### Caráter descrito nesta referência

        External morphology (ext_morph), Internal oral cavity (internal_oral)

    Esta função extrai cada bloco `### <label>` → valor.
    """
    sections = {}
    current = None
    buf = []
    for line in body.splitlines():
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m:
            if current is not None:
                sections[current] = '\n'.join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = '\n'.join(buf).strip()
    return sections


def fail(msg, code=1):
    print(f'::error::{msg}', file=sys.stderr)
    print(f'\n**VALIDATION FAILED:** {msg}')
    sys.exit(code)


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()


def find_species(data, query):
    """Retorna o objeto da spp se achar; senão, lista sugestões."""
    q = query.strip()
    q_slug = slugify(q)
    for sp in data['species']:
        if sp['species'].lower() == q.lower() or sp['id'] == q_slug:
            return sp, None
    # sem match exato — sugere similares (substring no nome)
    parts = q.lower().split()
    suggestions = []
    for sp in data['species']:
        name = sp['species'].lower()
        if all(p in name for p in parts):
            suggestions.append(sp['species'])
        if len(suggestions) >= 10:
            break
    return None, suggestions


def normalize_response(val):
    """Issue Forms colocam 'No response' quando o usuário não preencheu campo opcional."""
    if not val: return None
    s = val.strip()
    if s.lower() in {'_no response_', '_none_', 'n/a'}:
        return None
    return s


def parse_selected_characters(field_value):
    """Lê o markdown gerado por um campo `dropdown multiple` (checkbox)
    e retorna a lista de caracteres canônicos selecionados."""
    if not field_value:
        return []
    out = []
    for line in field_value.splitlines():
        m = re.match(r'^\s*-\s*\[\s*[xX]\s*\]\s*(.+?)\s*$', line)
        if m:
            label = m.group(1)
            if label in CHARACTER_MAP:
                out.append(CHARACTER_MAP[label])
        else:
            s = line.strip()
            if s in CHARACTER_MAP:
                out.append(CHARACTER_MAP[s])
    return list(dict.fromkeys(out))   # dedup, preserva ordem


def parse_reference_block(sec):
    """Extrai e valida o bloco de campos de referência (author, year, ...)
    presente tanto no template add_reference quanto add_species.
    Retorna o dict do ref pronto para inserir no JSON, ou None se vazio."""
    author = normalize_response(sec.get('Autores da referência') or
                                sec.get('Autores da referência (girino)') or
                                sec.get('Autores da ref que descreveu o girino'))
    year_str = normalize_response(sec.get('Ano de publicação'))
    title = normalize_response(sec.get('Título do artigo'))
    journal = normalize_response(sec.get('Periódico'))
    doi = normalize_response(sec.get('DOI'))
    raw = normalize_response(sec.get('Citação completa (raw) — opcional'))

    if not (author or title or year_str or doi):
        return None   # nenhum campo de ref preenchido

    if not (author and title):
        fail('Campos `Autores` e `Título` são obrigatórios quando há referência.')
    try:
        year = int(year_str)
    except (TypeError, ValueError):
        fail(f'Ano inválido: {year_str!r}')
    if year < 1750 or year > 2030:
        fail(f'Ano fora do range esperado [1750, 2030]: {year}')
    if doi:
        doi = re.sub(r'^(?:https?://)?(?:dx\.)?doi\.org/', '', doi).rstrip(' .,;)')
        if not re.match(r'^10\.\d{4,9}/\S+$', doi):
            fail(f'DOI inválido: {doi!r}')

    return {
        'author': author,
        'year': year,
        'title': title,
        'journal': journal,
        'doi': doi,
        'raw': raw or f'{author}. {year}. {title}.' + (f' {journal}.' if journal else ''),
    }


def handle_add_species(body, issue_number):
    sec = parse_issue_body(body)
    species = normalize_response(sec.get('Espécie (binomial completo)'))
    family = normalize_response(sec.get('Família'))

    if not species:
        fail('Campo "Espécie" vazio.')
    # validate binomial format
    parts = species.strip().split()
    if len(parts) != 2:
        fail(f'Espécie deve ter exatamente 2 palavras (Gênero epíteto). Recebido: {species!r}')
    genus, epithet = parts
    if not (genus[:1].isupper() and genus[1:].islower()):
        fail(f'Gênero deve começar com maiúscula e o resto minúsculo. Recebido: {genus!r}')
    if not epithet.islower():
        fail(f'Epíteto deve estar em minúsculas. Recebido: {epithet!r}')

    if not family:
        fail('Campo "Família" vazio.')
    if family not in VALID_FAMILIES:
        sug = ', '.join(sorted(VALID_FAMILIES))
        fail(f'Família `{family}` não é uma das 16 aceitas no banco. Lista: {sug}')

    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)

    # garante que ainda não existe
    existing, _ = find_species(data, species)
    if existing:
        fail(f'Esta espécie já existe no banco: `{existing["species"]}` ({existing["family"]}). '
             f'Para adicionar uma referência, use o template "📚 Adicionar referência".')

    # Constrói o objeto da espécie nova
    new_sp = {
        'id': slugify(species),
        'species': species,
        'genus': genus,
        'epithet': epithet,
        'tip_label': f'{genus}_{epithet}',
        'family': family,
        'ext_morph':      {'status': 'not_described', 'refs': []},
        'internal_oral':  {'status': 'not_described', 'refs': []},
        'chondrocranium': {'status': 'not_described', 'refs': []},
    }

    # Opcional: já registrar descrição larval no mesmo submit
    chars_selected = parse_selected_characters(
        sec.get('Caracteres larvais JÁ descritos na literatura'))
    new_ref = parse_reference_block(sec)
    if chars_selected and not new_ref:
        fail('Você marcou caracteres descritos mas não preencheu os campos da '
             'referência (autor, ano, título são obrigatórios).')
    if new_ref and not chars_selected:
        fail('Você forneceu uma referência mas não marcou nenhum caráter. '
             'Marque pelo menos um caráter descrito.')
    if chars_selected and new_ref:
        for ch in chars_selected:
            new_sp[ch]['status'] = 'described'
            new_sp[ch]['refs'] = [new_ref]

    # Insere ordenado por (família, espécie) — mesma ordem do builder original
    new_key = (family, species)
    insert_at = len(data['species'])
    for i, sp in enumerate(data['species']):
        if (sp['family'], sp['species']) > new_key:
            insert_at = i
            break
    data['species'].insert(insert_at, new_sp)
    data['count'] = len(data['species'])
    data['generated'] = date.today().isoformat()

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Summary pro PR body
    char_labels = {v: k for k, v in CHARACTER_MAP.items()}
    summary = [f'## Mudança aplicada (issue #{issue_number})\n']
    summary.append(f'- **Nova espécie:** *{species}* ({family})')
    summary.append(f'- **`id`:** `{new_sp["id"]}`')
    summary.append(f'- **`tip_label`:** `{new_sp["tip_label"]}`')
    summary.append(f'- **Posição no banco:** {insert_at + 1} de {len(data["species"])} (ordenada por família × espécie)')
    if chars_selected:
        summary.append(f'- **Caráter(es) descrito(s):** {", ".join(char_labels[c] for c in chars_selected)}')
        summary.append(f'- **Referência:** {new_ref["author"]} ({new_ref["year"]}) {new_ref["title"]}')
        if new_ref.get('doi'):
            summary.append(f'  - DOI: [{new_ref["doi"]}](https://doi.org/{new_ref["doi"]})')
    else:
        summary.append('- **Estado larval:** os 3 caracteres entram como `not_described` (girino ainda não descrito).')

    contributor = normalize_response(sec.get('Seu nome (para crédito no commit)'))
    if contributor:
        summary.append(f'\nContribuição: {contributor}')

    orig_doi = normalize_response(sec.get('DOI da descrição original da espécie (opcional)'))
    if orig_doi:
        summary.append(f'\nDescrição original da espécie (referência, não salva no JSON): https://doi.org/{orig_doi}')

    print('\n'.join(summary))


def handle_add_reference(body, issue_number):
    sec = parse_issue_body(body)
    species = normalize_response(sec.get('Espécie (binomial completo)'))
    if not species:
        fail('Campo "Espécie" vazio.')
    chars_field = normalize_response(sec.get('Caráter descrito nesta referência'))
    if not chars_field:
        fail('Campo "Caráter" vazio.')
    # checkboxes/multi-select vêm como "- [x] OPÇÃO" no markdown
    chars_selected = []
    for line in chars_field.splitlines():
        m = re.match(r'^\s*-\s*\[\s*[xX]\s*\]\s*(.+?)\s*$', line)
        if m:
            label = m.group(1)
            if label in CHARACTER_MAP:
                chars_selected.append(CHARACTER_MAP[label])
        else:
            # fallback: linha solta com o nome (dropdown single)
            s = line.strip()
            if s in CHARACTER_MAP:
                chars_selected.append(CHARACTER_MAP[s])
    chars_selected = list(dict.fromkeys(chars_selected))  # dedup, preserva ordem
    if not chars_selected:
        fail(f'Não consegui identificar o(s) caráter(es). Resposta crua:\n```\n{chars_field}\n```')

    author = normalize_response(sec.get('Autores da referência'))
    year_str = normalize_response(sec.get('Ano de publicação'))
    title = normalize_response(sec.get('Título do artigo'))
    journal = normalize_response(sec.get('Periódico'))
    doi = normalize_response(sec.get('DOI'))
    raw = normalize_response(sec.get('Citação completa (raw) — opcional'))
    contributor = normalize_response(sec.get('Seu nome (para crédito no commit)'))

    if not (author and title):
        fail('Campos `Autores` e `Título` são obrigatórios.')
    try:
        year = int(year_str)
    except (TypeError, ValueError):
        fail(f'Ano inválido: {year_str!r}')
    if year < 1750 or year > 2030:
        fail(f'Ano fora do range esperado [1750, 2030]: {year}')
    if doi:
        # normaliza DOI: remove prefixo se vier
        doi = re.sub(r'^(?:https?://)?(?:dx\.)?doi\.org/', '', doi).rstrip(' .,;)')
        if not re.match(r'^10\.\d{4,9}/\S+$', doi):
            fail(f'DOI inválido: {doi!r}')

    # carrega banco e acha espécie
    with open(JSON_PATH, encoding='utf-8') as f:
        data = json.load(f)
    sp, suggestions = find_species(data, species)
    if sp is None:
        sug = '\n'.join(f'  - `{s}`' for s in suggestions) or '_nenhuma sugestão_'
        fail(f'Espécie `{species}` não encontrada no banco. Você quis dizer:\n{sug}')

    # monta objeto ref no novo schema
    new_ref = {
        'author': author,
        'year': year,
        'title': title,
        'journal': journal,
        'doi': doi,
        'raw': raw or f'{author}. {year}. {title}.' + (f' {journal}.' if journal else ''),
    }

    # adiciona em cada caráter selecionado se ainda não estiver
    added_to = []
    already_in = []
    for ch in chars_selected:
        refs = sp[ch].setdefault('refs', [])
        # detecta duplicata: mesma DOI, ou mesmo (autor+ano+título)
        is_dup = False
        for r in refs:
            if not isinstance(r, dict): continue
            if doi and r.get('doi') == doi:
                is_dup = True; break
            if (r.get('year') == year and
                (r.get('title') or '').lower() == title.lower() and
                (r.get('author') or '').split(',')[0].lower() ==
                author.split(',')[0].lower()):
                is_dup = True; break
        if is_dup:
            already_in.append(ch)
        else:
            refs.append(new_ref)
            # garante status='described' quando havia 'not_described'
            if sp[ch].get('status') != 'described':
                sp[ch]['status'] = 'described'
            added_to.append(ch)

    if not added_to:
        fail(f'Esta referência já existe no banco para todos os caracteres '
             f'selecionados ({", ".join(already_in)}).')

    # atualiza meta
    data['generated'] = date.today().isoformat()

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # resumo (vai pro corpo do PR)
    char_labels = {v: k for k, v in CHARACTER_MAP.items()}
    summary = [f'## Mudança aplicada (issue #{issue_number})\n']
    summary.append(f'- **Espécie:** *{sp["species"]}* ({sp["family"]})')
    summary.append(f'- **Caráter(es):** {", ".join(char_labels[c] for c in added_to)}')
    if already_in:
        summary.append(f'- _Ignorado (já existia):_ {", ".join(char_labels[c] for c in already_in)}')
    summary.append(f'- **Autores:** {author}')
    summary.append(f'- **Ano:** {year}')
    summary.append(f'- **Título:** {title}')
    if journal: summary.append(f'- **Periódico:** {journal}')
    if doi:     summary.append(f'- **DOI:** [{doi}](https://doi.org/{doi})')
    summary.append('')
    if contributor:
        summary.append(f'Contribuição: {contributor}')
    print('\n'.join(summary))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--body-file', required=True)
    ap.add_argument('--labels', default='')
    ap.add_argument('--issue-number', type=int, required=True)
    args = ap.parse_args()

    with open(args.body_file, encoding='utf-8') as f:
        body = f.read()
    labels = [l.strip() for l in args.labels.split(',') if l.strip()]

    if 'add-reference' in labels:
        handle_add_reference(body, args.issue_number)
    elif 'add-species' in labels:
        handle_add_species(body, args.issue_number)
    else:
        print('::notice::Issue sem label de auto-PR (add-reference / add-species) — nada a fazer automaticamente.')
        sys.exit(0)


if __name__ == '__main__':
    main()
