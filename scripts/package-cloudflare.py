"""Create an inspectable Cloudflare Pages release candidate. Never deploys.

Outputs a deploy/ directory, reproducible deploy.zip, and SHA-256 manifest.
Read source files directly: do not package responses from localhost.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "cloudflare-runtime"
ICON_FILES = {"favicon.ico", "favicon-16x16.png", "favicon-32x32.png", "apple-touch-icon.png"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.og_urls = []
        self.noindex = False
        self.links = []
        self.resources = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href"))
        if tag == "meta" and a.get("property", "").lower() == "og:url":
            self.og_urls.append(a.get("content"))
        if tag == "meta" and a.get("name", "").lower() in {"robots", "googlebot"}:
            self.noindex |= "noindex" in a.get("content", "").lower()
        if tag == "a" and a.get("href", "").startswith("/"):
            self.links.append(a["href"])
        if tag in {"img", "script", "source"} and a.get("src", "").startswith("/"):
            self.resources.append(a["src"])
        if tag == "link" and a.get("rel") in {"stylesheet", "icon", "apple-touch-icon"} and a.get("href", "").startswith("/"):
            self.resources.append(a["href"])


def build(site: Path, output: Path, release_path: Path, rollback_archive: Path | None = None) -> dict:
    site = site.resolve(strict=True)
    output = output.resolve()
    # New output only. No recursive deletion, implicit overwrite, or mixing
    # candidate assets with an earlier release.
    if output.exists():
        raise ValueError(f"Output already exists; choose a new candidate directory: {output}")
    if output == site or site in output.parents:
        raise ValueError("Output cannot be inside the source site")
    routes = json.loads((ROOT / "routes.json").read_text(encoding="utf-8"))
    release = json.loads(release_path.read_text(encoding="utf-8"))
    origin = routes["origin"].rstrip("/")
    if origin != "https://newlifehutto.com":
        raise ValueError("Unexpected canonical origin")
    if len(routes["routes"]) != 14 or len(set(routes["routes"])) != 14:
        raise ValueError("Expected the 14 explicitly intended routes")
    expected_html = {((p.strip("/") + "/") if p != "/" else "") + "index.html" for p in routes["routes"]}
    actual_html = {p.relative_to(site).as_posix() for p in site.rglob("*.html")}
    if actual_html - expected_html - {"404.html"}:
        raise ValueError(f"Unreviewed HTML files: {sorted(actual_html - expected_html - {'404.html'})}")
    if not expected_html.issubset(actual_html):
        raise ValueError(f"Missing pages: {sorted(expected_html - actual_html)}")

    baseline = release["productionBaseline"]
    if not re.fullmatch(r"[0-9a-fA-F]{64}", baseline["archiveSha256"]):
        raise ValueError("Production rollback archive SHA-256 is invalid")
    # Build inputs are portable public source. Recovery archives remain in
    # church-controlled storage; verify the real archive before a release.
    if rollback_archive is not None and sha(rollback_archive.read_bytes()) != baseline["archiveSha256"].lower():
        raise ValueError("Production rollback archive hash does not match the recorded v4 baseline")
    dates = release.get("pageLastModified", {})
    if set(dates) - set(routes["routes"]):
        raise ValueError("Content-date keys must match intended routes")
    for route, value in dates.items():
        if date.fromisoformat(value) > date.today():
            raise ValueError(f"Future lastmod for {route}")

    files: dict[str, bytes] = {}
    source_files = []
    page_files = {}
    public_assets = []
    metadata = {}
    for route in routes["routes"]:
        rel = ((route.strip("/") + "/") if route != "/" else "") + "index.html"
        src = site / rel
        if src.is_symlink() or not src.resolve().is_relative_to(site):
            raise ValueError(f"Page escapes source tree: {rel}")
        content = src.read_bytes()
        text = content.decode("utf-8-sig")
        parser = PageMetadata()
        parser.feed(text)
        if parser.canonicals != [origin + route] or parser.og_urls != [origin + route]:
            raise ValueError(f"Canonical/Open Graph URL mismatch on {route}")
        if parser.noindex or re.search(r'private-preview-banner|Private website preview|127\.0\.0\.1:8770', text, re.I):
            raise ValueError(f"Private preview content must not be packaged: {route}")
        for match in re.finditer(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', text, re.I | re.S):
            json.loads(match.group(1))
        internal = "_nlh-pages/" + (route.strip("/").replace("/", "--") or "home") + ".page"
        if internal in files:
            raise ValueError(f"Internal asset-name collision: {route}")
        files[internal] = content
        page_files[route] = "/" + internal
        metadata[route] = parser
        source_files.append({"source": rel, "packaged": internal, "sha256": sha(content), "bytes": len(content)})

    for src in sorted(site.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(site).as_posix()
        if rel.lower().endswith("desktop.ini") or rel == ".assetsignore":
            continue
        if not (rel.startswith("assets/") or rel in ICON_FILES):
            continue
        if src.is_symlink() or not src.resolve().is_relative_to(site) or any(p.startswith(".") for p in src.relative_to(site).parts):
            raise ValueError(f"Unsafe public asset: {rel}")
        if src.suffix.lower() not in {".css", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".avif", ".ico", ".woff", ".woff2", ".mp4", ".pdf"}:
            raise ValueError(f"Unreviewed public asset type: {rel}")
        content = src.read_bytes()
        if len(content) > 25 * 1024 * 1024:
            raise ValueError(f"Asset exceeds Pages per-file limit: {rel}")
        files[rel] = content
        public_assets.append("/" + rel)
        source_files.append({"source": rel, "packaged": rel, "sha256": sha(content), "bytes": len(content)})

    files["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n".encode()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for route in routes["routes"]:
        lastmod = f"<lastmod>{dates[route]}</lastmod>" if route in dates else ""
        lines.append(f"  <url><loc>{escape(origin + route)}</loc>{lastmod}</url>")
    lines.append("</urlset>")
    files["sitemap.xml"] = ("\n".join(lines) + "\n").encode()
    public_assets += ["/robots.txt", "/sitemap.xml"]
    not_found = (RUNTIME / "404.html").read_bytes()
    files["_nlh-pages/not-found.page"] = not_found
    files["404.html"] = not_found  # Also disables Pages' implicit SPA fallback.
    config = {"origin": origin, "pages": page_files, "assets": sorted(public_assets), "legacyRedirects": routes["legacyRedirects"], "notFoundAsset": "/_nlh-pages/not-found.page"}
    source = (RUNTIME / "worker.mjs").read_text(encoding="utf-8")
    files["_worker.js"] = (source + "\nconst CONFIG = " + json.dumps(config, ensure_ascii=False, sort_keys=True) + ";\nexport default createHandler(CONFIG);\n").encode()
    files["_routes.json"] = json_bytes({"version": 1, "include": ["/*"], "exclude": []})
    all_resources = set(public_assets)
    for route, parser in metadata.items():
        for url in parser.resources:
            target = url.split("?", 1)[0].split("#", 1)[0]
            if target not in all_resources:
                raise ValueError(f"Missing packaged asset {target} on {route}")
        for url in parser.links:
            target = url.split("?", 1)[0].split("#", 1)[0]
            if target not in page_files and target not in all_resources:
                raise ValueError(f"Internal link is not a direct canonical page or packaged asset: {url} on {route}")

    output.mkdir(parents=True)
    deploy = output / "deploy"
    for rel, data in sorted(files.items()):
        destination = deploy / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    archive = output / "deploy.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, data in sorted(files.items()):
            entry = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest = {"schemaVersion": 1, "state": "Local release candidate; not deployed", "sourceDirectory": site.relative_to(ROOT).as_posix() if site.is_relative_to(ROOT) else site.name, "releaseContext": release, "rollbackArchiveVerified": rollback_archive is not None, "canonicalOrigin": origin, "routes": config, "sourceFiles": sorted(source_files, key=lambda r: r['source']), "packagedFiles": [{"path": p, "bytes": len(b), "sha256": sha(b)} for p, b in sorted(files.items())], "archive": {"path": "deploy.zip", "bytes": archive.stat().st_size, "sha256": sha(archive.read_bytes())}, "sitemapLastModified": dates, "sitemapLastModifiedPolicy": release["lastModifiedPolicy"], "publicWrites": []}
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    (output / "README.md").write_text((RUNTIME / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
    rollback = f"# Rollback reference\n\nNo deployment was made by packaging. Immediately before release, re-read production and confirm it is still deployment `{baseline['deploymentId']}`. If it changed, reconcile again.\n\n- v4 archive name: `{baseline['archiveName']}`\n- SHA-256: `{baseline['archiveSha256']}`\n- Custody: {baseline['archiveCustody']}\n- Archive verified during this build: {rollback_archive is not None}\n- Cloudflare Pages project: `{release['project']}`\n- Existing production runtime: {baseline['runtime']}.\n\nBefore release, verify recovery availability and the archive with `--rollback-archive PATH`. A build without that argument does not prove backup availability. After an authorized release, use Cloudflare's rollback to the verified v4 production deployment if new routing or site content fails. DNS, domain registrar, MX/TXT records, provider settings, and Search Console are outside this package.\n"
    (output / "ROLLBACK.md").write_text(rollback, encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--release-context", type=Path, default=RUNTIME / "release-context.json")
    parser.add_argument("--rollback-archive", type=Path, help="Optional church-controlled v4 archive to verify before release; not copied into output")
    args = parser.parse_args()
    try:
        result = build(args.site, args.out, args.release_context, args.rollback_archive)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Package not created: {exc}")
    print(json.dumps({"output": str(args.out.resolve()), "pages": len(result['routes']['pages']), "packagedFiles": len(result['packagedFiles']), "zipSha256": result['archive']['sha256'], "deployed": False}, indent=2))
