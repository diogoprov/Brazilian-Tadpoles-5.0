# Brazilian Tadpoles 5.0

Banco de dados das descrições de girinos de anuros do Brasil. Site **estático** (HTML/CSS/JS puro) que consome dados em JSON e roda inteiramente no navegador — hospedado no **GitHub Pages**.

A versão 5.0 cobre **1.058 espécies** de anuros brasileiros com girino livre-natante, distribuídas em **16 famílias**, e rastreia, para cada espécie, três conjuntos de caracteres do girino:

- **Morfologia externa**
- **Morfologia oral interna**
- **Condrocrânio**

Cada caráter tem um status (`described` / `not_described`) e a lista das referências que o descreveram (autor, ano, periódico, DOI quando disponível).

## O site

Quatro abas:

- **Espécies** — busca por espécie/gênero/família, filtros por status dos três caracteres, e tabela ordenável.
- **Filogenia** — árvore podada da megatree de anfíbios (Jetz & Pyron) para as 727 espécies do banco presentes na megatree, renderizada em D3.js. Clados colapsáveis, MRCAs de família/gênero rotulados, e barras de completude por caráter agregadas em cada clado.
- **Dados faltantes** — dashboard em Plotly: completude por família, espécies por família, completude global.
- **Sobre** — descrição, citação (Provete et al. 2012, BibTeX copiável), mantenedor, link pro código.

## Estrutura do repositório

```
.
├── index.html                         # página única (4 abas)
├── assets/
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js                     # busca, filtros, tabela, dashboard Plotly
│   │   └── phylogeny.js               # viz D3.js da árvore podada
│   └── data/
│       ├── species.json               # 1.058 spp. servidas ao site
│       ├── phylogeny.json             # árvore podada (D3-friendly, aninhada)
│       └── phylogeny_unmatched.json   # spp do banco sem tip na megatree
├── data-raw/                          # fontes brutas (preservadas, não servidas)
│   ├── Brazilian tadpoles database 4.1.0.xlsx
│   ├── Leptodactylus_mapeamento_refs.xlsx
│   ├── filogenia_jessyca_newNames.tre
│   └── …
├── scripts/
│   ├── build_species_json.py          # xlsx → species.json
│   └── prune_phylogeny.py             # megatree → phylogeny.json
├── .github/workflows/
│   ├── pages.yml                      # deploy automático no GitHub Pages
│   └── regen-json.yml                 # regera species.json quando o xlsx muda
└── README.md
```

## Rodar localmente

O navegador bloqueia `fetch` de arquivos via `file://`, então use um servidor local:

```bash
cd "Site Brazilian Tadpoles 5.0.0"
python3 -m http.server 8000
```

Depois abra <http://localhost:8000> (pare com `Ctrl + C`).

## Regenerar os dados

Os JSONs servidos ao site são gerados a partir das fontes brutas em `data-raw/`. Os scripts são **idempotentes** — não dependem de estado externo, podem ser rodados a qualquer momento.

### `species.json`

```bash
pip install openpyxl
python3 scripts/build_species_json.py
```

Lê `data-raw/Brazilian tadpoles database 4.1.0.xlsx`, exclui automaticamente as famílias do clado **Brachycephaloidea** (Brachycephalidae, Caligophrynidae, Ceuthomantidae, Craugastoridae, Eleutherodactylidae, Neblinaphrynidae) e **Hemiphractidae** (rãs marsupiais), porque não têm girino livre-natante e ficam fora do escopo do banco.

### `phylogeny.json`

```bash
python3 scripts/prune_phylogeny.py
```

Lê `data-raw/filogenia_jessyca_newNames.tre` (megatree em Newick, ~5300 tips, formato `Genus_epithet`), poda para os tips do banco e exporta uma árvore JSON aninhada com agregados por clado (contagens totais e por caráter, MRCAs de família/gênero, conjunto de famílias por subárvore). Espécies do banco que não estão na megatree saem em `assets/data/phylogeny_unmatched.json`.

## Publicar no GitHub Pages

Primeira vez:

```bash
git init
git add .
git commit -m "Brazilian Tadpoles 5.0 — site estático"
git branch -M main
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

Depois, no GitHub: **Settings → Pages → Source: GitHub Actions** (não "Deploy from branch"). O workflow `pages.yml` roda automaticamente em cada push pro `main`. O site fica em `https://<usuario>.github.io/<repo>/`.

O workflow `regen-json.yml` regera o `species.json` automaticamente sempre que o xlsx em `data-raw/` é atualizado, e commita o resultado.

> Os dois workflows já estão fixos em Node 24 via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"`, antecipando a deprecação obrigatória do Node 20 nas GitHub Actions (forçada em 02/06/2026, removido em 16/09/2026).

## Esquema dos JSONs

### `species.json`

```jsonc
{
  "schema_version": "5.0.0",
  "source": "Brazilian tadpoles database v4.1.0 (Google Sheet)",
  "generated": "AAAA-MM-DD",
  "excluded_families": ["Brachycephalidae", "..."],
  "excluded_count": 1,
  "count": 1058,
  "characters": ["ext_morph", "internal_oral", "chondrocranium"],
  "species": [
    {
      "id": "boana_faber",
      "species": "Boana faber",
      "genus": "Boana",
      "epithet": "faber",
      "family": "Hylidae",
      "tip_label": "Boana_faber",
      "ext_morph":      { "status": "described",     "refs": ["Cei 1980. ...", "..."] },
      "internal_oral":  { "status": "not_described", "refs": [] },
      "chondrocranium": { "status": "not_described", "refs": [] }
    }
  ]
}
```

`tip_label` é a chave usada pra casar a espécie com o tip da megatree.

### `phylogeny.json`

Árvore aninhada em formato D3-friendly. Cada nó tem:

```jsonc
{
  "name": "...",                                // rótulo do tip (ou vazio em internos)
  "length": 0.0,                                // comprimento do ramo
  "counts": { "total": n, "ext": n, "oral": n, "cond": n },
  "mrca_family": "Hylidae",                     // só no nó mais alto de cada família monofilética
  "mrca_genus":  "Boana",                       // idem pra gênero
  "families": ["Hylidae", "Phyllomedusidae"],   // em nós internos não-MRCA
  "family":  "Hylidae",  "genus": "Boana",  "epithet": "faber",   // só em tips
  "children": [ ... ]
}
```

`counts` é cumulativo — em cada nó, indica quantas espécies daquela subárvore têm o caráter descrito. É o que alimenta as barras de completude da viz.

## Como citar

> Provete, D.B., Garey, M.V., da Silva, F.R. & Jordani, M.X. (2012). Knowledge gaps and bibliographical revision about descriptions of free-swimming anuran larvae from Brazil. *North-Western Journal of Zoology*, 8(2), 283–286.

## Mantenedor

Diogo Borges Provete — <dbprovete@gmail.com>

Para correções, referências faltantes ou descrições novas publicadas, abra uma [issue](https://github.com/diogoprov/Brazilian-Tadpoles-5.0/issues/new).
