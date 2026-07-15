const state = { index: window.BENCHMARK_INDEX || { runs: [] }, run: null, item: null, candidate: null, page: 1 };
const $ = id => document.getElementById(id);
const ms = value => `${Number(value).toFixed(2)} ms`;
const pct = value => `${Number(value).toFixed(1)}%`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[char]));
const median = values => { const sorted = [...values].sort((a,b) => a-b); const middle = Math.floor(sorted.length/2); return sorted.length%2 ? sorted[middle] : (sorted[middle-1]+sorted[middle])/2; };

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
  return `<div class="bar"><span>${esc(name)}</span><div class="track"><div class="fill ${kind}" style="width:${Math.min(100,value/max*100)}%"></div></div><span>${format(value)}</span></div>`;
}

function render() {
  const run = state.run, aggregate = run.aggregates, candidate = state.candidate;
  $('content').hidden = false;
  $('status').textContent = `${run.status.toUpperCase()} · ${run.created_at} · ${run.profile} · ${run.environment.os}`;
  const candidateMean = run.cases.reduce((sum,item) => sum + median(item.renderers[candidate].samples_ms), 0) / run.cases.length;
  $('stats').innerHTML = `<div class="stat"><span>Quality</span><strong>${aggregate.quality_score.toFixed(1)}</strong><small>${pct(aggregate.overall_error_percent)} error</small></div><div class="stat"><span>Candidate mean</span><strong>${ms(candidateMean)}</strong><small>Reference ${ms(aggregate.reference_median_ms)}</small></div><div class="stat"><span>Critical failures</span><strong>${aggregate.critical_failure_count}</strong><small>${aggregate.case_count} cases</small></div>`;
  const max = Math.max(aggregate.reference_median_ms, candidateMean);
  $('speed').innerHTML = bar(run.reference, aggregate.reference_median_ms, max, 'reference') + bar(candidate, candidateMean, max, 'candidate');
  const values = ['text','layout','pagination','assets','visual'].map(name => ({ name, value: run.cases.reduce((sum,item) => sum + item.comparisons[candidate].categories[name],0) / run.cases.length }));
  $('errors').innerHTML = values.map(item => bar(item.name,item.value,100,'error',pct)).join('');
  $('cases').innerHTML = run.cases.map(item => { const comparison=item.comparisons[candidate], reference=item.renderers[run.reference], selected=item.id===state.item.id?'selected':''; return `<tr data-id="${esc(item.id)}" class="${selected}"><td>${esc(item.id)}</td><td>${(item.complexity.html_bytes/1024).toFixed(1)} KiB · ${item.complexity.element_count}</td><td>${ms(median(reference.samples_ms))}</td><td>${ms(median(item.renderers[candidate].samples_ms))}</td><td>${comparison.reference_pages}/${comparison.candidate_pages}</td><td>${comparison.quality_score.toFixed(1)}</td></tr>`; }).join('');
  document.querySelectorAll('tbody tr').forEach(row => { row.onclick=()=>{ state.item=run.cases.find(item=>item.id===row.dataset.id); state.page=1; render(); }; });
  renderDetail();
}

function renderDetail() {
  const run=state.run, candidate=state.candidate, item=state.item, comparison=item.comparisons[candidate], pages=Math.max(comparison.reference_pages,comparison.candidate_pages);
  $('case-title').textContent=item.id;
  $('case-meta').textContent=`${item.complexity.element_count} elements · ${comparison.reference_pages}/${comparison.candidate_pages} pages`;
  $('categories').innerHTML=Object.entries(comparison.categories).map(([name,value])=>`<div class="category"><span>${esc(name)} error</span><strong>${pct(value)}</strong></div>`).join('');
  $('page').innerHTML=Array.from({length:pages},(_,index)=>`<option value="${index+1}">Page ${index+1}</option>`).join('');
  $('page').value=state.page;
  $('page').onchange=()=>{state.page=Number($('page').value);renderImages();};
  renderImages();
}

function renderImages() {
  const run=state.run, candidate=state.candidate, item=state.item, page=state.page, base=`data/runs/${run.run_id}/cases/${item.id}`;
  $('pages').innerHTML=[[run.reference,`${base}/${run.reference}/page-${page}.png`],[candidate,`${base}/${candidate}/page-${page}.png`],['Difference',`${base}/diff-${candidate}/page-${page}.png`]].map(([label,src])=>`<figure><figcaption>${esc(label)}</figcaption><img src="${src}" alt="${esc(label)} page ${page}"></figure>`).join('');
}

(async () => {
  const runs=state.index.runs||[];
  if(!runs.length){$('empty').hidden=false;return;}
  $('run').innerHTML=runs.map(run=>`<option value="${esc(run.run_id)}">${esc(run.run_id)} · ${run.status}</option>`).join('');
  $('run').onchange=()=>loadRun($('run').value);
  await loadRun(runs[0].run_id);
})().catch(error=>{$('empty').hidden=false;$('empty').textContent=error.message;});
