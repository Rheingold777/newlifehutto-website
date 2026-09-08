import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHandler } from '../cloudflare-runtime/worker.mjs';

const routes = JSON.parse(await readFile(new URL('../routes.json', import.meta.url), 'utf8'));
const config = { origin: routes.origin, legacyRedirects: routes.legacyRedirects, pages: Object.fromEntries(routes.routes.map((p, i) => [p, `/_nlh-pages/${i}.page`])), assets: ['/assets/site.css', '/favicon.ico', '/sitemap.xml', '/robots.txt'], notFoundAsset: '/_nlh-pages/not-found.page' };
const handler = createHandler(config);
const calls = [];
const bodyByPath = new Map(Object.entries(config.pages).map(([publicPath, assetPath]) => [assetPath, `<html><h1>Page ${publicPath}</h1></html>`]));
bodyByPath.set(config.notFoundAsset, '<html><h1>Page not found</h1></html>');
for (const p of config.assets) bodyByPath.set(p, p === '/robots.txt' ? 'User-agent: *\nAllow: /\n' : 'asset body');
const env = { ASSETS: { fetch: async request => {
  const pathname = new URL(request.url).pathname;
  calls.push(pathname);
  return bodyByPath.has(pathname) ? new Response(bodyByPath.get(pathname), { headers: { 'Content-Type': 'application/octet-stream', ETag: '"fixture"' } }) : new Response('unintended fallback', { status: 404 });
} } };
const run = (p, options = {}) => handler.fetch(new Request(`https://newlifehutto.com${p}`, options), env);

test('all 14 canonical pages serve exact intended bodies and HTML content type', async () => {
  for (const route of routes.routes) {
    const response = await run(route);
    assert.equal(response.status, 200, route);
    assert.equal(response.headers.get('Location'), null);
    assert.match(response.headers.get('Content-Type'), /^text\/html/);
    assert.equal(response.headers.get('X-Robots-Tag'), null);
    assert.equal(await response.text(), `<html><h1>Page ${route}</h1></html>`);
  }
});

test('host, protocol, slash and index aliases converge in one permanent redirect with exact query', async () => {
  const query = '?utm_source=maps&x=a%2Bb&x=c+d&empty=';
  for (const route of routes.routes) {
    const variants = new Set([route === '/' ? '/index.html' : route.slice(0, -1), route + 'index.html']);
    for (const variant of variants) {
      for (const origin of ['https://newlifehutto.com', 'https://www.newlifehutto.com', 'http://newlifehutto.com', 'http://www.newlifehutto.com']) {
        const response = await handler.fetch(new Request(origin + variant + query), env);
        assert.equal(response.status, 301, origin + variant);
        assert.equal(response.headers.get('Location'), routes.origin + route + query);
      }
    }
  }
});

test('each declared legacy alias and optional slash preserves query in one redirect', async () => {
  for (const [legacy, target] of Object.entries(routes.legacyRedirects)) {
    for (const suffix of ['', '/']) {
      const response = await handler.fetch(new Request('http://www.newlifehutto.com' + legacy + suffix + '?a=1%202&a=3'), env);
      assert.equal(response.status, 301);
      assert.equal(response.headers.get('Location'), routes.origin + target + '?a=1%202&a=3');
    }
  }
});

test('retired routes, unknown routes, missing assets and internal files return real noindex 404s', async () => {
  for (const path of ['/kids', '/youth', '/upcoming-events', '/your-salvation-matters', '/es/', '/sermons/', '/blog/', '/never-existed/', '/assets/missing.png', '/_worker.js', '/_routes.json', '/manifest.json', '/_nlh-pages/0.page', '/404.html']) {
    const response = await run(path);
    assert.equal(response.status, 404, path);
    assert.equal(response.headers.get('Location'), null);
    assert.match(response.headers.get('X-Robots-Tag'), /noindex/);
    assert.equal(await response.text(), '<html><h1>Page not found</h1></html>');
  }
});

test('safe escaped letters normalize only to an existing route; unsafe encodings never read assets', async () => {
  const response = await run('/v%69sit?ref=test');
  assert.equal(response.status, 301);
  assert.equal(response.headers.get('Location'), routes.origin + '/visit/?ref=test');
  for (const path of ['/visit%2f', '/assets%2fsite.css', '/%5cvisit/', '/%00', '/%ff', '/%E0%A4%A', '/%25%32%65', '/%23x', '/%3Fx', '//visit/', '/.env', '/assets/.private']) {
    const before = calls.length;
    const result = await run(path);
    assert.equal(result.status, 400, path);
    assert.equal(calls.length, before, path);
  }
  // Exercise raw paths before standards-compliant Request has normalized them.
  for (const path of ['/assets/../index.html', '/assets/%2e%2e/index.html']) {
    const before = calls.length;
    const result = await handler.fetch({ url: routes.origin + path, method: 'GET', headers: new Headers() }, env);
    assert.equal(result.status, 400);
    assert.equal(calls.length, before);
  }
});

test('asset bytes, content type, HEAD semantics and rejected methods', async () => {
  const css = await run('/assets/site.css?v=2');
  assert.equal(css.status, 200);
  assert.match(css.headers.get('Content-Type'), /^text\/css/);
  assert.equal(await css.text(), 'asset body');
  for (const [path, status] of [['/', 200], ['/visit', 301], ['/unknown/', 404], ['/assets/site.css', 200]]) {
    const head = await run(path, { method: 'HEAD' });
    assert.equal(head.status, status);
    assert.equal(await head.text(), '');
  }
  for (const method of ['POST', 'PUT', 'DELETE', 'OPTIONS']) {
    const response = await run('/contact/', { method });
    assert.equal(response.status, 405);
    assert.equal(response.headers.get('Allow'), 'GET, HEAD');
  }
});

test('Pages preview retains its host with noindex; production robots stays crawlable', async () => {
  const preview = await handler.fetch(new Request('https://candidate.newlifehutto.pages.dev/visit'), env);
  assert.equal(preview.status, 301);
  assert.equal(preview.headers.get('Location'), '/visit/');
  assert.match(preview.headers.get('X-Robots-Tag'), /noindex/);
  const robots = await handler.fetch(new Request('https://candidate.newlifehutto.pages.dev/robots.txt'), env);
  assert.match(await robots.text(), /Disallow: \//);
  const productionRobots = await run('/robots.txt');
  assert.equal(productionRobots.headers.get('X-Robots-Tag'), null);
  assert.match(await productionRobots.text(), /Allow: \//);
});

test('asset backend redirects, missing files and exceptions fail closed with 503', async () => {
  for (const status of [301, 302, 404, 500]) {
    const response = await handler.fetch(new Request(routes.origin + '/'), { ASSETS: { fetch: async () => new Response('backend fallback', { status }) } });
    assert.equal(response.status, 503);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.doesNotMatch(await response.text(), /backend fallback/);
  }
  const response = await handler.fetch(new Request(routes.origin + '/'), { ASSETS: { fetch: async () => { throw Error('backend offline'); } } });
  assert.equal(response.status, 503);
});
