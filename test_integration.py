"""US-005: Comprehensive end-to-end integration test for artifact-library v0.3.1.

Tests all features together: notes, stats, export, batch operations.
Must be runnable independently with clean state each time.
"""
from __future__ import annotations
import sys, os, json, tempfile, shutil

# Mock qwenpaw for standalone test context
import types
for mod_name in ["qwenpaw", "qwenpaw.plugins", "qwenpaw.plugins.api"]:
    parts = mod_name.split(".")
    mod = None
    for i, p in enumerate(parts):
        full = ".".join(parts[:i+1])
        if full not in sys.modules:
            m = types.ModuleType(full)
            if i == 0:
                m.plugins = types.ModuleType("qwenpaw.plugins")
                sys.modules["qwenpaw.plugins"] = m.plugins
            sys.modules[full] = m

class MockPluginApi:
    def register_http_router(self, router, **kw): pass
    def register_tool(self, **kw): pass
    def register_skill_provider(self, **kw): pass

sys.modules["qwenpaw.plugins.api"].PluginApi = MockPluginApi

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Use temp directory for test data
TEST_DATA = tempfile.mkdtemp()
os.environ["APPDATA"] = TEST_DATA

from qwenpaw_artifact_library_store import (
    create_artifact, list_artifacts, get_artifact,
    patch_artifact, move_to_trash,
    get_stats, export_artifacts, batch_update, batch_delete,
    DATA_ROOT, DATA_FILE
)
# Force a clean metadata file so source-tree legacy data/artifacts.json cannot
# leak into the integration test. The shipped package does not include data/.
DATA_ROOT.mkdir(parents=True, exist_ok=True)
DATA_FILE.write_text("[]", encoding="utf-8")
from fastapi.testclient import TestClient
from fastapi import FastAPI
from plugin import router

app = FastAPI()
app.include_router(router, prefix="/artifact-library")
client = TestClient(app)

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f": {detail}" if detail else ""))

def setup_module():
    if os.path.exists(TEST_DATA):
        shutil.rmtree(TEST_DATA)
    os.makedirs(TEST_DATA)

# ──────────────────────────────────────────
# 1. Build verification
# ──────────────────────────────────────────
print("=" * 60)
print("🔧 1. Build Verification")
print("=" * 60)

manifest_version = json.loads(open(os.path.join(os.path.dirname(__file__), "plugin.json"), encoding="utf-8").read())["version"]
build_zip = os.path.join(os.path.dirname(__file__), f"qwenpaw-artifact-library-{manifest_version}.zip")
if os.path.exists(build_zip):
    import zipfile
    with zipfile.ZipFile(build_zip) as zf:
        names = zf.namelist()
    check("ZIP exists", True)
    check("ZIP contains plugin.json", "plugin.json" in names)
    check("ZIP contains backend/plugin.py", "backend/plugin.py" in names)
    check("ZIP contains backend/qwenpaw_artifact_library_store.py",
          "backend/qwenpaw_artifact_library_store.py" in names)
    frontend_entry = json.loads(zipfile.ZipFile(build_zip).read("plugin.json"))["entry"]["frontend"]
    check("ZIP contains ui/index.js compatibility copy", "ui/index.js" in names)
    check("ZIP contains versioned frontend entry", frontend_entry in names, frontend_entry)
    check("ZIP contains skills/artifact-register/SKILL.md",
          "skills/artifact-register/SKILL.md" in names)
    check("ZIP contains README.md", "README.md" in names)
    
    with zipfile.ZipFile(build_zip) as zf:
        pj = json.loads(zf.read("plugin.json"))
    check(f"plugin.json version is {manifest_version}", pj.get("version") == manifest_version, str(pj.get("version")))
else:
    check("ZIP exists", False, "Build package not found at " + build_zip)

# ──────────────────────────────────────────
# 2. Notes Field
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print("📝 2. Notes Field Tests")
print("=" * 60)

# Create temp files first
for fname in ["test1.txt", "test_nonotes.txt", "img.png", "doc.pdf", "code.py"]:
    with open(os.path.join(TEST_DATA, fname), "w") as f:
        f.write("test content")

