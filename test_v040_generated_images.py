# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, sqlite3, tempfile, shutil, types
from pathlib import Path

for mod_name in ["qwenpaw", "qwenpaw.plugins", "qwenpaw.plugins.api"]:
    parts = mod_name.split(".")
    for i, _ in enumerate(parts):
        full = ".".join(parts[:i+1])
        if full not in sys.modules:
            sys.modules[full] = types.ModuleType(full)
class MockPluginApi:
    def register_http_router(self, *a, **k): pass
    def register_tool(self, *a, **k): pass
    def register_skill_provider(self, *a, **k): pass
sys.modules["qwenpaw.plugins.api"].PluginApi = MockPluginApi

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
TEST_APPDATA = tempfile.mkdtemp(prefix="artifact-v040-")
os.environ["APPDATA"] = TEST_APPDATA
IMG_DB_DIR = Path(tempfile.mkdtemp(prefix="image-gen-db-"))
IMG_DB = IMG_DB_DIR / "image_gen.db"
os.environ["QWENPAW_IMAGE_GEN_DB"] = str(IMG_DB)

try:
    from qwenpaw_artifact_library_store import DATA_ROOT, DATA_FILE, import_image_gen_gallery, list_generated_images, generated_image_facets, image_gen_source_status, patch_artifact
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text("[]", encoding="utf-8")

    img1 = IMG_DB_DIR / "img1.png"; img1.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 128)
    img2 = IMG_DB_DIR / "img2.png"; img2.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 128)
    conn = sqlite3.connect(str(IMG_DB))
    conn.executescript("""
    CREATE TABLE gallery_images(
      id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT, file_name TEXT, file_size INTEGER,
      width INTEGER, height INTEGER, prompt TEXT, negative_prompt TEXT, model_name TEXT,
      lora_name TEXT, workflow_id INTEGER, steps INTEGER, cfg REAL, seed INTEGER,
      rating INTEGER, notes TEXT, deleted INTEGER DEFAULT 0, created_at TEXT, generated_at TEXT
    );
    """)
    conn.execute("INSERT INTO gallery_images(file_path,file_name,file_size,width,height,prompt,negative_prompt,model_name,lora_name,workflow_id,steps,cfg,seed,rating,notes,deleted,created_at,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (str(img1), "img1.png", img1.stat().st_size, 768, 768, "blue girl", "bad hands", "waiIllustriousSDXL_v170.safetensors", "luotianyi.safetensors", 1, 28, 6.5, 12345, 5, "好图", 0, "2026-07-28 10:00:00", "2026-07-28 10:00:00"))
    conn.execute("INSERT INTO gallery_images(file_path,file_name,file_size,width,height,prompt,negative_prompt,model_name,lora_name,workflow_id,steps,cfg,seed,rating,notes,deleted,created_at,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (str(img2), "img2.png", img2.stat().st_size, 1024, 1024, "red city", "", "JuggernautXL_Ragnarok_ByRunDiffusion.safetensors", "", 1, 20, 7.0, 222, 3, "", 0, "2026-07-28 11:00:00", "2026-07-28 11:00:00"))
    conn.commit(); conn.close()

    st = image_gen_source_status()
    assert st["available"] and st["active"] == 2, st
    r1 = import_image_gen_gallery(project="生图图库")
    assert r1["imported"] == 2 and r1["skipped"] == 0, r1
    r2 = import_image_gen_gallery(project="生图图库")
    assert r2["imported"] == 0 and r2["skipped"] == 2, r2
    all_imgs = list_generated_images()
    assert len(all_imgs) == 2, all_imgs
    assert all(x["asset_category"] == "generated_image" for x in all_imgs)
    five = list_generated_images(min_rating=5)
    assert len(five) == 1 and five[0]["generation_meta"]["rating"] == 5, five
    wai = list_generated_images(model_name="waiIllustriousSDXL_v170.safetensors")
    assert len(wai) == 1 and "blue girl" in wai[0]["generation_meta"]["prompt"], wai
    facets = generated_image_facets()
    assert facets["total"] == 2 and facets["models"]["waiIllustriousSDXL_v170.safetensors"] == 1, facets
    updated = patch_artifact(five[0]["id"], {"notes":"更新备注", "generation_meta": {**five[0]["generation_meta"], "rating": 4}})
    assert updated["notes"] == "更新备注" and updated["generation_meta"]["rating"] == 4, updated
    print("v0.4.0 generated image tests passed")
finally:
    shutil.rmtree(TEST_APPDATA, ignore_errors=True)
    shutil.rmtree(IMG_DB_DIR, ignore_errors=True)
