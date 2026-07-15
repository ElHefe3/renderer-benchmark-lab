// Static dashboard logic. No backend, no network assets, all links relative.
// Safe to require from Node: window/document are only touched in the browser
// bootstrap guard at the bottom, so the pure helpers can be unit tested.
const state = {
  index: (typeof window !== 'undefined' && window.BENCHMARK_INDEX) ? window.BENCHMARK_INDEX : { runs: [] },
  run: null, item: null, candidate: null, page: 1,
};
const $ = id => (typeof document !== 'undefined' ? document.getElementById(id) : null);
const ms = value => `${Number(value).toFixed(2)} ms`;
const pct = value => `${Number(value).toFixed(1)}%`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const median = values => { const sorted = [...values].sort((a, b) => a - b); const middle = Math.floor(sorted.length / 2); return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2; };

function loadScript(src) {
  return new Promise((resolve, reject) => { const script = document.createElement('script'); script.src = src; script.onload = resolve; script.onerror = reject; document.head.append(script); });
}

async function loadRun(id) {
  await loadScript(`data/runs/${encodeURIComponent(id)}/run.js`);
  state.run = window.BENCHMARK_RUNS[id];
  state.item = state.run.cases[0];
  state.candidate = state.run.candidates[0];
  state.page = 1;
  $('candidate').innerHTML = state.run.candidates.map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
  $('candidate').onchange = () => { state.candidate = $('candidate').value; state.page = 1; render(); };
  render();
}

function bar(name, value, max, kind, format = ms) {
  return `<div class="bar"><span>${esc(name)}</span><div class="track"><div class="fill ${kind}" style="width:${Math.min(100, value / max * 100)}%"></div></div><span>${format(value)}</span></div>`;
}

// One image figure. Product images (reference/candidate/diff) that fail to load
// are flagged so the CSS placeholder is shown instead of a broken image. The
// optional overlay figure is removed entirely when its image is missing, so the
// control stays clean when no overlay was produced for a case/page.
function frame(label, src, kind, page) {
  const onerror = kind === 'overlay'
    ? "onerror=\"this.closest('figure').remove()\""
    : "onerror=\"this.closest('.image-wrap').classList.add('missing');this.remove()\"";
  return `<figure class="frame ${kind}"><figcaption>${esc(label)}</figcaption>`
    + `<div class="image-wrap"><img loading="lazy" src="${src}" alt="${esc(label)} page ${page}" ${onerror}>`
    + `<div class="placeholder"><span>${esc(label)} page ${page} not available</span></div></div></figure>`;
}

// Pure HTML builder for the per-page comparison views. Exported for tests.
function imageGroups(run, candidate, item, page) {
  const base = `data/runs/${run.run_id}/cases/${item.id}`;
  const ref = run.reference;
  const refFrame = frame(ref, `${base}/${ref}/page-${page}.png`, 'reference', page);
  const candFrame = frame(candidate, `${base}/${candidate}/page-${page}.png`, 'candidate', page);
  const diffFrame = frame('Difference', `${base}/diff-${candidate}/page-${page}.png`, 'diff', page);
  const overlayFrame = frame('Overlay', `${base}/overlay-${candidate}/page-${page}.png`, 'overlay', page);
  return `<div class="group"><h3>Reference vs candidate</h3><div class="compare-grid">${refFrame}${candFrame}</div></div>`
    + `<div class="group"><h3>Difference &amp; overlay</h3><div class="diff-grid">${diffFrame}${overlayFrame}</div></div>`;
}