# Create with notes
a1 = create_artifact(
    path=os.path.join(TEST_DATA, "test1.txt"),
    title="Integration Test Artifact 1",
    summary="Testing integration of all features",
    project="TestProj",
    notes="This is a test note for integration testing"
)
check("Create artifact with notes", a1.get("notes") == "This is a test note for integration testing",
      str(a1.get("notes")))

# Verify notes in GET
g1 = get_artifact(a1["id"])
check("GET returns notes field", g1.get("notes") == "This is a test note for integration testing",
      str(g1.get("notes")))

# PATCH notes
a1_updated = patch_artifact(a1["id"], {"notes": "Updated note for integration test"})
check("PATCH notes updates correctly", a1_updated.get("notes") == "Updated note for integration test",
      str(a1_updated.get("notes")))

# Verify in list
all_items = list_artifacts()
check("List contains notes field",
      any(x["id"] == a1["id"] and x.get("notes") == "Updated note for integration test"
          for x in all_items))

# Create artifact without notes (default)
a_no_notes = create_artifact(
    path=os.path.join(TEST_DATA, "test_nonotes.txt"),
    title="No Notes Artifact",
    summary="Artifact without notes",
    project="TestProj"
)
check("Create without notes defaults to empty string",
      a_no_notes.get("notes") == "",
      str(a_no_notes.get("notes")))

# ──────────────────────────────────────────
# 3. Stats
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print("📊 3. Stats Tests")
print("=" * 60)

# Create more artifacts for diverse stats
create_artifact(path=os.path.join(TEST_DATA, "img.png"), title="Image Artifact",
                summary="An image", project="P1", artifact_type="image")
create_artifact(path=os.path.join(TEST_DATA, "doc.pdf"), title="PDF Artifact",
                summary="A document", project="P2", artifact_type="document")
create_artifact(path=os.path.join(TEST_DATA, "code.py"), title="Code Artifact",
                summary="Some code", project="P1", artifact_type="code",
                status="final")

stats = get_stats()
check("Stats total >= 5", stats["total"] >= 5, str(stats["total"]))
check("Stats has by_project", "by_project" in stats)
check("Stats has by_type", "by_type" in stats)
check("Stats has by_status", "by_status" in stats)
check("Stats P1 count >= 2", stats["by_project"].get("P1", 0) >= 2,
      str(stats["by_project"]))
check("Stats final status count >= 1", stats["by_status"].get("final", 0) >= 1,
      str(stats["by_status"]))

# Stats via API
r = client.get("/artifact-library/stats")
check("GET /stats returns 200", r.status_code == 200)
sdata = r.json()
check("GET /stats has total key", "total" in sdata)

# ──────────────────────────────────────────
# 4. Export
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print("📤 4. Export Tests")
print("=" * 60)

# JSON export
content, media_type, filename = export_artifacts("json")
parsed = json.loads(content)
check("Export JSON parses correctly", isinstance(parsed, dict))
check("Export JSON has items", len(parsed.get("items", [])) >= 5)
check("Export JSON has count", parsed.get("count", 0) >= 5)
check("Export JSON media type", "json" in media_type)
check("Export JSON filename ends with .json", filename.endswith(".json"))

r = client.get("/artifact-library/export?format=json")
check("GET /export?format=json returns 200", r.status_code == 200)
check("GET export JSON content-type", "json" in r.headers.get("content-type", ""))

# CSV export
content_csv, ct_csv, fn_csv = export_artifacts("csv")
check("Export CSV has header", "id,title,summary" in content_csv[:60])
check("Export CSV has notes column", "notes" in content_csv[:200])
check("Export CSV filename", fn_csv.endswith(".csv"))

r = client.get("/artifact-library/export?format=csv")
check("GET /export?format=csv returns 200", r.status_code == 200)
check("GET export CSV content-type", "csv" in r.headers.get("content-type", ""))

# MD export
content_md, ct_md, fn_md = export_artifacts("markdown")
check("Export MD has title", "# 产物库导出" in content_md)
check("Export MD has items", "## " in content_md)
check("Export MD filename", fn_md.endswith(".md"))

