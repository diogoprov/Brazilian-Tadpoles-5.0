/* The Rossa-Feres Tadpole Database (Brazilian Tadpoles 5.0.1) — Aba Colaborações.
   Carrega assets/data/coauthor_network.json (gerado por
   scripts/build_coauthor_network.py) e renderiza a rede com Cytoscape.js.
   Painel lateral mostra top-N por métrica + detalhes do nó selecionado. */

(function () {
  const COA = {
    data: null,     // payload do JSON
    cy:   null,     // instância Cytoscape
    metric: 'papers',
    minPapers: 2,
    initialized: false,
  };

  // 12 cores de comunidade (cíclico). Outras comunidades reusam.
  const COMM_COLORS = [
    '#2e6b4f','#c9881e','#3b6fa1','#9c3d75','#7aa44a','#b53c3c',
    '#5d4a8a','#1f8a8a','#a86b2a','#54607a','#75ad6f','#c4663d',
  ];
  const NEUTRAL = '#a0a8ae';

  function commColor(c) {
    return c >= 0 ? COMM_COLORS[c % COMM_COLORS.length] : NEUTRAL;
  }

  function escapeText(s) {
    return String(s ?? '').replace(/[&<>"]/g,
      c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  async function loadData() {
    const res = await fetch('assets/data/coauthor_network.json',
      { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  // Aplica o filtro de mín. papers, retorna {nodes, edges} pro Cytoscape.
  function applyFilter() {
    const min = COA.minPapers;
    const keptIds = new Set(
      COA.data.nodes.filter(n => (n.data.papers || 0) >= min)
                    .map(n => n.data.id));
    const nodes = COA.data.nodes
      .filter(n => keptIds.has(n.data.id))
      .map(n => ({ data: { ...n.data, _color: commColor(n.data.community) } }));
    const edges = COA.data.edges.filter(e =>
      keptIds.has(e.data.source) && keptIds.has(e.data.target));
    return { nodes, edges };
  }

  // Mapeia valor da métrica para tamanho do nó (px), escala raiz para
  // suavizar a longa cauda.
  function sizeFn(metric, value) {
    const v = Number(value) || 0;
    if (metric === 'papers' || metric === 'degree') {
      return 8 + 4 * Math.sqrt(v);   // 1=12, 4=16, 16=24, 36=32...
    }
    // métricas em [0,1]: escala logarítmica
    return 8 + 32 * Math.sqrt(Math.min(1, v));
  }

  function rebuildGraph() {
    const els = applyFilter();
    const m = COA.metric;
    // estiliza size por métrica corrente
    els.nodes.forEach(n => {
      n.data._size = sizeFn(m, n.data[m]);
    });

    if (COA.cy) COA.cy.destroy();

    COA.cy = cytoscape({
      container: document.getElementById('coa-graph'),
      elements: { nodes: els.nodes, edges: els.edges },
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(_color)',
            'width': 'data(_size)',
            'height': 'data(_size)',
            'border-width': 0.5,
            'border-color': '#fff',
            'label': 'data(name)',
            'font-size': 7,
            'font-family': 'system-ui, sans-serif',
            'color': '#1f2421',
            'text-valign': 'center',
            'text-halign': 'right',
            'text-margin-x': 3,
            'text-opacity': 0,   // labels só aparecem no hover/selecionado
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 2,
            'border-color': '#1f4a36',
            'text-opacity': 1,
            'font-size': 10,
            'font-weight': 700,
          }
        },
        {
          selector: 'node.highlight',
          style: {
            'border-width': 2,
            'border-color': '#c9881e',
            'text-opacity': 1,
            'font-size': 9,
          }
        },
        {
          selector: 'node.dim',
          style: {
            'opacity': 0.15,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(weight, 1, 10, 0.4, 3)',
            'line-color': '#b9c1bf',
            'opacity': 0.55,
            'curve-style': 'haystack',
            'haystack-radius': 0.4,
          }
        },
        {
          selector: 'edge.dim',  style: { 'opacity': 0.05 }
        },
        {
          selector: 'edge.highlight',
          style: { 'line-color': '#c9881e', 'opacity': 0.85, 'width': 2 }
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        randomize: true,
        nodeRepulsion: 6000,
        idealEdgeLength: 60,
        edgeElasticity: 100,
        gravity: 0.4,
        numIter: 1500,
        fit: true,
        padding: 30,
      },
      wheelSensitivity: 0.25,
      minZoom: 0.1,
      maxZoom: 4,
    });

    // Hover: mostra label do nó e destaca vizinhança
    COA.cy.on('mouseover', 'node', e => {
      const n = e.target;
      n.addClass('highlight');
      n.neighborhood('node').addClass('highlight');
      n.connectedEdges().addClass('highlight');
    });
    COA.cy.on('mouseout', 'node', e => {
      const n = e.target;
      n.removeClass('highlight');
      n.neighborhood('node').removeClass('highlight');
      n.connectedEdges().removeClass('highlight');
    });

    COA.cy.on('tap', 'node', e => showDetail(e.target.data()));
    COA.cy.on('tap', e => {
      if (e.target === COA.cy) hideDetail();
    });

    // Atualiza linha de status
    document.getElementById('coa-stats').textContent =
      `${els.nodes.length} autores · ${els.edges.length} arestas`;
  }

  function showDetail(d) {
    const body = document.getElementById('coa-detail-body');
    const lines = [
      `<div class="da-name">${escapeText(d.name)}</div>`,
      `<div class="da-metric"><span>Papers no banco</span><span>${d.papers}</span></div>`,
      `<div class="da-metric"><span>Degree (coautores)</span><span>${d.degree}</span></div>`,
      `<div class="da-metric"><span>Betweenness</span><span>${d.betweenness.toFixed(4)}</span></div>`,
      `<div class="da-metric"><span>Eigenvector</span><span>${d.eigenvector.toFixed(4)}</span></div>`,
      `<div class="da-metric"><span>PageRank</span><span>${d.pagerank.toFixed(4)}</span></div>`,
      `<div class="da-metric"><span>Comunidade</span><span>#${d.community}</span></div>`,
    ];
    body.innerHTML = lines.join('');
    document.getElementById('coa-detail').hidden = false;
  }
  function hideDetail() {
    document.getElementById('coa-detail').hidden = true;
  }

  function renderTopList(metric) {
    const list = document.getElementById('coa-top-list');
    const top = [...COA.data.nodes]
      .sort((a, b) => (b.data[metric] || 0) - (a.data[metric] || 0))
      .slice(0, 10);
    list.innerHTML = top.map(n => {
      const v = n.data[metric];
      const valStr = (metric === 'papers' || metric === 'degree')
        ? v : (typeof v === 'number' ? v.toFixed(4) : v);
      return `<li data-id="${escapeText(n.data.id)}">${escapeText(n.data.name)}<span class="val">${valStr}</span></li>`;
    }).join('');
    // click no top → seleciona no grafo
    list.querySelectorAll('li').forEach(li => {
      li.addEventListener('click', () => focusNode(li.dataset.id));
    });
  }

  function focusNode(id) {
    if (!COA.cy) return;
    const n = COA.cy.$id(id);
    if (!n || n.empty()) return;
    COA.cy.elements().unselect();
    n.select();
    COA.cy.animate({ center: { eles: n }, zoom: 1.6 }, { duration: 400 });
    showDetail(n.data());
  }

  function setupEvents() {
    document.getElementById('coa-metric').addEventListener('change', e => {
      COA.metric = e.target.value;
      rebuildGraph();
    });
    document.getElementById('coa-minpapers').addEventListener('change', e => {
      COA.minPapers = Math.max(1, parseInt(e.target.value, 10) || 1);
      rebuildGraph();
    });
    document.getElementById('coa-reset').addEventListener('click', () => {
      if (COA.cy) COA.cy.fit(null, 30);
    });
    document.getElementById('coa-top-metric').addEventListener('change', e => {
      renderTopList(e.target.value);
    });
    document.getElementById('coa-search').addEventListener('input', e => {
      const q = e.target.value.trim().toLowerCase();
      if (!COA.cy) return;
      if (!q) {
        COA.cy.elements().removeClass('dim').removeClass('highlight');
        return;
      }
      const match = COA.cy.nodes().filter(n =>
        n.data('name').toLowerCase().includes(q));
      COA.cy.elements().addClass('dim');
      match.removeClass('dim').addClass('highlight');
      match.neighborhood('node').removeClass('dim');
      match.connectedEdges().removeClass('dim');
      if (match.length === 1) focusNode(match[0].id());
    });
  }

  async function init() {
    if (COA.initialized) return;
    COA.initialized = true;
    if (!window.cytoscape) {
      document.getElementById('coa-graph').innerHTML =
        '<p style="padding:20px;color:#c0392b">Falha ao carregar Cytoscape.js. Verifique a conexão.</p>';
      return;
    }
    try {
      COA.data = await loadData();
      document.getElementById('coa-n-refs').textContent =
        `${COA.data.n_nodes} autores e ${COA.data.n_edges} arestas (${COA.data.n_communities} comunidades, Louvain)`;
      rebuildGraph();
      renderTopList('papers');
      setupEvents();
    } catch (err) {
      document.getElementById('coa-graph').innerHTML =
        `<p style="padding:20px;color:#c0392b">Não foi possível carregar a rede: ${escapeText(err.message)}. Rode <code>python3 scripts/build_coauthor_network.py</code> primeiro.</p>`;
    }
  }

  // Inicialização preguiçosa: só monta quando a aba for ativada
  document.addEventListener('DOMContentLoaded', () => {
    const tab = document.querySelector('.tab[data-view="colaboracoes"]');
    if (tab) tab.addEventListener('click', () => setTimeout(init, 50));
    // se a hash ou estado inicial já é colaborações, monta na hora
    if (document.querySelector('#view-colaboracoes.is-active')) init();
  });
})();