function render() {
  const run = state.run, aggregate = run.aggregates, candidate = state.candidate;
  $('content').hidden = false;
  $('status').textContent = `${run.status.toUpperCase()} · ${run.created_at} · ${run.profile} · ${run.environment.os}`;
  const candidateMean = run.cases.reduce((sum, item) => sum + median(item.renderers[candidate].samples_ms), 0) / run.cases.length;
  $('stats').innerHTML = `<div class="stat"><span>Quality</span><strong>${aggregate.quality_score.toFixed(1)}</strong><small>${pct(aggregate.overall_error_percent)} error</small></div><div class="stat"><span>Candidate mean</span><strong>${ms(candidateMean)}</strong><small>Reference ${ms(aggregate.reference_median_ms)}</small></div><div class="stat"><span>Critical failures</span><strong>${aggregate.critical_failure_count}</strong><small>${aggregate.case_count} cases</small></div>`;
  const max = Math.max(aggregate.reference_median_ms, candidateMean);
  $('speed').innerHTML = bar(run.reference, aggregate.reference_median_ms, max, 'reference') + bar(candidate, candidateMean, max, 'candidate');
  const firstRenderers = (run.cases[0] || {}).renderers || {};
  const refScope = (firstRenderers[run.reference] || {}).timing_scope || 'unknown';
  const candScope = (firstRenderers[candidate] || {}).timing_scope || 'unknown';
  $('timing').innerHTML = `<span><strong>${esc(run.reference)}</strong> ${esc(refScope)} scope</span><span><strong>${esc(candidate)}</strong> ${esc(candScope)} scope</span>`;
  const values = ['text', 'layout', 'pagination', 'assets', 'visual'].map(name => ({ name, value: run.cases.reduce((sum, item) => sum + item.comparisons[candidate].categories[name], 0) / run.cases.length }));
  $('errors').innerHTML = values.map(item => bar(item.name, item.value, 100, 'error', pct)).join('');
  $('cases').innerHTML = run.cases.map(item => { const comparison = item.comparisons[candidate], reference = item.renderers[run.reference], selected = item.id === state.item.id ? 'selected' : ''; return `<tr data-id="${esc(item.id)}" class="${selected}"><td>${esc(item.id)}</td><td>${(item.complexity.html_bytes / 1024).toFixed(1)} KiB · ${item.complexity.element_count}</td><td>${ms(median(reference.samples_ms))}</td><td>${ms(median(item.renderers[candidate].samples_ms))}</td><td>${comparison.reference_pages}/${comparison.candidate_pages}</td><td>${comparison.quality_score.toFixed(1)}</td></tr>`; }).join('');
  document.querySelectorAll('tbody tr').forEach(row => { row.onclick = () => { state.item = run.cases.find(item => item.id === row.dataset.id); state.page = 1; render(); }; });
  renderDetail();
}

function renderDetail() {
  const run = state.run, candidate = state.candidate, item = state.item, comparison = item.comparisons[candidate], pages = Math.max(comparison.reference_pages, comparison.candidate_pages);
  $('case-title').textContent = item.id;
  const pageNote = comparison.reference_pages === comparison.candidate_pages ? '' : ' · pages differ';
  $('case-meta').textContent = `${item.complexity.element_count} elements · ${comparison.reference_pages}/${comparison.candidate_pages} pages${pageNote}`;
  $('categories').innerHTML = Object.entries(comparison.categories).map(([name, value]) => `<div class="category"><span>${esc(name)} error</span><strong>${pct(value)}</strong></div>`).join('');
  $('critical').innerHTML = comparison.critical_failures.length
    ? comparison.critical_failures.map(fail => `<li>${esc(fail)}</li>`).join('')
    : '<li class="ok">No critical failures</li>';
  $('page').innerHTML = Array.from({ length: pages }, (_, index) => `<option value="${index + 1}">Page ${index + 1}</option>`).join('');
  $('page').value = state.page;
  $('page').onchange = () => { state.page = Number($('page').value); renderImages(); };
  renderImages();
}

function renderImages() {
  $('pages').innerHTML = imageGroups(state.run, state.candidate, state.item, state.page);
}

if (typeof document !== 'undefined') {
  (async () => {
    const runs = state.index.runs || [];
    if (!runs.length) { $('empty').hidden = false; return; }
    $('run').innerHTML = runs.map(run => `<option value="${esc(run.run_id)}">${esc(run.run_id)} · ${run.status}</option>`).join('');
    $('run').onchange = () => loadRun($('run').value);
    await loadRun(runs[0].run_id);
  })().catch(error => { $('empty').hidden = false; $('empty').textContent = error.message; });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { state, median, esc, ms, pct, bar, frame, imageGroups };
}

