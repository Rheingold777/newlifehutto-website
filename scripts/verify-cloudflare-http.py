"""Exercise the actual Wrangler Pages server using HTTP, not a router mock."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base", required=True)
parser.add_argument("--package", type=Path, required=True)
args = parser.parse_args()
base = urlsplit(args.base)
if base.hostname not in {"localhost", "127.0.0.1", "::1"}:
    raise SystemExit("This verifier is for local Wrangler servers only")
manifest = json.loads((args.package / "manifest.json").read_text(encoding="utf-8"))
checks = []


def request(path, method="GET", host=None):
    cls = http.client.HTTPSConnection if base.scheme == "https" else http.client.HTTPConnection
    conn = cls(base.hostname, base.port, timeout=15)
    headers = {"Host": host} if host else {}
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    result = response.status, dict((k.lower(), v) for k, v in response.getheaders()), response.read()
    conn.close()
    return result


def check(name, condition, detail=None):
    checks.append({"check": name, "passed": bool(condition), "detail": detail})


for route, asset in manifest["routes"]["pages"].items():
    status, headers, body = request(route)
    expected = (args.package / "deploy" / asset.lstrip("/")).read_bytes()
    check(f"canonical page {route}", status == 200 and body == expected and headers.get("content-type", "").startswith("text/html"), status)
    check(f"local noindex {route}", "noindex" in headers.get("x-robots-tag", ""))
    status, headers, body = request(route, "HEAD")
    check(f"HEAD {route}", status == 200 and body == b"")
    for alias in {route.rstrip("/") or "/index.html", route + "index.html"}:
        status, headers, body = request(alias + "?a=x%2By&a=c+d")
        check(f"canonical alias {alias}", status == 301 and headers.get("location") == route + "?a=x%2By&a=c+d", headers.get("location"))

for path in manifest["routes"]["assets"]:
    status, headers, body = request(path)
    expected = (args.package / "deploy" / path.lstrip("/")).read_bytes()
    # Preview robots intentionally differs; all other public asset bytes match.
    check(f"asset {path}", status == 200 and (b"Disallow: /" in body if path == "/robots.txt" else body == expected), status)

for old, target in manifest["routes"]["legacyRedirects"].items():
    for slash in ["", "/"]:
        status, headers, body = request(old + slash + "?source=old%20link")
        check(f"legacy {old}{slash}", status == 301 and headers.get("location") == target + "?source=old%20link")
        status, headers, body = request(old + slash + "?source=old%20link", host="www.newlifehutto.com")
        check(f"combined www/HTTP/legacy {old}{slash}", status == 301 and headers.get("location") == manifest["canonicalOrigin"] + target + "?source=old%20link", headers.get("location"))

for path in ["/kids", "/youth", "/upcoming-events", "/your-salvation-matters", "/es/", "/sermons/", "/blog/", "/missing-page/", "/assets/missing.png", "/_worker.js", "/_routes.json", "/_nlh-pages/home.page", "/404.html", "/manifest.json"]:
    for method in ["GET", "HEAD"]:
        status, headers, body = request(path, method)
        check(f"real 404 {method} {path}", status == 404 and "noindex" in headers.get("x-robots-tag", "") and (not body if method == "HEAD" else b"We couldn't find that page" in body), status)

for path in ["/v%69sit", "/v%69sit/"]:
    status, headers, body = request(path + "?ref=encoded")
    check(f"safe encoded route {path}", status == 301 and headers.get("location") == "/visit/?ref=encoded")

for path in ["/assets%2fcss/refinement.css", "/visit%5c", "/%00", "/%FF", "/%E0%A4%A", "/%252e%252e", "/.env", "/assets/.private", "//visit/"]:
    status, headers, body = request(path)
    check(f"invalid path {path}", status == 400, status)

# Standards-compliant URL parsing may collapse dot segments before the Worker.
# Both rejection and a normalized known route are safe; no file traversal occurs.
for path in ["/assets/../visit/", "/assets/%2e%2e/visit/", "/assets/../../.env"]:
    status, headers, body = request(path)
    allowed = status == 400 or (path != "/assets/../../.env" and status == 200 and b'newlifehutto.com/visit/' in body)
    check(f"normalized traversal cannot escape route map {path}", allowed, status)

for method in ["POST", "PUT", "DELETE", "OPTIONS"]:
    status, headers, body = request("/contact/", method)
    check(f"unsupported method {method}", status == 405 and headers.get("allow") == "GET, HEAD", status)

status, headers, body = request("/visit/?ref=maps", host="www.newlifehutto.com")
check("www HTTPS destination preserves path/query", status == 301 and headers.get("location") == "https://newlifehutto.com/visit/?ref=maps")
status, headers, body = request("/visit/?ref=maps", host="newlifehutto.com")
check("HTTP apex upgrade preserves path/query", status == 301 and headers.get("location") == "https://newlifehutto.com/visit/?ref=maps")
sitemap = ElementTree.fromstring((args.package / "deploy" / "sitemap.xml").read_bytes())
locations = [e.text for e in sitemap.findall("{*}url/{*}loc")]
check("sitemap contains only 14 canonical routes", set(locations) == {manifest["canonicalOrigin"] + p for p in manifest["routes"]["pages"]} and len(locations) == 14)
check("public robots permits crawling", b"Allow: /" in (args.package / "deploy" / "robots.txt").read_bytes())
check("ZIP hash matches manifest", hashlib.sha256((args.package / "deploy.zip").read_bytes()).hexdigest() == manifest["archive"]["sha256"])
report = {"kind": "Actual local Wrangler Pages/workerd HTTP checks", "base": args.base, "package": str(args.package.resolve()), "passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks), "checks": checks, "limitations": ["Local workerd does not establish production account settings or deployment health.", "The Node unit suite separately verifies native HTTPS apex behavior without a redirect.", "No public deployment, browser analytics execution, form submission, or provider action occurred."]}
(args.package / "http-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: report[k] for k in ["kind", "passed", "failed"]}, indent=2))
for item in checks:
    if not item["passed"]:
        print("FAIL", item["check"], item["detail"])
raise SystemExit(1 if report["failed"] else 0)
