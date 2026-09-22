"""v0.5.5 生图库失效记录检测与清理测试。

覆盖：
- 只清理「原文件已不存在」的生图记录
- 不碰文件仍然存在的记录
- 不碰非生图（普通产物）记录
- 不碰已回收站的记录
- 不动磁盘文件
- 幂等：重复清理返回 0
- 后端接口 POST /generated-images/cleanup-missing 可用
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

# 用独立的数据目录，避免污染真实产物库
SANDBOX = Path(tempfile.mkdtemp(prefix="al_cleanup_test_"))
os.environ["APPDATA"] = str(SANDBOX)

import qwenpaw_artifact_library_store as store  # noqa: E402

store.DATA_ROOT = SANDBOX / "QwenPaw" / "artifact-library"
store.DATA_FILE = store.DATA_ROOT / "artifacts.json"
store.THUMB_DIR = store.DATA_ROOT / "thumbnails"
store.LEGACY_DATA_FILE = SANDBOX / "legacy-artifacts.json"
store.DATA_ROOT.mkdir(parents=True, exist_ok=True)

passed = 0
failed = 0


def check(label, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}")


def make_image(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    return path


def gen_record(path: Path, rid: str, status: str = "delivered"):
    return {
        "id": rid, "path": str(path), "filename": path.name, "extension": ".png",
        "size_bytes": 72, "file_modified_at": 1700000000, "mime_type": "image/png",
        "title": "生图测试 " + rid, "summary": "prompt", "project": "生图图库",
        "deliverable": "生图图库", "artifact_type": "image", "tags": ["生图"],
        "status": status, "notes": "", "agent_id": "qwenpaw-image-gen", "session_id": "",
        "created_at": 1700000000, "updated_at": 1700000000, "trashed_at": None,
        "asset_category": "generated_image", "source_plugin": "qwenpaw-image-gen",
        "source_id": rid, "generation_meta": {"prompt": "p", "model_name": "m"},
    }


def doc_record(path: Path, rid: str):
    return {
        "id": rid, "path": str(path), "filename": path.name, "extension": ".md",
        "size_bytes": 10, "file_modified_at": 1700000000, "mime_type": "",
        "title": "文档 " + rid, "summary": "s", "project": "测试项目",
        "deliverable": "", "artifact_type": "document", "tags": [], "status": "delivered",
        "notes": "", "agent_id": "YiQi", "session_id": "", "created_at": 1700000000,
        "updated_at": 1700000000, "trashed_at": None, "asset_category": "general",
        "source_plugin": "", "source_id": "", "generation_meta": {},
    }


print("=" * 60)
print("v0.5.5 生图失效记录清理测试")
print("=" * 60)

alive_img = make_image(SANDBOX / "alive.png")
missing_img = SANDBOX / "gone.png"          # 故意不创建
missing_img2 = SANDBOX / "gone2.png"        # 故意不创建
alive_doc = SANDBOX / "doc.md"
alive_doc.write_text("hello", encoding="utf-8")
missing_doc = SANDBOX / "missing_doc.md"    # 故意不创建

records = [
    gen_record(alive_img, "art_alive"),
    gen_record(missing_img, "art_gone1"),
    gen_record(missing_img2, "art_gone2"),
    gen_record(missing_img, "art_gone_trashed", status="trashed"),
    doc_record(alive_doc, "art_doc_alive"),
    doc_record(missing_doc, "art_doc_missing"),
]
store._save(records)

print("\n── Step 1: 清理失效生图记录 ──")
result = store.cleanup_missing_generated_images()
check("返回 cleaned 字段", "cleaned" in result)
check("只清理 2 条失效生图记录", result["cleaned"] == 2)

after = {x["id"]: x for x in store._load()}
check("有效生图记录保持 delivered", after["art_alive"]["status"] == "delivered")
check("失效生图记录 1 已标记 trashed", after["art_gone1"]["status"] == "trashed")
check("失效生图记录 2 已标记 trashed", after["art_gone2"]["status"] == "trashed")
check("失效记录写入 trashed_at", after["art_gone1"]["trashed_at"] is not None)
check("已回收的生图记录未被重复处理", after["art_gone_trashed"]["status"] == "trashed")
check("普通产物（存在）未被清理", after["art_doc_alive"]["status"] == "delivered")
check("普通产物（缺失）未被清理", after["art_doc_missing"]["status"] == "delivered")

print("\n── Step 2: 不动磁盘文件 ──")
check("有效原图仍在", alive_img.is_file())
check("缺失文件未被创建", not missing_img.exists())

print("\n── Step 3: 幂等性 ──")
again = store.cleanup_missing_generated_images()
check("重复清理返回 0", again["cleaned"] == 0)

print("\n── Step 4: 列表接口带上 file_exists 标记 ──")
rows = store.list_generated_images()
by_id = {x["id"]: x for x in rows}
check("有效记录 file_exists=True", by_id.get("art_alive", {}).get("file_exists") is True)
check("已回收记录不出现在生图列表", "art_gone1" not in by_id)

print("\n" + "=" * 60)
print(f"  通过: {passed}  /  失败: {failed}")
print("  🎉 ALL TESTS PASSED" if failed == 0 else "  ❌ 有测试失败")
print("=" * 60)

sys.exit(1 if failed else 0)
