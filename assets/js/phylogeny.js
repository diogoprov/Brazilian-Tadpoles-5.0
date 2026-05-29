/* Filogenia interativa — Brazilian Tadpoles 5.0
   Le assets/data/phylogeny.json (arvore podada) e assets/data/species.json
   (para metadados das pontas) e renderiza em D3 com colapsar/expandir clados. */

(function () {
  // Estado
  let tree = null;        // hierarquia D3
  let speciesByTip = {};  // tip_label -> sp data
  let unmatched = 0;      // contagem de spp sem tip
  let initialized = false;

  // Cores por nº de caracteres descritos (0..3)
  const CHAR_COLORS = ['#c0c4cc', '#e4b15c', '#8bbd61', '#2e6b4f'];

  const NODE_HEIGHT = 14;   // px por leaf
  const NODE_WIDTH = 130;   // px por nivel de profundidade
  const MARGIN = { top: 20, right: 220, bottom: 20, left: 20 };

  let svg, gRoot, tooltip;

  function countDescribed(sp) {
    if (!sp) return 0;
    return ['ext_morph', 'internal_oral', 'chondrocranium']
      .filter(c => sp[c] && sp[c].status === 'described').length;
  }

  function isLeaf(node) {
    return !(node.children && node.children.length) &&
           !(node._children && node._children.length);
  }

  function nLeavesVisible(node) {
    if (isLeaf(node)) return 1;
    let n = 0;
    if (node.children) {
      for (const c of node.children) n += nLeavesVisible(c);
    }
    return n || 1;
  }

  function nLeavesTotal(node) {
    if (!node.children && !node._children) return 1;
    let n = 0;
    const kids = node.children || node._children || [];
    for (const c of kids) n += nLeavesTotal(c);
    return n;
  }

  function collapseAll(node, depthLimit) {
    // Colapsa todos os internos abaixo de depthLimit
    if (node.depth >= depthLimit && node.children) {
      node._children = node.children;
      node.children = null;
    }
    const kids = node.children || node._children || [];
    for (const c of kids) collapseAll(c, depthLimit);
  }

  function expandAll(node) {
    if (node._children) {
      node.children = node._children;
      node._children = null;
    }
    if (node.children) for (const c of node.children) expandAll(c);
  }

  function fullyCollapse(node) {
    if (node.children) {
      node._children = node.children;
      node.children = null;
    }
    const kids = node._children || [];
    for (const c of kids) fullyCollapse(c);
  }

  function toggle(node) {
    if (node.children) {
      node._children = node.children;
      node.children = null;
    } else if (node._children) {
      node.children = node._children;
      node._children = null;
    }
    update();
  }

  // ------------- Render -------------
  function update() {
    const visibleLeaves = nLeavesVisible(tree);
    const width = NODE_WIDTH * (tree.height + 1) + MARGIN.left + MARGIN.right;
    const height = Math.max(600, NODE_HEIGHT * visibleLeaves + MARGIN.top + MARGIN.bottom);

    svg.attr('width', width).attr('height', height);

    // Layout dendrograma horizontal
    const layout = d3.tree()
      .size([height - MARGIN.top - MARGIN.bottom, width - MARGIN.left - MARGIN.right])
      .separation(() => 1);
    layout(tree);

    const all = tree.descendants();

    // -------- Links --------
    const linkGen = d3.linkHorizontal()
      .x(d => d.y)
      .y(d => d.x);

    const links = gRoot.selectAll('path.phylo-link')
      .data(tree.links(), d => nodeKey(d.target));

    links.exit().remove();

    links.enter()
      .append('path')
      .attr('class', 'phylo-link')
      .merge(links)
      .attr('d', linkGen);

    // -------- Internal nodes (circulos clicaveis) --------
    const internalData = all.filter(d => !isLeaf(d));

    const internals = gRoot.selectAll('g.phylo-internal')
      .data(internalData, nodeKey);

    internals.exit().remove();

    const internalsEnter = internals.enter()
      .append('g')
      .attr('class', 'phylo-internal');

    internalsEnter.append('circle').attr('r', 5);
    internalsEnter.append('text');

    const internalsMerged = internalsEnter.merge(internals)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    internalsMerged.select('circle')
      .attr('class', d => 'phylo-internal-circle' + (d._children ? ' collapsed' : ''))
      .on('click', (event, d) => { toggle(d); event.stopPropagation(); });

    internalsMerged.select('text')
      .attr('class', 'phylo-internal-count')
      .attr('x', 8)
      .attr('y', 3)
      .text(d => d._children ? `+${nLeavesTotal(d)}` : '');

    // -------- Leaves --------
    const leafData = all.filter(isLeaf);

    const leaves = gRoot.selectAll('g.phylo-leaf')
      .data(leafData, nodeKey);

    leaves.exit().remove();

    const leavesEnter = leaves.enter()
      .append('g')
      .attr('class', 'phylo-leaf');

    leavesEnter.append('circle')
      .attr('class', 'phylo-tip-circle')
      .attr('r', 4);

    leavesEnter.append('text')
      .attr('class', 'phylo-tip-text')
      .attr('x', 9)
      .attr('y', 0);

    const leavesMerged = leavesEnter.merge(leaves)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    leavesMerged.select('circle')
      .attr('fill', d => {
        const sp = speciesByTip[d.data.name];
        return CHAR_COLORS[countDescribed(sp)];
      })
      .on('mouseover', (event, d) => showTooltip(event, d))
      .on('mousemove', positionTooltip)
      .on('mouseout', hideTooltip);

    leavesMerged.select('text')
      .text(d => prettySpecies(d.data.name))
      .attr('class', d => 'phylo-tip-text' + (countDescribed(speciesByTip[d.data.name]) === 0 ? ' dim' : ''));
  }

  function nodeKey(d) {
    // Chave estavel pra d3 data join
    return d.data.name + '/' + d.depth + '/' + (d.parent ? d.parent.data.name : 'R');
  }

  function prettySpecies(tipLabel) {
    return (tipLabel || '').replace(/_/g, ' ');
  }

  // ------------- Tooltip -------------
  function showTooltip(event, d) {
    const sp = speciesByTip[d.data.name];
    if (!sp) {
      tooltip.innerHTML = `<strong>${prettySpecies(d.data.name)}</strong>
        <div class="tt-sub">não consta no banco</div>`;
    } else {
      const status = c => sp[c].status === 'described' ? '✓' : '—';
      tooltip.innerHTML = `<strong><em>${sp.species}</em></strong>
        <div class="tt-sub">${sp.family}</div>
        <div class="tt-sub" style="margin-top:6px">
          ${status('ext_morph')} Morf. externa<br>
          ${status('internal_oral')} Morf. oral<br>
          ${status('chondrocranium')} Condrocrânio
        </div>`;
    }
    tooltip.classList.add('visible');
    positionTooltip(event);
  }
  function positionTooltip(event) {
    const pad = 12;
    let x = event.clientX + pad;
    let y = event.clientY + pad;
    // Ajusta pra não estourar a viewport
    const r = tooltip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = event.clientX - r.width - pad;
    if (y + r.height > window.innerHeight - 8) y = event.clientY - r.height - pad;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  }
  function hideTooltip() {
    tooltip.classList.remove('visible');
  }

  // ------------- Boot -------------
  async function init() {
    if (initialized) return;
    initialized = true;
    try {
      const [phy, sp] = await Promise.all([
        fetch('assets/data/phylogeny.json', { cache: 'no-store' }).then(r => r.json()),
        fetch('assets/data/species.json', { cache: 'no-store' }).then(r => r.json()),
      ]);

      for (const s of sp.species) speciesByTip[s.tip_label] = s;
      unmatched = sp.species.length - phy.tip_count;

      document.getElementById('phylo-meta').textContent =
        `${phy.tip_count} pontas (espécies posicionadas) · árvore podada a partir de ${phy.source.split(' podada')[0]} · gerada em ${phy.generated}`;
      document.getElementById('phylo-unmatched-hint').textContent =
        unmatched > 0 ? `${unmatched} espécies do banco ainda sem posicionamento na megatree (em geral spp. descritas após a publicação da megatree).` : '';

      tree = d3.hierarchy(phy.tree);
      // Colapsa inicialmente até profundidade ~3 (mostra clados grandes)
      collapseAll(tree, 3);

      // Setup SVG
      const container = document.getElementById('phylo-container');
      tooltip = document.createElement('div');
      tooltip.className = 'phylo-tooltip';
      document.body.appendChild(tooltip);

      svg = d3.select(container).append('svg');
      gRoot = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

      update();

      document.getElementById('btn-expand-all').addEventListener('click', () => { expandAll(tree); update(); });
      document.getElementById('btn-collapse-all').addEventListener('click', () => {
        // Mantem a raiz expandida pra nao sumir tudo
        fullyCollapse(tree);
        if (tree._children) { tree.children = tree._children; tree._children = null; }
        update();
      });
    } catch (err) {
      document.getElementById('phylo-container').innerHTML =
        `<p style="color:var(--err);padding:24px">Não foi possível carregar a filogenia (${err.message}). Rode via servidor local.</p>`;
    }
  }

  // Lazy load: só inicializa quando o usuário clicar na aba
  document.querySelectorAll('.tab').forEach(tab => {
    if (tab.dataset.view === 'filogenia') {
      tab.addEventListener('click', init, { once: false });
    }
  });
})();
