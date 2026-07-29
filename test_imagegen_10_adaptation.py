# -*- coding: utf-8 -*-
"""隔离验证：生图助手 1.0 图库导入、旧记录修复、图片预览文件可读。"""
import os, sys, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

# 必须在导入 store 前设置：让产物库测试数据落到临时目录，不污染真实数据。
tmp = Path(tempfile.mkdtemp(prefix="artifact_library_imagegen10_"))
os.environ["APPDATA"] = str(tmp)
os.environ["QWENPAW_IMAGE_GEN_DB"] = str(Path.home() / ".qwenpaw" / "plugins" / "qwenpaw-image-gen" / "data" / "image_gen.db")

import qwenpaw_artifact_library_store as store

# 1) 先模拟旧版产物库记录：登记时文件存在，随后旧缓存被清理。
old_path = tmp / "missing_old_cache.png"
old_path.write_bytes(b"not-a-real-image")
old = store.create_artifact(
    path=str(old_path), title="旧缓存生图", summary="旧记录", project="生图图库",
    artifact_type="image", asset_category="generated_image", source_plugin="qwenpaw-image-gen", source_id="1",
    generation_meta={"prompt":"old"},
)
old_path.unlink()
assert store.get_artifact(old["id"])["file_exists"] is False

# 2) 从真实 1.0 图库导入：应修复 id=1，并导入其余真实图片。
r = store.import_image_gen_gallery("生图图库")
assert r["repaired"] == 1, r
assert r["imported"] + r["repaired"] > 0, r

# 3) 修复后必须指向真实存在的文件，且可生成缩略图。
item = store.get_artifact(old["id"])
assert item["file_exists"] is True, item
assert Path(item["path"]).is_file(), item["path"]
thumb = store.thumbnail_path(old["id"])
assert thumb.is_file() and thumb.stat().st_size > 0, thumb

# 4) 再次导入必须幂等：不能新建重复记录，也不能再次修复。
r2 = store.import_image_gen_gallery("生图图库")
assert r2["imported"] == 0 and r2["repaired"] == 0, r2
print(json.dumps({"temp":str(tmp), "first": {k:r[k] for k in ("imported","repaired","skipped")}, "second": {k:r2[k] for k in ("imported","repaired","skipped")}, "thumbnail":str(thumb)}, ensure_ascii=False))
