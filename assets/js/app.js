/* Brazilian Tadpoles 5.0
   Carrega species.json, monta UI clean (search central + tabela sob demanda)
   e dashboard de completude para os 3 caracteres (ext_morph, internal_oral, chondrocranium). */

const CHAR_LABELS = {
  ext_morph: 'Morf. externa',
  internal_oral: 'Morf. oral',
  chondrocranium: 'Condrocrânio',
};
const STATUS_LABELS = {
  described: 'Descrita',
  not_described: 'Não descrita',
};
const COLORS = {
  described: '#4caf50',
  not_described: '#c0c4cc',
  accent: '#2e6b4f',
};

let DATA = [];
let view = [];
let sortKey = 'species';
let sortDir = 1;
let tableVisible = false;

// ---------- Carregamento ----------
async function load() {
  try {
    const res = await fetch('assets/data/species.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    DATA = json.species || [];
    document.getElementById('about-meta').textContent =
      `Esquema ${json.schema_version} · gerado em ${json.generated} · ${json.count} espécies · ` +
      `excluídas ${json.excluded_count} sp. das famílias sem girino livre-natante · fonte: ${json.source}`;
    populateFilters();
    renderSummary();
    buildDashboard();
  } catch (err) {
    document.getElementById('hero-hint').innerHTML =
      `<span style="color:var(--err)">Não foi possível carregar os dados (${esc(err.message)}). ` +
      `Se você abriu o arquivo direto (file://), rode um servidor local — veja o README.</span>`;
  }
}

// ---------- Summary cards (primeira tela) ----------
function renderSummary() {
  const fams = new Set(DATA.map(d => d.family)).size;
  const desc = c => DATA.filter(d => d[c].status === 'described').length;
  const pct = c => Math.round(desc(c) / DATA.length * 100);
  document.getElementById('summary-cards').innerHTML = [
    card(DATA.length, 'espécies no banco'),
    card(fams, 'famílias'),
    card(pct('ext_morph') + '%', 'com morf. externa descrita',
         `${desc('ext_morph')} de ${DATA.length}`),
    card(pct('internal_oral') + '%', 'com morf. oral descrita',
         `${desc('internal_oral')} de ${DATA.length}`),
    card(pct('chondrocranium') + '%', 'com condrocrânio descrito',
         `${desc('chondrocranium')} de ${DATA.length}`),
  ].join('');
}

function card(num, lbl, sub) {
  return `<div class="card">
    <div class="num">${num}</div>
    <div class="lbl">${lbl}</div>
    ${sub ? `<div class="sub muted">${esc(sub)}</div>` : ''}
  </div>`;
}

// ---------- Filtros / tabela ----------
function uniqueSorted(key) {
  return [...new Set(DATA.map(d => d[key]).filter(Boolean))].sort();
}
function populateFilters() {
  const famSel = document.getElementById('filter-family');
  const genSel = document.getElementById('filter-genus');
  uniqueSorted('family').forEach(f => famSel.add(new Option(f, f)));
  uniqueSorted('genus').forEach(g => genSel.add(new Option(g, g)));
}

function showTable() {
  if (tableVisible) return;
  tableVisible = true;
  document.getElementById('table-block').hidden = false;
}
function hideTable() {
  tableVisible = false;
  document.getElementById('table-block').hidden = true;
}

function hasActiveQueryOrFilter() {
  const q = document.getElementById('search').value.trim();
  const f = ['filter-family','filter-genus','filter-ext','filter-int','filter-cho']
    .some(id => document.getElementById(id).value);
  return q.length > 0 || f;
}

function applyFilters() {
  if (!hasActiveQueryOrFilter()) {
    hideTable();
    return;
  }
  showTable();

  const q = document.getElementById('search').value.trim().toLowerCase();
  const fam = document.getElementById('filter-family').value;
  const gen = document.getElementById('filter-genus').value;
  const ext = document.getElementById('filter-ext').value;
  const int_ = document.getElementById('filter-int').value;
  const cho = document.getElementById('filter-cho').value;

  view = DATA.filter(d => {
    if (fam && d.family !== fam) return false;
    if (gen && d.genus !== gen) return false;
    if (ext && d.ext_morph.status !== ext) return false;
    if (int_ && d.internal_oral.status !== int_) return false;
    if (cho && d.chondrocranium.status !== cho) return false;
    if (q) {
      const hay = (d.species + ' ' + d.family + ' ' + d.genus).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  sortView();
  render();
}

function sortView() {
  view.sort((a, b) => {
    let av, bv;
    if (sortKey === 'ext') { av = a.ext_morph.status; bv = b.ext_morph.status; }
    else if (sortKey === 'internal_oral') { av = a.internal_oral.status; bv = b.internal_oral.status; }
    else if (sortKey === 'chondrocranium') { av = a.chondrocranium.status; bv = b.chondrocranium.status; }
    else { av = a[sortKey] || ''; bv = b[sortKey] || ''; }
    return String(av).localeCompare(String(bv), 'pt') * sortDir;
  });
}

function render() {
  const body = document.getElementById('species-body');
  document.getElementById('result-count').textContent =
    `${view.length} de ${DATA.length} espécies`;

  if (!view.length) {
    body.innerHTML = `<tr><td colspan="5" style="padding:24px;color:var(--muted)">Nenhuma espécie encontrada.</td></tr>`;
    return;
  }

  body.innerHTML = view.map((d, i) => `<tr>
    <td class="sp-name">${esc(d.species)}</td>
    <td class="sp-family">${esc(d.family)}</td>
    ${charCell(d, 'ext_morph', i)}
    ${charCell(d, 'internal_oral', i)}
    ${charCell(d, 'chondrocranium', i)}
  </tr>`).join('');
}

function charCell(d, charKey, idx) {
  const c = d[charKey];
  const refsHtml = c.refs && c.refs.length
    ? `<button class="refs-toggle" type="button" data-row="${idx}" data-char="${charKey}">${c.refs.length} ref${c.refs.length>1?'s':''}</button>
       <div class="refs-details" id="refs-${idx}-${charKey}" hidden>
         <ol>${c.refs.map(r => `<li>${esc(r)}</li>`).join('')}</ol>
       </div>`
    : '';
  return `<td><div class="refs-cell">
    <span class="badge ${c.status}">${STATUS_LABELS[c.status]}</span>
    ${refsHtml}
  </div></td>`;
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));
}

// ---------- Dashboard ----------
function buildDashboard() {
  // Stat cards globais
  const fams = new Set(DATA.map(d => d.family)).size;
  const desc = c => DATA.filter(d => d[c].status === 'described').length;
  const pct = c => Math.round(desc(c) / DATA.length * 100);
  document.getElementById('stat-cards').innerHTML = [
    card(DATA.length, 'espécies'),
    card(fams, 'famílias'),
    card(pct('ext_morph') + '%', 'morf. externa'),
    card(pct('internal_oral') + '%', 'morf. oral'),
    card(pct('chondrocranium') + '%', 'condrocrânio'),
  ].join('');

  // Por família (ordenada por nº de spp.) — agrupado pelos 3 caracteres
  const fams_list = [...new Set(DATA.map(d => d.family))]
    .sort((a, b) => famCount(b) - famCount(a));
  function famCount(f) { return DATA.filter(d => d.family === f).length; }
  function famPct(f, c) {
    const sp = DATA.filter(d => d.family === f);
    if (!sp.length) return 0;
    return Math.round(sp.filter(d => d[c].status === 'described').length / sp.length * 100);
  }
  const characters = ['ext_morph', 'internal_oral', 'chondrocranium'];
  const colorMap = { ext_morph: '#2e6b4f', internal_oral: '#7aa44a', chondrocranium: '#c9881e' };
  const traces = characters.map(c => ({
    x: fams_list,
    y: fams_list.map(f => famPct(f, c)),
    name: CHAR_LABELS[c],
    type: 'bar',
    marker: { color: colorMap[c] },
    hovertemplate: '%{x}<br>%{data.name}: %{y}%<extra></extra>',
  }));
  whenPlotly(() => Plotly.newPlot('chart-completude', traces, {
    barmode: 'group',
    margin: { t: 10, r: 10, b: 110, l: 50 },
    legend: { orientation: 'h', y: -0.32 },
    font: { family: 'system-ui' },
    yaxis: { title: '% descritos', range: [0, 100] },
    xaxis: { tickangle: -35 },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false, responsive: true }));

  // Spp por família (barra horizontal)
  whenPlotly(() => Plotly.newPlot('chart-family-count', [{
    x: fams_list.map(f => famCount(f)),
    y: fams_list,
    type: 'bar',
    orientation: 'h',
    marker: { color: '#2e6b4f' },
    hovertemplate: '%{y}: %{x} spp.<extra></extra>',
  }], {
    margin: { t: 10, r: 10, b: 40, l: 130 },
    font: { family: 'system-ui' },
    xaxis: { title: 'nº de espécies' },
    yaxis: { autorange: 'reversed' },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false, responsive: true }));

  // Completude global (3 donuts em pizza única — barra empilhada)
  const totals = characters.map(c => ({
    char: c,
    desc: DATA.filter(d => d[c].status === 'described').length,
    miss: DATA.filter(d => d[c].status === 'not_described').length,
  }));
  whenPlotly(() => Plotly.newPlot('chart-global', [
    {
      x: totals.map(t => CHAR_LABELS[t.char]),
      y: totals.map(t => t.desc),
      name: 'Descritos',
      type: 'bar',
      marker: { color: COLORS.described },
    },
    {
      x: totals.map(t => CHAR_LABELS[t.char]),
      y: totals.map(t => t.miss),
      name: 'Não descritos',
      type: 'bar',
      marker: { color: COLORS.not_described },
    },
  ], {
    barmode: 'stack',
    margin: { t: 10, r: 10, b: 60, l: 50 },
    legend: { orientation: 'h', y: -0.2 },
    font: { family: 'system-ui' },
    yaxis: { title: 'nº de espécies' },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false, responsive: true }));
}

function whenPlotly(fn) {
  if (window.Plotly) fn();
  else window.addEventListener('load', fn, { once: true });
}

// ---------- Tabs ----------
function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('is-active'));
      document.querySelectorAll('.view').forEach(v => v.classList.remove('is-active'));
      tab.classList.add('is-active');
      document.getElementById('view-' + tab.dataset.view).classList.add('is-active');
      // Plotly redraw on tab change to fix sizing
      if (tab.dataset.view === 'dashboard') {
        ['chart-completude','chart-family-count','chart-global'].forEach(id => {
          const el = document.getElementById(id);
          if (el && window.Plotly) Plotly.Plots.resize(el);
        });
      }
    });
  });
}

