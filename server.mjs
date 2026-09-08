// Private loopback preview server. Does not deploy, proxy, or modify live systems.
import http from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const base = path.dirname(fileURLToPath(import.meta.url));
const root = await realpath(path.join(base, 'site'));
const config = JSON.parse(await readFile(path.join(base, 'routes.json'), 'utf8'));
const routes = new Set(config.routes);
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.avif': 'image/avif', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.woff': 'font/woff', '.mp4': 'video/mp4' };
const topAssets = new Set(['/favicon.ico', '/favicon-16x16.png', '/favicon-32x32.png', '/apple-touch-icon.png', '/sitemap.xml']);
const common = { 'X-Robots-Tag': 'noindex, nofollow, noarchive', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
const fallback404 = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Page not found | New Life Hutto</title><style>body{margin:0;background:#102235;color:#f8f4e9;font:18px/1.6 system-ui}main{max-width:650px;margin:12vh auto;padding:28px}p:first-child{color:#d5ae64;letter-spacing:.1em}h1{font:700 48px/1.1 Georgia}a{display:inline-block;color:#102235;background:#d5ae64;padding:12px 22px;border-radius:5px;margin:8px 12px 0 0;text-decoration:none}</style></head><body><main><p>NEW LIFE HUTTO · PRIVATE PREVIEW</p><h1>Let's help you find your way.</h1><p>We couldn't find that page. Plan your visit or head back to the homepage.</p><a href="/visit/">Plan your visit</a><a href="/">Back to home</a></main></body></html>`;

function previewHtml(text) {
  // Source analytics is preserved in files. Preview responses remove both the
  // external loader and its inline config so review traffic never reaches GA.
  return text.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, block => /googletagmanager\.com|google-analytics\.com|\bgtag\s*\(|\bdataLayer\b/.test(block) ? '' : block)
    .replace(/<\/head\s*>/i, '<meta name="robots" content="noindex,nofollow,noarchive"></head>')
    .replace(/<body\b[^>]*>/i, opening => opening + '<div class="private-preview-banner" role="note">Private website preview · Homepage and visitor page</div>');
}

function send(req, res, status, body, type = 'text/plain; charset=utf-8', extras = {}) {
  const bytes = Buffer.isBuffer(body) ? body : Buffer.from(body);
  res.writeHead(status, { ...common, 'Content-Type': type, 'Content-Length': bytes.byteLength, ...extras });
  res.end(req.method === 'HEAD' ? undefined : bytes);
}

async function notFound(req, res) {
  let html;
  try { html = await readFile(path.join(root, '404.html'), 'utf8'); } catch { html = fallback404; }
  send(req, res, 404, previewHtml(html), mime['.html']);
}

function canonicalRoute(p) {
  if (p === '/index.html') return '/';
  const withoutIndex = p.replace(/\/index\.html$/, '/');
  const candidate = withoutIndex.endsWith('/') ? withoutIndex : withoutIndex + '/';
  return routes.has(candidate) ? candidate : null;
}

const server = http.createServer(async (req, res) => {
  try {
    if (!['GET', 'HEAD'].includes(req.method)) return send(req, res, 405, 'Preview supports GET and HEAD only.', undefined, { Allow: 'GET, HEAD' });
    const rawPath = (req.url || '/').split('?')[0];
    let decoded;
    try { decoded = decodeURIComponent(rawPath); } catch { return send(req, res, 400, 'Invalid path.'); }
    // Check the raw decoded input before URL normalization can hide traversal.
    if (decoded.includes('\\') || decoded.includes('\0') || decoded.split('/').some(segment => segment === '.' || segment === '..' || segment.startsWith('.')))
      return send(req, res, 400, 'Invalid path.');
    const url = new URL(req.url || '/', 'http://127.0.0.1:8770');
    const p = decoded;
    if (p === '/robots.txt') return send(req, res, 200, 'User-agent: *\nDisallow: /\n');
    const legacyKey = p.replace(/\/$/, '');
    const destination = config.legacyRedirects[legacyKey] || canonicalRoute(p);
    if (destination && p !== destination)
      return send(req, res, 301, `Moved to ${destination}`, undefined, { Location: destination + url.search });
    let relative;
    if (routes.has(p)) relative = path.join(p.slice(1), 'index.html');
    else if (p.startsWith('/assets/') || topAssets.has(p)) relative = p.slice(1);
    else return await notFound(req, res);
    const fullPath = path.resolve(root, relative);
    if (!fullPath.startsWith(root + path.sep)) return send(req, res, 400, 'Invalid path.');
    let physical;
    try { physical = await realpath(fullPath); } catch { return await notFound(req, res); }
    if (!physical.startsWith(root + path.sep)) return send(req, res, 403, 'Outside preview root.');
    if (!(await stat(physical)).isFile()) return await notFound(req, res);
    const extension = path.extname(physical).toLowerCase();
    let bytes = await readFile(physical);
    if (extension === '.html') bytes = previewHtml(bytes.toString('utf8'));
    send(req, res, 200, bytes, mime[extension] || 'application/octet-stream');
  } catch (error) {
    console.error(error.message);
    if (!res.headersSent) send(req, res, 500, 'Preview server error.'); else res.end();
  }
});
server.listen(8770, '127.0.0.1', () => console.log('Private preview: http://127.0.0.1:8770/'));
