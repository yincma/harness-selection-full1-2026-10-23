"""Verify distributed bytes and excerpt hashes. Does not verify undistributed originals."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'SHA256SUMS.json').read_text())
bad=[]
for rel,expected in manifest.items():
    p=root/rel
    actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if actual!=expected:bad.append(rel)
for e in json.loads((root/'provenance.json').read_text())['sources']:
    p=root/e['excerpt_path']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=e['published_excerpt_sha256']:bad.append(e['excerpt_path'])
print(json.dumps({'files_checked':len(manifest),'mismatches':bad},ensure_ascii=False))
raise SystemExit(bool(bad))
