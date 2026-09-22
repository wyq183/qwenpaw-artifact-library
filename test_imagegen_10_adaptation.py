# -*- coding: utf-8 -*-
"""隔离验证：生图助手图库导入、旧记录路径修复、图片预览文件可读。

自包含设计：本测试自建临时生图助手数据库，不依赖本机真实图库状态，
因此生图助手迁移目录、清理旧文件或本机无图库时同样可稳定运行。
"""
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

tmp = Path(tempfile.mkdtemp(prefix="artifact_library_imagegen_adapt_"))

# 1) 自建一个临时「生图助手」图库，模拟 1.0+ 的 gallery_images 结构。
img_dir = tmp / "images"
img_dir.mkdir(parents=True, exist_ok=True)
live_image = img_dir / "image_gen_00001_.png"
try:
    from PIL import Image as _Image
    _Image.new("RGB", (64, 64), (120, 160, 220)).save(live_image, "PNG")
except Exception:  # pragma: no cover - PIL 不可用时退化为最小合法 PNG
    import struct, zlib
    def _chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00" + bytes([200, 100, 50] * 2)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw))
           + _chunk(b"IEND", b""))
    live_image.write_bytes(png)

img_db = tmp / "image_gen.db"
conn = sqlite3.connect(str(img_db))
conn.execute("""
    CREATE TABLE gallery_images (
        id INTEGER PRIMARY KEY, file_path TEXT, file_name TEXT, file_size INTEGER,
        width INTEGER, height INTEGER, prompt TEXT, negative_prompt TEXT,
        model_name TEXT, lora_name TEXT, category TEXT, workflow_id INTEGER,
        steps INTEGER, cfg REAL, seed INTEGER, rating INTEGER, notes TEXT,
        deleted INTEGER DEFAULT 0, created_at TEXT, generated_at TEXT
    )
""")
conn.execute(
    "INSERT INTO gallery_images (id, file_path, file_name, file_size, width, height, prompt, "
    "negative_prompt, model_name, lora_name, category, steps, cfg, seed, rating, notes, deleted, "
    "created_at, generated_at) VALUES (1, ?, ?, 136, 64, 64, 'example prompt', 'example negative', "
    "'example-model.safetensors', '', '测试分类', 20, 7.0, 1234, 5, '', 0, "
    "'2026-01-01 10:00:00', '2026-01-01 09:59:00')",
    (str(live_image), live_image.name),
)
conn.commit()
conn.close()

# 产物库测试数据落到临时目录，不污染真实数据。
os.environ["APPDATA"] = str(tmp)
os.environ["QWENPAW_IMAGE_GEN_DB"] = str(img_db)

import qwenpaw_artifact_library_store as store  # noqa: E402

# 2) 模拟旧版产物库记录：登记时文件存在，随后旧缓存被清理（源文件消失）。
old_path = tmp / "missing_old_cache.png"
old_path.write_bytes(live_image.read_bytes())
old = store.create_artifact(
    path=str(old_path), title="旧缓存生图", summary="旧记录", project="生图图库",
    artifact_type="image", asset_category="generated_image",
    source_plugin="qwenpaw-image-gen", source_id="1",
    generation_meta={"prompt": "old"},
)
old_path.unlink()
assert store.get_artifact(old["id"])["file_exists"] is False

# 3) 从图库导入：同一 source_id 的失效记录应被原地修复。
r = store.import_image_gen_gallery("生图图库")
assert r["repaired"] == 1, r
assert r["imported"] + r["repaired"] > 0, r

# 4) 修复后必须指向真实存在的文件，且可生成缩略图。
item = store.get_artifact(old["id"])
assert item["file_exists"] is True, item
assert Path(item["path"]).is_file(), item["path"]
assert item["generation_meta"]["category"] == "测试分类", item["generation_meta"]
assert item["generation_meta"]["rating"] == 5, item["generation_meta"]
thumb = store.thumbnail_path(old["id"])
assert thumb.is_file() and thumb.stat().st_size > 0, thumb

# 5) 再次导入必须幂等：不能新建重复记录，也不能再次修复。
r2 = store.import_image_gen_gallery("生图图库")
assert r2["imported"] == 0 and r2["repaired"] == 0, r2

# 6) 源文件再次消失时，清理接口应只回收失效记录。
live_image.unlink()
cleaned = store.cleanup_missing_generated_images()
assert cleaned["cleaned"] == 1, cleaned

print(json.dumps({
    "temp": str(tmp),
    "first": {k: r[k] for k in ("imported", "repaired", "skipped")},
    "second": {k: r2[k] for k in ("imported", "repaired", "skipped")},
    "thumbnail": str(thumb),
    "cleanup": cleaned,
}, ensure_ascii=False))
print("✅ 生图助手适配测试通过（导入 / 路径修复 / 缩略图 / 幂等 / 失效清理）")
