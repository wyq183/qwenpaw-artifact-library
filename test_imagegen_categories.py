# -*- coding: utf-8 -*-
"""验证生图助手分类单向同步、更新与筛选。仅使用临时产物库数据。"""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))
tmp = Path(tempfile.mkdtemp(prefix="artifact_library_categories_"))
os.environ["APPDATA"] = str(tmp)
os.environ["QWENPAW_IMAGE_GEN_DB"] = str(Path.home() / ".qwenpaw" / "plugins" / "qwenpaw-image-gen" / "data" / "image_gen.db")
import qwenpaw_artifact_library_store as store

first = store.import_image_gen_gallery("测试项目")
rows = store.list_generated_images()
assert rows and all("category" in (x.get("generation_meta") or {}) for x in rows), "导入必须保存生图分类"
facets = store.generated_image_facets()
assert facets.get("categories"), "分类统计不能为空"
category = next(iter(facets["categories"]))
filtered = store.list_generated_images(category=category)
assert filtered and all((x.get("generation_meta") or {}).get("category") == category for x in filtered)
# 第二次同步必须幂等，健康且元数据未变时不重复写入。
second = store.import_image_gen_gallery("测试项目")
assert second["imported"] == 0 and second["repaired"] == 0, second
# 模拟生图助手随后修改分类：下一次同步应更新已有元数据，不创建重复项。
source_id = rows[0]["source_id"]
old_category = (rows[0].get("generation_meta") or {}).get("category")
store._image_gen_rows = lambda _db: [{"id": source_id, "file_path": rows[0]["path"], "file_name": Path(rows[0]["path"]).name, "category": "同步测试分类", "prompt": "", "negative_prompt": "", "model_name": "", "lora_name": "", "rating": 0, "steps": 0, "cfg": 0, "seed": 0, "width": 0, "height": 0, "created_at": ""}]
third = store.import_image_gen_gallery("测试项目")
assert third["imported"] == 0 and third["repaired"] == 1, third
changed = store.list_generated_images(category="同步测试分类")
assert len(changed) == 1 and (changed[0].get("generation_meta") or {}).get("category") == "同步测试分类", changed
print({"first": {k:first[k] for k in ("imported","repaired","skipped")}, "categories":facets["categories"], "filtered":len(filtered), "second": {k:second[k] for k in ("imported","repaired","skipped")}, "changed_category_from":old_category, "third": {k:third[k] for k in ("imported","repaired","skipped")}})
