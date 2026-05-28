# Brazilian Tadpoles 5.0

Banco de dados das descrições de girinos de anuros do Brasil. Site **estático** (HTML/CSS/JS puro) que consome dados em JSON e roda inteiramente no navegador — hospedado no **GitHub Pages**.

A versão 5.0 cobre **1.058 espécies de anuros brasileiros** com girino livre-natante, distribuídas em **16 famílias**, com o rastreamento de três conjuntos de caracteres do girino: **morfologia externa**, **morfologia oral interna** e **condrocrânio**.

## Estrutura do repositório

```
.
├── index.html                       # página única (Espécies, Dados faltantes, Sobre)
├── assets/
│   ├── css/style.css
│   ├── js/app.js                    # busca, filtros, tabela e dashboard (Plotly)
│   └── data/species.json            # 1.058 spp. servidas ao site
├── data-raw/                        # fontes brutas (preservadas, não servidas)
│   ├── Brazilian tadpoles database 4.1.0.xlsx
│   ├── Leptodactylus_mapeamento_refs.xlsx
│   ├── filogenia_jessyca_newNames.tre
│   └── …
├── scripts/
│   └── build_species_json.py        # gera species.json a partir do xlsx
├── .github/workflows/
│   ├── pages.yml                    # deploy automático no GitHub Pages
│   └── regen-json.yml               # regera species.json quando o xlsx muda
└── README.md
```

## Rodar localmente

O navegador bloqueia `fetch` de arquivos via `file://`, então use um servidor local:

```bash
cd "Site Brazilian Tadpoles 5.0.0"
python3 -m http.server 8000
```

Depois abra http://localhost:8000 (pare com `Ctrl + C`).

## Regenerar `species.json`

```bash
pip install openpyxl
python3 scripts/build_species_json.py
```

O script lê `data-raw/Brazilian tadpoles database 4.1.0.xlsx`, exclui automaticamente as famílias do clado **Brachycephaloidea** (Brachycephalidae, Caligophrynidae, Ceuthomantidae, Craugastoridae, Eleutherodactylidae, Neblinaphrynidae) e **Hemiphractidae** (rãs marsupiais) — espécies sem girino livre-natante — e regenera `assets/data/species.json`.

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

Depois, no GitHub:

1. **Settings → Pages → Source:** *GitHub Actions* (não "Deploy from branch").
2. O workflow `pages.yml` já está configurado e roda automaticamente em cada push pro `main`.
3. O site fica disponível em `https://<usuario>.github.io/<repo>/`.

O workflow `regen-json.yml` regera o `species.json` automaticamente sempre que o xlsx em `data-raw/` for atualizado, e commita o resultado no repositório.

## Esquema de `species.json`

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
      "family": "Hylidae",
      "ext_morph": {
        "status": "described",
        "refs": ["Cei 1980. ...", "..."]
      },
      "internal_oral":   { "status": "not_described", "refs": [] },
      "chondrocranium":  { "status": "not_described", "refs": [] }
    }
  ]
}
```

Cada caráter tem `status` (`described` ou `not_described`) e uma lista `refs` com as referências completas (autor, ano, periódico, DOI).
