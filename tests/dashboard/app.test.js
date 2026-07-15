// Lightweight Node test for dashboard app.js pure helpers. No framework, no DOM.
// Run with: node tests/dashboard/app.test.js
const assert = require('assert');
const path = require('path');

const app = require(path.join(__dirname, '..', '..', 'src', 'renderer_benchmark_lab', 'dashboard', 'app.js'));

let failures = 0;
function check(name, fn) {
  try { fn(); console.log('ok   -', name); }
  catch (error) { failures += 1; console.error('FAIL -', name, '\n      ', error.message); }
}

check('exports the expected pure helpers', () => {
  for (const key of ['median', 'esc', 'ms', 'pct', 'bar', 'frame', 'imageGroups']) {
    assert.strictEqual(typeof app[key], 'function', `expected function export ${key}`);
  }
  assert.ok(app.state && typeof app.state === 'object', 'expected state export');
});

check('esc escapes html and handles null/undefined', () => {
  assert.strictEqual(app.esc('<a>&"\''), '&lt;a&gt;&amp;&quot;&#39;');
  assert.strictEqual(app.esc(null), '');
  assert.strictEqual(app.esc(undefined), '');
});

check('median computes the middle value', () => {
  assert.strictEqual(app.median([3, 1, 2]), 2);
  assert.strictEqual(app.median([1, 2, 3, 4]), 2.5);
  assert.strictEqual(app.median([7]), 7);
});

check('ms and pct format numbers', () => {
  assert.strictEqual(app.ms(123.456), '123.46 ms');
  assert.strictEqual(app.pct(12.34), '12.3%');
});

check('frame marks missing product images instead of breaking', () => {
  const out = app.frame('Candidate', 'c.png', 'candidate', 3);
  assert.ok(out.includes('class="frame candidate"'));
  assert.ok(out.includes("this.closest('.image-wrap').classList.add('missing')"));
  assert.ok(out.includes('Candidate page 3 not available'));
  assert.ok(!out.includes("closest('figure').remove()"));
});

check('overlay frame removes itself when missing', () => {
  const out = app.frame('Overlay', 'o.png', 'overlay', 1);
  assert.ok(out.includes("this.closest('figure').remove()"));
  assert.ok(!out.includes("classList.add('missing')"));
});

check('imageGroups lays out reference/candidate side by side and a diff view', () => {
  const run = { run_id: 'run1', reference: 'ref' };
  const item = { id: 'caseA' };
  const out = app.imageGroups(run, 'cand', item, 2);
  assert.ok(out.includes('compare-grid'));
  assert.ok(out.includes('diff-grid'));
  assert.ok(out.includes('data/runs/run1/cases/caseA/ref/page-2.png'));
  assert.ok(out.includes('data/runs/run1/cases/caseA/cand/page-2.png'));
  assert.ok(out.includes('data/runs/run1/cases/caseA/diff-cand/page-2.png'));
  assert.ok(out.includes('data/runs/run1/cases/caseA/overlay-cand/page-2.png'));
});

check('imageGroups uses only relative paths', () => {
  const out = app.imageGroups({ run_id: 'r', reference: 'ref' }, 'c', { id: 'x' }, 1);
  assert.ok(!out.includes('http://'));
  assert.ok(!out.includes('https://'));
});

if (failures) {
  console.error(`\n${failures} dashboard check(s) failed`);
  process.exit(1);
}
console.log('\nall dashboard checks passed');
