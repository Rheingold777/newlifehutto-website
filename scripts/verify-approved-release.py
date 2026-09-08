"""Compare every generated deploy file with the approved, versioned SHA-256 set."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", type=Path, required=True)
args = parser.parse_args()
expected = json.loads((ROOT / "config/approved-release-2026-09-08.json").read_text())
folder = args.package / "deploy"
actual = {p.relative_to(folder).as_posix(): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size} for p in folder.rglob("*") if p.is_file()}
wanted = {p["path"]: {"sha256": p["sha256"], "bytes": p["bytes"]} for p in expected["files"]}
assert actual == wanted, f"Deploy bytes differ from the approved release: {sorted(k for k in actual.keys() | wanted.keys() if actual.get(k) != wanted.get(k))}"
manifest = json.loads((args.package / "manifest.json").read_text())
assert {p["path"]: {"sha256": p["sha256"], "bytes": p["bytes"]} for p in manifest["packagedFiles"]} == actual
zip_sha = hashlib.sha256((args.package / "deploy.zip").read_bytes()).hexdigest()
assert zip_sha == manifest["archive"]["sha256"]
print(json.dumps({"approved_deploy_files": len(actual), "all_file_hashes_match": True, "zip_manifest_matches": True, "original_zip_hash_matches": zip_sha == expected["archiveSha256"]}))
