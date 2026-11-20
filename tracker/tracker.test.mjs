import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
const source = readFileSync(new URL('./tracker.js', import.meta.url), 'utf8');
function run({ dnt = '0', allow = false, width = 1440, site = 'public-site-key' } = {}) {
  const requests = [];
  const listeners = {};
  const ctx = {
    document: { currentScript: { dataset: { site, dnt: allow ? 'allow' : undefined }, src: 'https://api.pulselite.test/api/tracker.js' }, referrer: 'https://search.example.test/private?email=discard', visibilityState: 'visible' },
    navigator: { doNotTrack: dnt }, location: { pathname: '/journal', search: '?private=yes', hash: '#secret' }, screen: { width },
    history: { pushState() {}, replaceState() {} }, URL, encodeURIComponent,
    fetch: (url, options) => { requests.push({ url, options, body: JSON.parse(options.body) }); return Promise.resolve(); },
  };
  ctx.window = { addEventListener: (name, fn) => { listeners[name] = fn; } };
  Object.defineProperty(ctx.document, 'cookie', { get() { throw new Error('Cookie read forbidden'); }, set() { throw new Error('Cookie write forbidden'); } });
  for (const key of ['localStorage', 'sessionStorage']) Object.defineProperty(ctx, key, { get() { throw new Error('Storage forbidden'); } });
  vm.runInNewContext(source, ctx);
  return { requests, ctx, listeners };
}
test('tracker stays below 3 KB uncompressed', () => assert.ok(Buffer.byteLength(source) < 3000));
test('one anonymous pageview, credentials omitted and no cookies/storage touched', () => {
  const { requests } = run();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].options.credentials, 'omit');
  assert.equal(requests[0].options.referrerPolicy, 'no-referrer');
  assert.deepEqual(requests[0].body, { type: 'pageview', path: '/journal', referrer: 'search.example.test', device: 'desktop', dnt: false });
});
test('DNT defaults to no request', () => assert.equal(run({ dnt: '1' }).requests.length, 0));
test('explicit owner override sends DNT signal for server enforcement', () => assert.equal(run({ dnt: '1', allow: true }).requests[0].body.dnt, true));
test('absent key does nothing', () => assert.equal(run({ site: '' }).requests.length, 0));
for (const [width, category] of [[375, 'mobile'], [767, 'mobile'], [768, 'tablet'], [1023, 'tablet'], [1024, 'desktop']]) test(`coarse screen category ${width}`, () => assert.equal(run({ width }).requests[0].body.device, category));
test('SPA navigation tracks a new path once, never query-only transitions', () => {
  const { requests, ctx, listeners } = run();
  ctx.history.pushState();
  assert.equal(requests.length, 1);
  ctx.location.pathname = '/work'; ctx.history.pushState();
  assert.equal(requests.length, 2);
  listeners.popstate(); assert.equal(requests.length, 2);
  ctx.location.pathname = '/journal'; listeners.popstate(); assert.equal(requests.length, 3);
});
test('network failure is swallowed, not surfaced to host page', () => {
  const { ctx } = run();
  ctx.fetch = () => Promise.reject(new Error('offline'));
  ctx.location.pathname = '/next'; ctx.history.pushState();
});