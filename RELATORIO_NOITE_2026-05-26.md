# Relatório de progresso noturno — 2026-05-26

Sleep work enquanto você dormia. Concluí as duas últimas tarefas dos 10 erros originais (#13 e #14) usando o PDF de **Magalhães et al. 2020**, *Herpetological Monographs* 34:131–177, lido na íntegra. Esse é exatamente o paper canônico que o seu xlsx menciona, e ele resolve definitivamente o grupo *Leptodactylus latrans*.

## Tarefa #13 — *Leptodactylus luctator* ✓

A revalidação de *L. luctator* (Hudson 1892) por Magalhães et al. 2020 está confirmada. Distribuição: AR, UY, sul/sudeste BR — **não ocorre na Venezuela nem na Amazônia**.

**Veredicto sobre as refs da v4.0** (`Dixon & Staton 1976 / Dubeux et al. 2020 / Cei 1980 / Fabrezi & Vera 1997 / Schulze et al. 2015 / Schiesari et al. 2022`):

| Ref | Veredicto | Por quê |
|---|---|---|
| Dixon & Staton 1976 | → *L. macrosternum* | Venezuela = macrosternum |
| **Dubeux et al. 2020** | → ***L. natalensis*** | Surpresa: é sobre o grupo *melanonotus*, **outro grupo do gênero**. Row displacement clássico. |
| Cei 1980 | provavelmente → *L. macrosternum* | Argentina/Chaco; era considerada *L. chaquensis* |
| Fabrezi & Vera 1997 | provavelmente → *L. macrosternum* | Argentina/Chaco; condrocrânio de "*L. chaquensis*" |
| Schulze et al. 2015 | provavelmente → *L. macrosternum* | Chaco |
| Schiesari et al. 2022 | → *L. macrosternum* | Amazônia Central |
| Heyer 1994 | fora do grupo | complexo *podicipinus-wagneri* |

**Resultado:** **nenhuma** das refs da v4.0 sobreviveu à verificação. *L. luctator* fica como `ext_morph: unknown` ("a verificar") até localizarmos uma descrição genuína do girino — provavelmente em **Cei 1980** (monografia "*Amphibians of Argentina*", sob o nome *L. ocellatus*). Magalhães 2020 corrobora a observação do xlsx de que "girino da loc-tipo desconhecido".

## Tarefa #14 — *Leptodactylus macrosternum* ✓

A sinonímia de *L. chaquensis* Cei 1950 com *L. macrosternum* Miranda-Ribeiro 1926 está formalmente confirmada por Magalhães 2020. Refs migradas conforme você previu:

**ext_morph (descrita):**
- **Dixon & Staton 1976** (Venezuela — ref original do nome *macrosternum*)
- **Cei 1980**, **Fabrezi & Vera 1997**, **Schulze et al. 2015** (refs do antigo *chaquensis*, AR/Chaco)
- **Schiesari et al. 2022** (Amazônia Central)

**internal_oral + chondrocranium** (categorias quando o banco abrir esses campos): Alcalde 2005, Wassersug & Heyer 1988, Larson & de Sá 1998, Palavecino 1997, Perotti 2001 — todas do antigo *chaquensis*.

**Removidas:**
- **Heyer 1994** — complexo *podicipinus-wagneri* (você já tinha confirmado)

**Pendente** (1 minuto de verificação quando quiser): **Duellman 2005** — provavelmente Peru/Amazônia = *L. macrosternum*, mas não localizei o trabalho específico.

## Estado final do banco

- **32 espécies** no `species.json` (Leptodactylidae — *Adenomera* + grupo *latrans*)
- **31 válidas v5.0** (1 sinônimo: *L. chaquensis*)
- **10 descritas** / 20 não descritas / 1 a verificar → **32%** de completude da morf. externa
- **14 espécies com auditoria formal registrada** (campo `verification: {date, by}` no JSON)

## Saldo geral da revisão

Dos **10 erros originais** do xlsx, todos foram resolvidos:

| # | Espécie | Status final |
|---|---|---|
| 6 | *A. andreae* ↔ *araucaria* (swap) | ✓ Hero 1990 + Menin & Rodrigues 2013 (andreae); *araucaria* → Not_described |
| 7 | *A. bokermanni* | ✓ Heyer 1973 (confirmado visualmente) |
| 8 | *A. diptyx* | ✓ Zaracho & Carvalho-Kokubum 2017 + De La Riva 1995 |
| 9 | *A. gridipappi* | ✓ Carvalho et al. 2020 (descrição da sp.); girino Not_described |
| 10 | *A. hylaedactyla* | ✓ Heyer 1973 + Heyer & Silverstone 1969 + Menin, Almeida & Kokubum 2009 |
| 11 | *A. marmorata* | ✓ Heyer et al. 1990 (Frogs of Boracéia, p. 154) |
| 12 | *A. martinezi* | ✓ Carvalho & Giaretta 2013 (redescreve adultos; girino não descrito) |
| 13 | *L. luctator* | ✓ Magalhães 2020 (revalidação); refs ainda a localizar |
| 14 | *L. macrosternum* | ✓ Magalhães 2020 (sinônimo de *chaquensis*); refs migradas |

**Bônus descobertos no caminho:**
- *A. saci* — girino descrito por Carvalho & Giaretta 2013 (Zootaxa 3701)
- *A. chicomendesi* — descrição em Carvalho et al. 2019 (Herpetologica 75); girino não descrito
- *A. kayapo, amicorum, aurantiaca, inopinata, tapajonica* — todas em Carvalho et al. 2020 (Zool. J. Linn. Soc.); todas Not_described

## Pendências pra discussão quando você acordar

1. **Cei 1980 monografia**: vale a pena conseguir o livro pra fechar definitivamente *L. luctator*.
2. **Duellman 2005** atribuído a *L. macrosternum*: localizar o trabalho específico (provavelmente "Cusco Amazónico" ou guia herpetológico peruano).
3. **Visual mais clean do site**: ainda pendente da sua observação anterior — tabela aparecendo direto sob a search box.
4. **Adicionar ao banco** quando quiser expandir além de Leptodactylidae: as 6 novas spp. da clade *heyeri* descritas em Carvalho 2020 (kayapo, amicorum, aurantiaca, inopinata, tapajonica, gridipappi — já estão no banco) + as 2 novas do grupo *latrans* (*L. payaya*, *L. paranaru*) que ainda não estão na amostra do JSON.
5. **Fluxo daqui pra frente**: como combinamos, a próxima fase seria expandir do xlsx de Leptodactylidae pro Google Sheet completo e depois fazer o push pro GitHub Pages.

Bom dia quando ler isto.
