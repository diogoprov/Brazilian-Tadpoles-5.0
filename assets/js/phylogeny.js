/* Filogenia interativa — The Rossa-Feres Tadpole Database (Brazilian Tadpoles 5.0.1)
   Le assets/data/phylogeny.json (arvore podada com MRCAs e counts pre-calculados)
   e renderiza em D3:
     - Layout COMPACTO via nodeSize() (canvas cresce sob demanda).
     - MRCAs de familia/genero etiquetados nos nos internos.
     - Barras empilhadas de completude (ext / oral / cond) por no, agregando
       descendentes em clados colapsados.
     - Inicia colapsado nas MRCAs de familia. */

(function () {
  // Cores por caracter
  const CHARS = [
    { key: 'ext',  label: 'Morf. externa', color: '#2e6b4f' },
    { key: 'oral', label: 'Morf. oral',    color: '#7aa44a' },
    { key: 'cond', label: 'Condrocrânio',  color: '#c9881e' },
  ];

  // Layout
  const NODE_H = 20;        // px por leaf (era 16; aumentado pra evitar colisão)
  const NODE_W = 60;        // px por nivel de profundidade
  const MARGIN = { top: 18, right: 28, bottom: 18, left: 18 };
  const LABEL_PAD = 14;     // espaço entre fim do nome e início das barras
  const CHAR_PX = 6.3;      // estimativa de largura média de char (italic 11px)
  const MAX_LABEL_CHARS = 38; // truncamento em ... para clados muito largos
  const BAR_W = 18, BAR_GAP = 2, BAR_H = 10;
  const BAR_BLOCK_W = CHARS.length * BAR_W + (CHARS.length - 1) * BAR_GAP;

  let tree, svg, gRoot, tooltip;
  let initialized = false;
  let _initPromise = null;
  const HIGHLIGHT_MS = 2400;

  // -------- Helpers --------
  function isLeaf(d) {
    return !(d.children && d.children.length) &&
           !(d._children && d._children.length);
  }
  function isCollapsed(d) {
    return d._children && !d.children;
  }

  function collapseToFamilies(node) {
    // Colapsa cada no com mrca_family (nivel familia). Nao recurse abaixo.
    if (node.data.mrca_family) {
      if (node.children) {
        node._children = node.children;
        node.children = null;
      }
      return;
    }
    if (node.children) {
      for (const c of node.children) collapseToFamilies(c);
    }
  }

  function fullyCollapse(node) {
    if (node.children) { node._children = node.children; node.children = null; }
    (node._children || []).forEach(fullyCollapse);
  }
  function expandAll(node) {
    if (node._children) { node.children = node._children; node._children = null; }
    (node.children || []).forEach(expandAll);
  }
  function toggle(d) {
    if (d.children) { d._children = d.children; d.children = null; }
    else if (d._children) { d.children = d._children; d._children = null; }
    update();
  }

  // -------- Layout / render --------
  function update() {
    // d3.cluster (dendrograma) em vez de d3.tree: alinha TODAS as folhas no
    // mesmo x (profundidade max), o que mantém os rótulos colados nas barras
    // mesmo com clados colapsados em profundidades diferentes. Espaçamento
    // vertical fica uniforme (NODE_H por folha), sem clumping cousin/cousin.
    const layout = d3.cluster().nodeSize([NODE_H, NODE_W]);
    layout(tree);

    let xMin = Infinity, xMax = -Infinity, yMax = 0;
    let maxLabelW = 0;
    tree.each(d => {
      if (d.x < xMin) xMin = d.x;
      if (d.x > xMax) xMax = d.x;
      if (d.y > yMax) yMax = d.y;
      // Largura estimada do texto da ponta ou do label MRCA (com offset do círculo)
      if (isLeaf(d)) {
        const w = pretty(d.data.name).length * CHAR_PX + 9;
        if (w > maxLabelW) maxLabelW = w;
      } else if (isCollapsed(d)) {
        const w = mrcaLabel(d, true).length * CHAR_PX + 12;
        if (w > maxLabelW) maxLabelW = w;
      }
    });

    const barStartX = yMax + maxLabelW + LABEL_PAD;
    const width  = barStartX + BAR_BLOCK_W + 70 /* n= label */ + MARGIN.left + MARGIN.right;
    const height = (xMax - xMin) + NODE_H + MARGIN.top + MARGIN.bottom;

    svg.attr('width', width).attr('height', height);
    gRoot.attr('transform', `translate(${MARGIN.left}, ${MARGIN.top - xMin})`);

    // ===== Links =====
    const linkGen = d3.linkHorizontal().x(d => d.y).y(d => d.x);
    const links = gRoot.selectAll('path.phylo-link').data(tree.links(), d => key(d.target));
    links.exit().remove();
    links.enter().append('path').attr('class', 'phylo-link')
      .merge(links).attr('d', linkGen);

    // ===== Internal nodes (clickable circles + MRCA label) =====
    const internalData = tree.descendants().filter(d => !isLeaf(d));
    const internals = gRoot.selectAll('g.phylo-internal').data(internalData, key);
    internals.exit().remove();
    const ent = internals.enter().append('g').attr('class', 'phylo-internal');
    ent.append('circle');
    ent.append('text').attr('class', 'phylo-mrca-label');
    const merged = ent.merge(internals).attr('transform', d => `translate(${d.y},${d.x})`);
    merged.select('circle')
      .attr('r', d => isCollapsed(d) ? 5.5 : 3.5)
      .attr('class', d => 'phylo-internal-circle' + (isCollapsed(d) ? ' collapsed' : ''))
      .on('click', (e, d) => { toggle(d); e.stopPropagation(); })
      .on('mouseover', (e, d) => showTooltip(e, d))
      .on('mousemove', positionTooltip)
      .on('mouseout', hideTooltip);
    merged.select('text.phylo-mrca-label')
      .attr('x', d => isCollapsed(d) ? 10 : -6)
      .attr('y', d => isCollapsed(d) ? 4 : -4)
      .attr('text-anchor', d => isCollapsed(d) ? 'start' : 'end')
      .text(d => mrcaLabel(d, /*forCollapsed*/ isCollapsed(d)))
      .classed('clickable', d => isCollapsed(d) && (d.data.mrca_family || d.data.mrca_genus))
      .on('click', (e, d) => {
        // Só dispara filtro pra MRCAs monofiléticos (family ou genus singleton)
        if (!(isCollapsed(d) && (d.data.mrca_family || d.data.mrca_genus))) return;
        const tgt = d.data.mrca_genus
          ? { genus: d.data.mrca_genus }
          : { family: d.data.mrca_family };
        if (window.SpeciesView) window.SpeciesView.filterBy(tgt);
        e.stopPropagation();
      });

    // ===== Tips (leaves) =====
    const leafData = tree.descendants().filter(isLeaf);
    const leaves = gRoot.selectAll('g.phylo-leaf').data(leafData, key);
    leaves.exit().remove();
    const lent = leaves.enter().append('g').attr('class', 'phylo-leaf');
    lent.append('circle').attr('class', 'phylo-tip-circle').attr('r', 3);
    lent.append('text').attr('class', 'phylo-tip-text').attr('x', 7);
    const lmerged = lent.merge(leaves).attr('transform', d => `translate(${d.y},${d.x})`);
    lmerged.select('circle')
      .attr('fill', d => tipColor(d))
      .on('mouseover', (e, d) => showTooltip(e, d))
      .on('mousemove', positionTooltip)
      .on('mouseout', hideTooltip);
    lmerged.select('text')
      .text(d => pretty(d.data.name))
      .classed('clickable', true)
      .on('click', (e, d) => {
        if (window.SpeciesView) window.SpeciesView.filterBy({ species: pretty(d.data.name) });
        e.stopPropagation();
      });

    // ===== Barras empilhadas por no (tips + colapsados) =====
    const barredData = tree.descendants().filter(d => isLeaf(d) || isCollapsed(d));
    const bars = gRoot.selectAll('g.phylo-bars').data(barredData, key);
    bars.exit().remove();
    const bent = bars.enter().append('g').attr('class', 'phylo-bars');
    bent.append('text').attr('class', 'phylo-bar-n');
    // CHARS.length pares de retangulos (bg + fg)
    CHARS.forEach((_, i) => {
      bent.append('rect').attr('class', `bar-bg bar-bg-${i}`);
      bent.append('rect').attr('class', `bar-fg bar-fg-${i}`);
    });
    const bmerged = bent.merge(bars).attr('transform', d => `translate(${barStartX}, ${d.x})`);
    CHARS.forEach((ch, i) => {
      const x = i * (BAR_W + BAR_GAP);
      bmerged.select(`rect.bar-bg-${i}`)
        .attr('x', x).attr('y', -BAR_H / 2)
        .attr('width', BAR_W).attr('height', BAR_H)
        .attr('rx', 1).attr('fill', '#e8eae3');
      bmerged.select(`rect.bar-fg-${i}`)
        .attr('x', x).attr('y', -BAR_H / 2)
        .attr('height', BAR_H).attr('rx', 1).attr('fill', ch.color)
        .attr('width', d => {
          const c = d.data.counts;
          if (!c || !c.total) return 0;
          return BAR_W * (c[ch.key] / c.total);
        });
    });
    bmerged.select('text.phylo-bar-n')
      .attr('x', BAR_BLOCK_W + 8).attr('y', 3)
      .text(d => {
        const n = d.data.counts.total;
        // Esconde o label em tips (sempre n=1) — fica visual mais limpo
        return n > 1 ? `n=${n}` : '';
      });
  }

  function key(d) {
    return d.data.name + '|' + (d.parent ? d.parent.data.name : 'R') + '|' + d.depth;
  }

  function familiesLabel(fams) {
    if (!fams || !fams.length) return 'clado';
    if (fams.length === 1) return fams[0];
    if (fams.length <= 3) return fams.join(' + ');
    return `${fams.slice(0, 2).join(' + ')} + ${fams.length - 2} outras`;
  }

  function truncate(s, max) {
    if (s.length <= max) return s;
    return s.slice(0, max - 1).trimEnd() + '…';
  }

  function mrcaLabel(d, forCollapsed) {
    const data = d.data;
    const total = data.counts ? data.counts.total : 0;
    if (forCollapsed) {
      // ordem de preferencia: gênero MRCA > família MRCA > lista de famílias aninhadas
      let name;
      if (data.mrca_genus) name = data.mrca_genus;
      else if (data.mrca_family) name = data.mrca_family;
      else name = familiesLabel(data.families);
      // reserva espaço pro sufixo "(+N)" no truncamento
      const suffix = ` (+${total})`;
      return truncate(name, MAX_LABEL_CHARS - suffix.length) + suffix;
    }
    // Nós internos EXPANDIDOS: sem label persistente (a topologia ja mostra a
    // estrutura). Detalhes via tooltip ao passar o mouse no círculo cinza.
    return '';
  }

  function pretty(s) { return (s || '').replace(/_/g, ' '); }

  function tipColor(d) {
    const c = d.data.counts || {};
    const n = (c.ext || 0) + (c.oral || 0) + (c.cond || 0);
    return ['#c0c4cc', '#e4b15c', '#8bbd61', '#2e6b4f'][n];
  }

  // -------- Tooltip --------
  function showTooltip(e, d) {
    const data = d.data;
    const c = data.counts || {};
    const pct = k => c.total ? Math.round(100 * (c[k] || 0) / c.total) : 0;
    let title;
    if (isLeaf(d)) {
      title = `<strong><em>${pretty(data.name)}</em></strong>`;
      if (data.family) title += `<div class="tt-sub">${data.family}</div>`;
    } else {
      const lbl = data.mrca_genus || data.mrca_family || 'Clado';
      title = `<strong>${lbl}</strong><div class="tt-sub">${c.total} espécies${isCollapsed(d) ? ' (colapsadas)' : ''}</div>`;
    }
    const bars = CHARS.map(ch => {
      const v = c[ch.key] || 0;
      return `<div class="tt-bar-row">
        <span class="tt-swatch" style="background:${ch.color}"></span>
        ${ch.label}: <strong>${v}/${c.total || 0}</strong> (${pct(ch.key)}%)
      </div>`;
    }).join('');
    tooltip.innerHTML = title + `<div class="tt-bars">${bars}</div>`;
    tooltip.classList.add('visible');
    positionTooltip(e);
  }
  function positionTooltip(e) {
    const pad = 12;
    const r = tooltip.getBoundingClientRect();
    let x = e.clientX + pad, y = e.clientY + pad;
    if (x + r.width > window.innerWidth - 8) x = e.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = e.clientY - r.height - pad;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  }
  function hideTooltip() { tooltip.classList.remove('visible'); }

  // -------- Cross-filter: focar um clado/espécie --------
  // Caminha pela árvore inteira, INCLUSIVE os filhos colapsados (_children),
  // pra achar tips que estão "escondidos" dentro de uma MRCA colapsada.
  function walkAll(d, out) {
    out.push(d);
    (d.children || []).forEach(c => walkAll(c, out));
    (d._children || []).forEach(c => walkAll(c, out));
  }

  function expandAncestors(d) {
    let cur = d.parent;
    while (cur) {
      if (cur._children && !cur.children) { cur.children = cur._children; cur._children = null; }
      cur = cur.parent;
    }
  }

  function collapseSubtree(d) {
    // Mantém o nó como colapsado pra que o label MRCA fique visível
    if (d.children) { d._children = d.children; d.children = null; }
  }

  async function focus(target) {
    await ensureInit();
    if (!tree) return false;

    const all = [];
    walkAll(tree, all);

    let found = null;
    let needCollapse = false; // true pra MRCAs (queremos ver o label do clado)

    if (target.species) {
      const sp = target.species.toLowerCase();
      found = all.find(d => !(d.children || d._children) &&
                            pretty(d.data.name).toLowerCase() === sp);
    } else if (target.genus) {
      found = all.find(d => d.data.mrca_genus === target.genus);
      needCollapse = true;
    } else if (target.family) {
      found = all.find(d => d.data.mrca_family === target.family);
      needCollapse = true;
    }

    if (!found) return false;

    expandAncestors(found);
    if (needCollapse) collapseSubtree(found);

    update();

    // Acha o elemento DOM correspondente e aplica highlight + scroll
    const k = key(found);
    const allG = gRoot.selectAll('g.phylo-leaf, g.phylo-internal').nodes();
    const gNode = allG.find(g => g.__data__ && key(g.__data__) === k);
    if (gNode) {
      gNode.classList.add('phylo-highlight');
      setTimeout(() => gNode.classList.remove('phylo-highlight'), HIGHLIGHT_MS);

      // Centra na viewport do container — usa requestAnimationFrame pra esperar
      // o DOM acomodar o resize do SVG após update()
      requestAnimationFrame(() => {
        const cont = document.getElementById('phylo-container');
        if (!cont) return;
        const cRect = cont.getBoundingClientRect();
        const gRect = gNode.getBoundingClientRect();
        const dx = (gRect.left - cRect.left) - (cont.clientWidth - gRect.width) / 2;
        const dy = (gRect.top  - cRect.top)  - (cont.clientHeight - gRect.height) / 2;
        cont.scrollTo({
          left: cont.scrollLeft + dx,
          top:  cont.scrollTop + dy,
          behavior: 'smooth'
        });
      });
    }
    return true;
  }

  function ensureInit() {
    if (!_initPromise) _initPromise = init();
    return _initPromise;
  }

  // -------- Boot --------
  async function init() {
    if (initialized) return;
    try {
      const phy = await fetch('assets/data/phylogeny.json', { cache: 'no-store' }).then(r => r.json());
      document.getElementById('phylo-meta').textContent =
        `${phy.tip_count} pontas (espécies posicionadas) · gerada em ${phy.generated}`;
      const sp = await fetch('assets/data/species.json', { cache: 'no-store' }).then(r => r.json());
      const unmatched = sp.species.length - phy.tip_count;
      document.getElementById('phylo-unmatched-hint').textContent =
        unmatched > 0 ? `${unmatched} espécies do banco ainda sem posicionamento na megatree (em geral spp. descritas após a publicação dela).` : '';

      tree = d3.hierarchy(phy.tree);
      collapseToFamilies(tree);

      const container = document.getElementById('phylo-container');
      tooltip = document.createElement('div');
      tooltip.className = 'phylo-tooltip';
      document.body.appendChild(tooltip);
      svg = d3.select(container).append('svg');
      gRoot = svg.append('g');

      update();

      document.getElementById('btn-expand-all').addEventListener('click', () => { expandAll(tree); update(); });
      document.getElementById('btn-collapse-all').addEventListener('click', () => {
        fullyCollapse(tree);
        if (tree._children) { tree.children = tree._children; tree._children = null; }
        update();
      });
      initialized = true;
    } catch (err) {
      document.getElementById('phylo-container').innerHTML =
        `<p style="color:var(--err);padding:24px">Não foi possível carregar a filogenia (${err.message}). Rode via servidor local.</p>`;
      throw err;
    }
  }

  document.querySelectorAll('.tab').forEach(tab => {
    if (tab.dataset.view === 'filogenia') tab.addEventListener('click', () => { ensureInit(); });
  });

  // API pública pra cross-filter com a aba Espécies
  window.PhyloView = { ensureInit, focus };
})();
