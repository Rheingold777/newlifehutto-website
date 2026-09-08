// Cloudflare Pages advanced-mode source. package-cloudflare.py embeds CONFIG.
// HTML uses internal .page assets, avoiding Pages HTML URL normalization.
export function createHandler(config) {
  const origin = new URL(config.origin);
  const pages = new Map(Object.entries(config.pages));
  const assets = new Set(config.assets);
  const aliases = new Map(Object.entries(config.legacyRedirects));
  const productionHosts = new Set([origin.hostname, `www.${origin.hostname}`]);
  const mime = { '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2', '.mp4': 'video/mp4', '.pdf': 'application/pdf' };

  function canonicalPage(p) {
    if (p === '/index.html') return '/';
    const withoutIndex = p.replace(/\/index\.html$/, '/');
    const candidate = withoutIndex.endsWith('/') ? withoutIndex : withoutIndex + '/';
    return pages.has(candidate) ? candidate : null;
  }

  return {
    async fetch(request, env) {
      const url = new URL(request.url);
      const isProduction = productionHosts.has(url.hostname);
      const headersFor = (extras = {}) => {
        const headers = new Headers(extras);
        headers.set('X-Content-Type-Options', 'nosniff');
        headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
        if (!isProduction) headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
        return headers;
      };
      const answer = (status, body, extras = {}) => new Response(request.method === 'HEAD' ? null : body, { status, headers: headersFor({ 'Content-Type': 'text/plain; charset=utf-8', ...extras }) });
      if (!['GET', 'HEAD'].includes(request.method)) return answer(405, 'Use GET or HEAD.', { Allow: 'GET, HEAD' });

      // Validate before decoding or URL path normalization. Browsers/Cloudflare
      // may already normalize dot segments; no decoded path can escape a map.
      const rawPath = request.url.match(/^[a-z]+:\/\/[^/?#]+([^?#]*)/i)?.[1] || '/';
      let p;
      try { p = decodeURIComponent(rawPath); } catch { return answer(400, 'Invalid path.'); }
      if (/%(?:2f|5c|25)/i.test(rawPath) || /[\\\u0000-\u001f\u007f?#]/.test(p) || p.includes('//') || p.split('/').some(part => part.startsWith('.'))) {
        return answer(400, 'Invalid path.');
      }
      const canonical = aliases.get(p.replace(/\/$/, '')) || canonicalPage(p);
      const destination = canonical || p;
      const wrongHost = isProduction && url.origin !== origin.origin;
      if (wrongHost || (canonical && url.pathname !== canonical)) {
        const location = (isProduction ? origin.origin : '') + destination + url.search;
        return answer(301, 'This page has moved.', { Location: location });
      }

      async function readAsset(assetPath, status, contentType) {
        const assetUrl = new URL(request.url);
        assetUrl.pathname = assetPath;
        assetUrl.search = '';
        // Fetch only manifest-listed paths. Never recurse into this Worker.
        const assetResponse = await env.ASSETS.fetch(new Request(assetUrl, { method: 'GET', headers: { 'Accept-Encoding': request.headers.get('Accept-Encoding') || 'identity' } }));
        // A missing package file must not become a 200 fallback or redirect.
        if (assetResponse.status !== 200) return answer(503, 'This page is temporarily unavailable.', { 'Cache-Control': 'no-store' });
        const headers = headersFor(assetResponse.headers);
        if (contentType) headers.set('Content-Type', contentType);
        if (status === 404) {
          headers.set('X-Robots-Tag', 'noindex');
          headers.set('Cache-Control', 'no-store');
        }
        return new Response(request.method === 'HEAD' ? null : assetResponse.body, { status, headers });
      }

      try {
        if (p === '/robots.txt' && !isProduction) return answer(200, 'User-agent: *\nDisallow: /\n');
        if (pages.has(p)) return await readAsset(pages.get(p), 200, 'text/html; charset=utf-8');
        if (assets.has(p)) {
          const extension = p.slice(p.lastIndexOf('.')).toLowerCase();
          return await readAsset(p, 200, mime[extension] || 'application/octet-stream');
        }
        // Includes undeclared paths, assets that do not exist, internal package
        // files, and retired URLs without a verified relevant successor.
        return await readAsset(config.notFoundAsset, 404, 'text/html; charset=utf-8');
      } catch {
        return answer(503, 'This page is temporarily unavailable.', { 'Cache-Control': 'no-store' });
      }
    }
  };
}
