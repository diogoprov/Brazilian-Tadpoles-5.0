/* Filogenia interativa — Brazilian Tadpoles 5.0
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
    const layout = d3.tree().nodeSize([NODE_H, NODE_W]);
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
      .text(d => mrcaLabel(d, /*forCollapsed*/ isCollapsed(d)));

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
      .text(d => pretty(d.data.name));

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

  // -------- Boot --------
  async function init() {
    if (initialized) return;
    initialized = true;
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
    } catch (err) {
      document.getElementById('phylo-container').innerHTML =
        `<p style="color:var(--err);padding:24px">Não foi possível carregar a filogenia (${err.message}). Rode via servidor local.</p>`;
    }
  }

  document.querySelectorAll('.tab').forEach(tab => {
    if (tab.dataset.view === 'filogenia') tab.addEventListener('click', init);
  });
})();