// ---------- Eventos ----------
function setupEvents() {
  document.getElementById('search').addEventListener('input', applyFilters);
  ['filter-family','filter-genus','filter-ext','filter-int','filter-cho'].forEach(
    id => document.getElementById(id).addEventListener('change', applyFilters));

  document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = 1; }
      sortView(); render();
    });
  });

  document.getElementById('btn-show-all').addEventListener('click', () => {
    // Mostra todas — atalho que não exige busca
    showTable();
    view = DATA.slice();
    sortView();
    render();
    document.getElementById('table-block').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  document.getElementById('btn-clear').addEventListener('click', () => {
    document.getElementById('search').value = '';
    ['filter-family','filter-genus','filter-ext','filter-int','filter-cho']
      .forEach(id => document.getElementById(id).value = '');
    applyFilters();
    document.getElementById('hero').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Delegação: toggle de refs
  document.getElementById('species-body').addEventListener('click', e => {
    const btn = e.target.closest('.refs-toggle');
    if (!btn) return;
    const id = `refs-${btn.dataset.row}-${btn.dataset.char}`;
    const el = document.getElementById(id);
    if (el) el.hidden = !el.hidden;
  });

  // Copiar BibTeX (aba Sobre)
  const btnCopy = document.getElementById('btn-copy-bib');
  if (btnCopy) {
    btnCopy.addEventListener('click', async () => {
      const txt = document.getElementById('bib-content').textContent;
      try {
        await navigator.clipboard.writeText(txt);
        const fb = document.getElementById('bib-copy-feedback');
        fb.hidden = false;
        setTimeout(() => { fb.hidden = true; }, 2500);
      } catch (err) {
        alert('Não foi possível copiar automaticamente. Selecione o texto e copie manualmente.');
      }
    });
  }
}

setupTabs();
setupEvents();
load();
