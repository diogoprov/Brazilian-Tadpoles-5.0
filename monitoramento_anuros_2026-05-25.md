# Monitoramento de novas espécies de anuros brasileiros
**Data da verificação:** 25 de maio de 2026
**Fontes:** AmphibiaWeb · AMNH Amphibian Species of the World 6.2 · SBH

---

## 1. Novas espécies brasileiras (Anura) — escopo da base

**Filtro aplicado:** a base "Brazilian Tadpoles" contém apenas espécies com girinos livre-natantes. **Brachycephaloidea (Brachycephalidae, Craugastoridae, Eleutherodactylidae, Strabomantidae) é excluída** por desenvolvimento direto.

Lista consolidada das duas fontes taxonômicas (AmphibiaWeb + AMNH ASW). Todas devem entrar no banco com status `Not_described` nas colunas de girino (External Morphology, Internal Oral Features, Chondrocranium) até verificação da literatura.

| Espécie | Família | Tipo de dado | Referência | Fonte |
|---|---|---|---|---|
| *Arcovomer ubatuba* | Microhylidae | Espécie nova (partição de *A. passarellii*) | Andrade et al. 2026, *Salamandra* 62: 77–96. DOI 10.5281/zenodo.20267179 | AmphibiaWeb + AMNH |
| *Arcovomer moqueca* | Microhylidae | Espécie nova (partição de *A. passarellii*) | Andrade et al. 2026, *Salamandra* 62: 77–96. DOI 10.5281/zenodo.20267179 | AmphibiaWeb + AMNH |
| *Phyllodytes gravata* | Hylidae | Espécie nova | dos Santos, Rodrigues & Dias 2026, *Eur. J. Taxon.* 1048: 62–83. DOI 10.5852/ejt.2026.1048.3235 | AmphibiaWeb + AMNH |
| *Ranitomeya ichapama* | Dendrobatidae | Espécie nova (Peru e Brasil) | Brown et al. 2026, *Zootaxa* 5793(1): 42–60. DOI 10.11646/zootaxa.5793.1.2 | AmphibiaWeb |
| *Ololygon paracatu* | Hylidae | Espécie nova | Carvalho et al. 2026, *Zootaxa* 5757(6): 522–542. DOI 10.11646/zootaxa.5757.6.x | AmphibiaWeb + AMNH |
| *Adenomera varcena* | Leptodactylidae | Espécie nova (Acre, BR + Equador/Peru) | Borburema et al. 2026, *Ichthyol. & Herpetol.* 114: 204–216 | AMNH |

**Total: 6 espécies novas** a adicionar ao banco.

### Excluídas do banco (desenvolvimento direto — apenas para auditoria)

| Espécie | Família | Referência |
|---|---|---|
| *Ischnocnema rubridactyla* | Brachycephalidae | Silva-Soares et al. 2026, *Zootaxa* 5768(4): 503–524 |
| *Pristimantis acuraua* | Craugastoridae | Mônico et al. 2026, *Zootaxa* 5810: 434–462 |

> Observação sobre DOI: o volume/fascículo de *Ololygon paracatu* (*Zootaxa* 5757) aparece truncado na fonte; o DOI completo deve ser confirmado antes da inserção.

---

## 2. Mudanças taxonômicas relevantes (AMNH ASW 6.2, 2026)

Entradas que adicionam comentários, alteram distribuição ou afetam espécies provavelmente já presentes no banco. Não criam novos registros, mas podem exigir atualização de notas/distribuição:

- **Comentários / distribuição – Bufonidae:** *Rhinella achavali, R. arenarum, R. diptycha, R. icterica* (Caseiro-Silva et al. 2026); *R. arenarum* — novo registro (Valente et al. 2026); *R. ornata* — comentário (22 abr 2026).
- **Comentários – Hylidae:** *Scinax x-signatus* (filogeografia, Nogueira et al. 2026); *Boana albomarginata, B. faber, Dendropsophus elegans, Scinax perereca, Phyllomedusa distincta* (comentários, 22 abr 2026); *Pseudis limellum* — primeiro registro no RS em 41 anos (Costa et al. 2026); *Dendropsophus anataliasiasi* — distribuição revisada (Rachid et al. 2025); *Trachycephalus typhonius, T. quadrangulum, T. macrotis* — registros ajustados (Mendoza-Henao et al. 2026).
- **Comentário – Hylodidae:** *Hylodes dactylocinus* (22 abr 2026).

*(Excluídos do escopo: *Luetkenotyphlus fredi* (Siphonopidae) — Gymnophiona; *Brachycephalus rotenbergae* (Brachycephalidae) — desenvolvimento direto.)*

---

## 3. SBH — NOVA LISTA OFICIAL PUBLICADA ⚠️

**Mudança importante desde a última verificação.** A SBH publicou uma nova lista de anfíbios do Brasil:

- **Organizadores:** Leandro O. Drummond, Diego J. Santana, Albertina P. Lima e Luís Felipe Toledo.
- **Base:** literatura revisada por pares até **março de 2026**.
- **Resultado:** remoção de **41 espécies** e adição de **104 táxons**.
- **Fauna nacional atual:** **1.251 espécies válidas** — **1.206 anuros**, 40 cecílias, 5 salamandras.
- PDF disponível na página ("Baixe aqui o PDF"); o link é gerado via JavaScript e não pôde ser extraído automaticamente. **Recomendo baixar o PDF manualmente** para reconciliação completa.

O banco Brazilian Tadpoles 5.0 contém ~991 espécies; a nova lista SBH registra 1.206 anuros. A diferença reflete tanto o escopo do banco (foco em girinos) quanto as adições recentes — uma reconciliação completa contra o PDF é necessária.

---

## 4. Ação necessária

| Item | Ação |
|---|---|
| 6 espécies novas (seção 1) | **Adicionar ao banco** com status `Not_described` em todas as colunas de girino |
| Mudanças taxonômicas (seção 2) | **Atualizar taxonomia/notas** das espécies já presentes; verificar se distribuições/sinonímias afetam registros existentes |
| Nova lista SBH (seção 3) | **Reconciliação prioritária:** baixar o PDF e cruzar os 1.206 anuros contra os ~991 do banco (41 removidos + 104 adicionados pela SBH) |

---

### Notas de execução
- Execução automática; nenhum download foi realizado (downloads exigem confirmação do usuário).
- AmphibiaWeb e AMNH foram lidas via navegador (renderização JavaScript). A tabela 2026 do AmphibiaWeb tinha 62 espécies no total, das quais 6 brasileiras (Anura). O log do AMNH ASW 6.2 (data da página: 25/05/2026) trouxe 17 entradas relacionadas ao Brasil em 2026.
- Filtro aplicado: apenas Anura do Brasil **com girinos livre-natantes**; Caudata, Gymnophiona e Brachycephaloidea (Brachycephalidae, Craugastoridae, Eleutherodactylidae, Strabomantidae) excluídos.
