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
    buildTrendIndex();
    buildTrendUI();
    whenPlotly(renderTrend);
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

// Mostra "Ver na filogenia" só quando o filtro de família ou gênero está ativo.
// Mostra texto adaptado (família ou gênero alvo).
function updatePhyloJumpBtn() {
  const btn = document.getElementById('btn-phylo-link');
  if (!btn) return;
  const fam = document.getElementById('filter-family').value;
  const gen = document.getElementById('filter-genus').value;
  if (gen) {
    btn.hidden = false;
    btn.textContent = `Ver ${gen} na filogenia →`;
  } else if (fam) {
    btn.hidden = false;
    btn.textContent = `Ver ${fam} na filogenia →`;
  } else {
    btn.hidden = true;
  }
}

function hasActiveQueryOrFilter() {
  const q = document.getElementById('search').value.trim();
  const f = ['filter-family','filter-genus','filter-ext','filter-int','filter-cho']
    .some(id => document.getElementById(id).value);
  return q.length > 0 || f;
}

function applyFilters() {
  updatePhyloJumpBtn();
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
         <ol>${c.refs.map(formatRef).join('')}</ol>
       </div>`
    : '';
  return `<td><div class="refs-cell">
    <span class="badge ${c.status}">${STATUS_LABELS[c.status]}</span>
    ${refsHtml}
  </div></td>`;
}

// Renderiza uma ref estruturada como citação curta + link DOI.
// Aceita também strings (schema antigo) por segurança.
function formatRef(r) {
  if (typeof r === 'string') return `<li>${esc(r)}</li>`;
  if (!r) return '';
  const parts = [];
  if (r.author) parts.push(esc(r.author));
  if (r.year)   parts.push(`(${r.year})`);
  if (r.title)  parts.push(esc(r.title) + '.');
  if (r.journal) parts.push(`<em>${esc(r.journal)}</em>.`);
  let line = parts.join(' ');
  if (!line) line = esc(r.raw || '');
  if (r.doi) {
    const doi = esc(r.doi);
    line += ` <a href="https://doi.org/${doi}" target="_blank" rel="noopener">doi:${doi}</a>`;
  }
  return `<li>${line}</li>`;
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

// Normaliza uma ref para o índice de tendências. Aceita o schema
// estruturado (5.1.0+: objeto com year/doi/raw) e cai pra string solta
// se aparecer um JSON antigo. Retorna { key, year } ou null.
function normalizeRef(ref) {
  if (!ref) return null;
  if (typeof ref === 'object') {
    if (ref.year == null) return null;
    const key = ref.doi ? ('doi:' + ref.doi) : ('raw:' + (ref.raw || ''));
    return { key, year: ref.year };
  }
  // legado: string solta — extrai ano por regex
  const r = String(ref).trim();
  if (r.length < 25) return null;
  const ys = r.match(/\b(18\d{2}|19\d{2}|20\d{2})\b/g);
  if (!ys) return null;
  const y = Math.max(...ys.map(Number));
  if (y < 1850 || y > 2030) return null;
  return { key: 'raw:' + r, year: y };
}

// ---------- Tendências (linha por década) ----------
// Paleta categórica (ColorBrewer Set2 + extras), repete se exceder.
const TREND_PALETTE = [
  '#2e6b4f','#c9881e','#3b6fa1','#9c3d75','#7aa44a','#b53c3c',
  '#5d4a8a','#1f8a8a','#a86b2a','#54607a','#75ad6f','#c4663d',
  '#8a4a8a','#2e7a7a','#a89540','#8c6d1a','#4a8a4a','#3a5e8c',
];
let TREND_REFS = [];   // [{ref, year, decade, family, chars: Set}]
let TREND_FAMS = [];   // famílias ordenadas por nº de refs (desc)
let TREND_DECADES = []; // décadas presentes (asc)
let TREND_FAM_SELECTED = new Set();

// Constrói o índice a partir do novo schema de refs (objeto com `year`).
// Cada ref única (chave: doi || raw) ganha uma entrada por família em que
// aparece, para permitir contagem dedup por (família, década).
function buildTrendIndex() {
  // map: refKey -> { year, families: Set, chars: Set }
  const byRef = new Map();
  for (const sp of DATA) {
    for (const ch of ['ext_morph','internal_oral','chondrocranium']) {
      const refs = sp[ch].refs || [];
      for (const ref of refs) {
        const r = normalizeRef(ref);
        if (!r || r.year == null) continue;
        let entry = byRef.get(r.key);
        if (!entry) {
          entry = { year: r.year, families: new Set(), chars: new Set() };
          byRef.set(r.key, entry);
        }
        entry.families.add(sp.family);
        entry.chars.add(ch);
      }
    }
  }
  TREND_REFS = [];
  for (const [key, e] of byRef) {
    for (const fam of e.families) {
      TREND_REFS.push({
        ref: key,
        year: e.year,
        decade: Math.floor(e.year / 10) * 10,
        family: fam,
        chars: e.chars,
      });
    }
  }
  // famílias ordenadas por nº de refs únicas
  const famCounts = new Map();
  for (const t of TREND_REFS) {
    famCounts.set(t.family, (famCounts.get(t.family) || 0) + 1);
  }
  TREND_FAMS = [...famCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([f]) => f);
  // décadas
  const decSet = new Set(TREND_REFS.map(t => t.decade));
  if (decSet.size) {
    const dmin = Math.min(...decSet), dmax = Math.max(...decSet);
    TREND_DECADES = [];
    for (let d = dmin; d <= dmax; d += 10) TREND_DECADES.push(d);
  } else {
    TREND_DECADES = [];
  }
}

function buildTrendUI() {
  const list = document.getElementById('trend-fam-list');
  if (!list) return;
  // checkbox por família (default: Top 6 marcados)
  TREND_FAM_SELECTED = new Set(TREND_FAMS.slice(0, 6));
  list.innerHTML = TREND_FAMS.map(f => `
    <label><input type="checkbox" class="trend-fam-cb" value="${esc(f)}"
      ${TREND_FAM_SELECTED.has(f) ? 'checked' : ''}> ${esc(f)}</label>
  `).join('');

  // listeners
  document.querySelectorAll('input[name="trend-mode"]').forEach(r =>
    r.addEventListener('change', onTrendChange));
  document.querySelectorAll('input[name="trend-char"]').forEach(r =>
    r.addEventListener('change', renderTrend));
  document.querySelectorAll('input[name="trend-cum"]').forEach(r =>
    r.addEventListener('change', renderTrend));
  list.addEventListener('change', e => {
    const cb = e.target.closest('.trend-fam-cb');
    if (!cb) return;
    if (cb.checked) TREND_FAM_SELECTED.add(cb.value);
    else TREND_FAM_SELECTED.delete(cb.value);
    renderTrend();
  });
  document.getElementById('trend-fam-top').addEventListener('click', () => {
    TREND_FAM_SELECTED = new Set(TREND_FAMS.slice(0, 6));
    syncFamCheckboxes(); renderTrend();
  });
  document.getElementById('trend-fam-all').addEventListener('click', () => {
    TREND_FAM_SELECTED = new Set(TREND_FAMS);
    syncFamCheckboxes(); renderTrend();
  });
  document.getElementById('trend-fam-none').addEventListener('click', () => {
    TREND_FAM_SELECTED = new Set();
    syncFamCheckboxes(); renderTrend();
  });

  onTrendChange();
}

function syncFamCheckboxes() {
  document.querySelectorAll('.trend-fam-cb').forEach(cb => {
    cb.checked = TREND_FAM_SELECTED.has(cb.value);
  });
}

function onTrendChange() {
  const mode = document.querySelector('input[name="trend-mode"]:checked').value;
  document.getElementById('trend-families-group').hidden = (mode !== 'family');
  renderTrend();
}

function renderTrend() {
  if (!window.Plotly || !TREND_DECADES.length) return;
  const mode = document.querySelector('input[name="trend-mode"]:checked').value;
  const cum  = document.querySelector('input[name="trend-cum"]:checked').value === 'cumulative';
  const charsSel = new Set(
    [...document.querySelectorAll('input[name="trend-char"]:checked')].map(c => c.value)
  );

  // filtra por caráter (uma ref entra se interseccionar o subset escolhido)
  const filtered = TREND_REFS.filter(t => {
    for (const c of t.chars) if (charsSel.has(c)) return true;
    return false;
  });

  const x = TREND_DECADES.map(d => d + 's');
  let traces = [];

  if (mode === 'all') {
    // total: refs únicas por década (deduplicar refs entre famílias)
    const seen = new Map(); // ref -> decade
    for (const t of filtered) {
      if (!seen.has(t.ref)) seen.set(t.ref, t.decade);
    }
    const counts = new Map(TREND_DECADES.map(d => [d, 0]));
    for (const d of seen.values()) counts.set(d, counts.get(d) + 1);
    let y = TREND_DECADES.map(d => counts.get(d));
    if (cum) y = cumulative(y);
    traces.push({
      x, y,
      mode: 'lines+markers',
      type: 'scatter',
      name: 'Todas as famílias',
      line: { color: COLORS.accent, width: 2.5 },
      marker: { size: 7, color: COLORS.accent },
      hovertemplate: '%{x}: <b>%{y}</b> artigos<extra></extra>',
    });
  } else {
    // por família: refs únicas por (família, década)
    const sel = [...TREND_FAM_SELECTED].filter(f => TREND_FAMS.includes(f));
    sel.sort((a, b) => TREND_FAMS.indexOf(a) - TREND_FAMS.indexOf(b));
    sel.forEach((fam, i) => {
      const refsFam = filtered.filter(t => t.family === fam);
      // refs únicas por década dentro da família
      const seen = new Map();
      for (const t of refsFam) if (!seen.has(t.ref)) seen.set(t.ref, t.decade);
      const counts = new Map(TREND_DECADES.map(d => [d, 0]));
      for (const d of seen.values()) counts.set(d, counts.get(d) + 1);
      let y = TREND_DECADES.map(d => counts.get(d));
      if (cum) y = cumulative(y);
      const color = TREND_PALETTE[i % TREND_PALETTE.length];
      traces.push({
        x, y,
        mode: 'lines+markers',
        type: 'scatter',
        name: fam,
        line: { color, width: 2 },
        marker: { size: 6, color },
        hovertemplate: `<b>${esc(fam)}</b><br>%{x}: %{y} artigos<extra></extra>`,
      });
    });
    if (!traces.length) {
      traces.push({ x, y: TREND_DECADES.map(() => 0), type: 'scatter',
        mode: 'lines', line: { color: '#ccc' }, name: '(nenhuma família)' });
    }
  }

  const layout = {
    margin: { t: 10, r: 10, b: 60, l: 60 },
    font: { family: 'system-ui' },
    xaxis: { title: 'Década', tickangle: -35 },
    yaxis: { title: cum ? 'Artigos acumulados' : 'Artigos por década', rangemode: 'tozero' },
    legend: { orientation: 'h', y: -0.2 },
    hovermode: 'closest',
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  };
  Plotly.react('chart-trend', traces, layout,
    { displayModeBar: true, displaylogo: false, responsive: true,
      modeBarButtonsToRemove: ['lasso2d','select2d','autoScale2d','toggleSpikelines'] });
}

function cumulative(arr) {
  let s = 0;
  return arr.map(v => (s += v));
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
      if (tab.dataset.view === 'tendencias') {
        const el = document.getElementById('chart-trend');
        if (el && window.Plotly) Plotly.Plots.resize(el);
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

  // "Ver na filogenia" — vai pra aba e focaliza o clado MRCA
  const btnPhylo = document.getElementById('btn-phylo-link');
  if (btnPhylo) {
    btnPhylo.addEventListener('click', () => {
      const fam = document.getElementById('filter-family').value;
      const gen = document.getElementById('filter-genus').value;
      const target = gen ? { genus: gen } : fam ? { family: fam } : null;
      if (!target) return;
      jumpToPhylo(target);
    });
  }

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

// ---------- Cross-filter (Espécies ↔ Filogenia) ----------
function switchTab(view) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('is-active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('is-active'));
  const tab = document.querySelector(`.tab[data-view="${view}"]`);
  const sec = document.getElementById('view-' + view);
  if (tab) tab.classList.add('is-active');
  if (sec) sec.classList.add('is-active');
  // Plotly precisa redimensionar se a aba alvo é o dashboard
  if (view === 'dashboard') {
    ['chart-completude','chart-family-count','chart-global'].forEach(id => {
      const el = document.getElementById(id);
      if (el && window.Plotly) Plotly.Plots.resize(el);
    });
  }
  if (view === 'tendencias') {
    const el = document.getElementById('chart-trend');
    if (el && window.Plotly) Plotly.Plots.resize(el);
  }
  // Filogenia: pede inicialização se ainda não foi
  if (view === 'filogenia' && window.PhyloView) window.PhyloView.ensureInit();
}

async function jumpToPhylo(target) {
  switchTab('filogenia');
  if (!window.PhyloView) return;
  try {
    const ok = await window.PhyloView.focus(target);
    const msg = document.getElementById('phylo-focus-msg');
    if (!ok && msg) {
      const what = target.species || target.genus || target.family;
      msg.textContent = `"${what}" não está presente na árvore podada (provavelmente espécie descrita após a publicação da megatree).`;
      msg.hidden = false;
      setTimeout(() => { msg.hidden = true; }, 5000);
    } else if (msg) {
      msg.hidden = true;
    }
  } catch (err) {
    console.warn('PhyloView.focus falhou:', err);
  }
}

// Expostos pra phylogeny.js disparar filtro de volta na aba Espécies
window.SpeciesView = {
  filterBy(target) {
    // target = {family} | {genus} | {species}
    const searchEl = document.getElementById('search');
    const famEl = document.getElementById('filter-family');
    const genEl = document.getElementById('filter-genus');
    // Limpa filtros restritivos antes de aplicar — evita zerar acidentalmente
    searchEl.value = '';
    famEl.value = '';
    genEl.value = '';
    ['filter-ext','filter-int','filter-cho'].forEach(id => { document.getElementById(id).value = ''; });
    if (target.species) {
      searchEl.value = target.species;
    } else if (target.genus) {
      // Se gênero estiver na lista, usa o filtro; senão cai pra busca textual
      if ([...genEl.options].some(o => o.value === target.genus)) genEl.value = target.genus;
      else searchEl.value = target.genus;
    } else if (target.family) {
      if ([...famEl.options].some(o => o.value === target.family)) famEl.value = target.family;
      else searchEl.value = target.family;
    }
    switchTab('especies');
    applyFilters();
    // Rola pro topo da tabela
    const tb = document.getElementById('table-block');
    if (tb && !tb.hidden) tb.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

setupTabs();
setupEvents();
load();
