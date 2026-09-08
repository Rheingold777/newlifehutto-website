"""Verify native HTTPS/apex behavior on a loopback Wrangler Pages TLS server.

The self-signed certificate is accepted only on this hardcoded loopback test
connection. Host headers test the Worker logic without making public requests.
"""
import argparse
import http.client
import json
from pathlib import Path
import ssl

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", type=Path, required=True)
parser.add_argument("--port", type=int, default=8788)
args = parser.parse_args()
package = args.package
manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
checks = []


def request(path, host):
    conn = http.client.HTTPSConnection("127.0.0.1", args.port, context=ssl._create_unverified_context(), timeout=15)
    conn.request("GET", path, headers={"Host": host})
    response = conn.getresponse()
    result = response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
    conn.close()
    return result


for route, asset in manifest["routes"]["pages"].items():
    status, headers, body = request(route, "newlifehutto.com")
    expected = (package / "deploy" / asset.lstrip("/")).read_bytes()
    checks.append({"route": route, "check": "HTTPS apex direct 200, exact body, no noindex", "passed": status == 200 and body == expected and "noindex" not in headers.get("x-robots-tag", ""), "status": status, "robots": headers.get("x-robots-tag")})

cases = [
    ("/visit?x=a%2Bb", "www.newlifehutto.com", 301, "https://newlifehutto.com/visit/?x=a%2Bb"),
    ("/new-here?x=a%2Bb", "www.newlifehutto.com", 301, "https://newlifehutto.com/visit/?x=a%2Bb"),
    ("/missing/", "newlifehutto.com", 404, None),
    ("/_nlh-pages/home.page", "newlifehutto.com", 404, None),
    ("/robots.txt", "newlifehutto.com", 200, None),
    ("/visit/", "candidate.newlifehutto.pages.dev", 200, None),
]
for path, host, expected_status, location in cases:
    status, headers, body = request(path, host)
    ok = status == expected_status and headers.get("location") == location
    if path == "/robots.txt":
        ok &= b"Allow: /" in body and "noindex" not in headers.get("x-robots-tag", "")
    if host.endswith(".pages.dev") or status == 404:
        ok &= "noindex" in headers.get("x-robots-tag", "")
    checks.append({"route": path, "host": host, "passed": ok, "status": status, "location": headers.get("location"), "robots": headers.get("x-robots-tag")})

report = {"kind": "Actual local Wrangler Pages/workerd HTTPS checks", "passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks), "checks": checks, "tlsScope": "Loopback self-signed dev certificate; certificate verification disabled for 127.0.0.1 only. No public request or production TLS claim."}
(package / "https-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: report[k] for k in ["kind", "passed", "failed"]}, indent=2))
for check in checks:
    if not check["passed"]:
        print(check)
raise SystemExit(1 if report["failed"] else 0)
