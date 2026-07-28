from __future__ import annotations
import json
import re
import shutil
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
package = root / "package"
if package.exists():
    shutil.rmtree(package)
(package / "backend").mkdir(parents=True)
(package / "ui").mkdir()
(package / "skills" / "artifact-register").mkdir(parents=True)

# Package only reviewable runtime files. No development data, source archives,
# test fixtures, local paths, build cache, or historical modules are shipped.
manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
version = manifest["version"]
frontend_entry = manifest.get("entry", {}).get("frontend", "ui/index.js")
versioned_frontend = f"ui/index.v{version}.js"
if frontend_entry != versioned_frontend:
    raise SystemExit(f"plugin.json entry.frontend must be {versioned_frontend}, got {frontend_entry}")
if not re.fullmatch(r"ui/index\.v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?\.js", frontend_entry):
    raise SystemExit(f"unexpected frontend entry path: {frontend_entry}")

for source, target in [
    (root / "README.md", package / "README.md"),
    (root / "requirements.txt", package / "requirements.txt"),
    (root / "backend" / "plugin.py", package / "backend" / "plugin.py"),
    (root / "backend" / "qwenpaw_artifact_library_store.py", package / "backend" / "qwenpaw_artifact_library_store.py"),
    (root / "ui" / "index.js", package / "ui" / "index.js"),
    (root / "ui" / "index.js", package / frontend_entry),
    (root / "skills" / "artifact-register" / "SKILL.md", package / "skills" / "artifact-register" / "SKILL.md"),
]:
    shutil.copy2(source, target)

(package / "plugin.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

zip_path = root / f"qwenpaw-artifact-library-{manifest['version']}.zip"
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(package.rglob("*")):
        if path.is_file():
            zf.write(path, path.relative_to(package).as_posix())
print(zip_path)
print(zip_path.stat().st_size)
print("\\n".join(str(p.relative_to(package)) for p in sorted(package.rglob("*")) if p.is_file()))
