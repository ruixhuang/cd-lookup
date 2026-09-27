// Headless smoke test for the search logic in docs/index.html. Run: node tests/search_smoke.mjs
import { readFileSync, existsSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../docs/index.html', import.meta.url), 'utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const stub = () => ({ value: '', textContent: '', innerHTML: '', addEventListener() {}, appendChild() {} });
const ctx = {
  window: {}, document: { getElementById: stub, createElement: stub },
  performance: { now: () => 0 }, history: { replaceState() {} },
  location: { hash: '', pathname: '/' }, URLSearchParams, console, setTimeout, clearTimeout,
  fetch: () => new Promise(() => {}),   // never resolves; we inject items ourselves
};
ctx.window = ctx;
vm.createContext(ctx);
vm.runInContext(js, ctx);
const { normalize, editDistance, search, setItems } = ctx.__cdlookup;

const indexPath = new URL('../docs/index.json', import.meta.url);
const sample = [
  { g: 'Rock, Pop, Blues, Soul', a: 'Adrian Belew', t: 'Inner Revolution', y: null, c: null, p: 'x', parent: null },
  { g: 'Rock, Pop, Blues, Soul', a: '', t: 'Tower Of Song; The Songs Of Leonard Cohen', y: null, c: null, p: 'x', parent: null },
  { g: 'Chinese', a: '崔健', t: '红旗下的蛋', y: null, c: null, p: 'x', parent: null },
  { g: 'ECM Records', a: 'Chick Corea & Dave Holland & Barry Altschul', t: 'A.R.C', y: 1971, c: 'ECM 1009', p: 'x', parent: null },
  { g: 'Country', a: 'Johnny Cash', t: 'Ride This Train', y: 1962, c: null, p: 'x', parent: 'Johnny Cash - Complete Columbia' },
  { g: 'Jazz', a: 'André Previn', t: 'King Size', y: null, c: null, p: 'x', parent: null },
];
const items = existsSync(indexPath) ? JSON.parse(readFileSync(indexPath, 'utf8')).items : sample;
setItems(items.map((it) => {
  const norm = normalize([it.a, it.t, it.c || '', it.parent || '', it.y || ''].join(' '));
  return Object.assign(it, { norm, words: norm.split(' ').filter(Boolean) });
}));
console.log(`loaded ${items.length} items (${existsSync(indexPath) ? 'real index' : 'sample'})`);

let failures = 0;
function expect(label, cond, detail = '') {
  console.log(`${cond ? 'ok  ' : 'FAIL'} ${label}${detail ? '  ' + detail : ''}`);
  if (!cond) failures++;
}
const hits = (q, g = '') => search(q, g);
const has = (res, pred) => res.rows.some(pred);

expect('editDistance transposition', editDistance('adrain', 'adrian', 1) === 1);
expect('editDistance bound', editDistance('abcdef', 'xyz', 1) === 2);
expect('normalize strips accents', normalize('André Previn') === 'andre previn');

let r = hits('adrain belew');
expect('typo "adrain belew" finds Adrian Belew', has(r, (i) => i.a === 'Adrian Belew'), `${r.total} matches`);
r = hits('cohen songs');
expect('"cohen songs" finds the Tower Of Song compilation', has(r, (i) => /Leonard Cohen/.test(i.t)), `${r.total} matches`);
r = hits('崔健');
expect('"崔健" finds Cui Jian', has(r, (i) => i.a === '崔健'), `${r.total} matches`);
r = hits('ECM 1009');
expect('"ECM 1009" finds the catalog entry', has(r, (i) => i.c === 'ECM 1009'), `${r.total} matches`);
r = hits('cash 1962');
expect('"cash 1962" finds a box-set child', has(r, (i) => i.parent && /Cash/.test(i.a)), `${r.total} matches`);
r = hits('andre previn');
expect('"andre previn" matches accented André', has(r, (i) => /Andr[ée] Previn/.test(i.a)), `${r.total} matches`);
r = hits('andras schiff');
expect('"andras schiff" matches repaired mojibake name', has(r, (i) => /Andr[áa]s Schiff/.test(i.a)) || !items.some((i) => /Schiff/.test(i.a)), `${r.total} matches`);
r = hits('cash', 'Jazz');
expect('genre filter excludes other genres', r.rows.every((i) => i.g === 'Jazz'), `${r.total} matches`);
r = hits('');
expect('empty query returns everything', r.total === items.length);

if (existsSync(indexPath)) {
  const t0 = Date.now();
  for (const q of ['adrain belew', 'cohen songs', 'miles davis kind', 'zzzzqqq']) search(q, '');
  console.log(`4 queries over real index in ${Date.now() - t0} ms total`);
}
if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log('all search checks passed');