r = client.get("/artifact-library/export?format=markdown")
check("GET /export?format=markdown returns 200", r.status_code == 200)

# ──────────────────────────────────────────
# 5. Batch Operations
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print("🔄 5. Batch Operations Tests")
print("=" * 60)

# Get all current items
all_before = list_artifacts()
item_ids = [x["id"] for x in all_before if x.get("status") != "trashed"]

# Batch update project
batch_items = [{"id": iid, "project": "BatchProj"} for iid in item_ids[:3]]
result = batch_update(batch_items)
check("Batch update returns correct count", len(result) == min(3, len(item_ids)),
      f"got {len(result)}, expected {min(3, len(item_ids))}")

# Verify updates persisted
all_after = list_artifacts()
updated_count = sum(1 for x in all_after if x.get("project") == "BatchProj")
check("Batch update persists", updated_count >= min(3, len(item_ids)),
      f"found {updated_count} with BatchProj")

# Batch update via API
if len(item_ids) >= 2:
    r = client.post("/artifact-library/batch", json={
        "items": [{"id": item_ids[0], "artifact_type": "code"}]
    })
    check("POST /batch returns 200", r.status_code == 200)
    check("POST /batch returns updated count", r.json().get("updated", 0) == 1,
          str(r.json()))

# Batch delete
if len(item_ids) >= 2:
    existing_ids = [x["id"] for x in all_before if x.get("status") != "trashed" and x.get("file_exists")]
    delete_ids = existing_ids[-2:] if len(existing_ids) >= 2 else existing_ids
    del_count = batch_delete(delete_ids)
    check("Batch delete returns correct count", del_count == len(delete_ids),
          f"got {del_count}, expected {len(delete_ids)}")

    # Verify trashed
    all_trashed = list_artifacts(include_trashed=True)
    trashed_count = sum(1 for x in all_trashed if x["id"] in delete_ids and x.get("status") == "trashed")
    check("Batch delete actually trashed items",
          trashed_count == len(delete_ids),
          f"found {trashed_count} trashed out of {len(delete_ids)}")

    # Batch delete via API
    r = client.post("/artifact-library/batch/delete", json={"ids": [delete_ids[0]]})
    check("POST /batch/delete returns 200", r.status_code == 200)

# Missing-file batch delete must skip and not claim success
missing_path = os.path.join(TEST_DATA, "missing-target.txt")
with open(missing_path, "w") as f:
    f.write("will be removed before batch delete")
missing_art = create_artifact(path=missing_path, title="Missing File", summary="Missing file behavior", project="MissingProj")
os.unlink(missing_path)
missing_count = batch_delete([missing_art["id"]])
check("Batch delete skips missing files", missing_count == 0, str(missing_count))

# Batch no-op cases
r = client.post("/artifact-library/batch", json={"items": []})
check("POST /batch with empty list", r.status_code == 200 and r.json()["updated"] == 0)

r = client.post("/artifact-library/batch/delete", json={"ids": []})
check("POST /batch/delete with empty list", r.status_code == 200 and r.json()["deleted"] == 0)

# ──────────────────────────────────────────
# 6. JS Syntax Check (if Node available)
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print("🔍 6. JS Syntax Check")
print("=" * 60)

import subprocess
result = subprocess.run(
    ["node", "--check",
     os.path.join(os.path.dirname(__file__), "ui", "index.js")],
    capture_output=True, text=True, timeout=15
)
check("JS syntax check passes", result.returncode == 0, result.stderr)

# ──────────────────────────────────────────
# Summary
# ──────────────────────────────────────────
print("\n" + "=" * 60)
print(f"📋 INTEGRATION TEST SUMMARY")
print("=" * 60)
total = PASS + FAIL
print(f"  Total: {total}  |  Passed: {PASS}  |  Failed: {FAIL}")
if FAIL == 0:
    print("  ✅ ALL INTEGRATION TESTS PASSED!")
else:
    print(f"  ❌ {FAIL} test(s) FAILED — fix before publishing")

sys.exit(0 if FAIL == 0 else 1)
