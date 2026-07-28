# -*- coding: utf-8 -*-
"""US-001: Test artifact notes (备注) field — create, patch, list.

Run: python test_notes.py
Must pass on 1st run AND 2nd run (clean state).
"""

import json
import os
import sys
import tempfile
import time
import uuid

# Point to the backend source
SRC_DIR = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, SRC_DIR)

from qwenpaw_artifact_library_store import (
    DATA_ROOT,
    DATA_FILE,
    create_artifact,
    list_artifacts,
    get_artifact,
    patch_artifact,
    move_to_trash,
)

PASS = 0
FAIL = 0


def check(label: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  —  {detail}")


def main():
    # ── 0. cleanup leftover from previous aborted run ──
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        original_len = len(data)
        data = [d for d in data if d.get("project") != "us001-test-notes"]
        if len(data) != original_len:
            DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("  🧹 已清理上次运行的测试记录\n")

    # ── 1. create a temp file to register ──
    fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="us001_notes_test_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("US-001 test artifact for notes field\n")

    test_notes_original = "这个是第一次登记的备注"
    test_notes_updated = "这个是用 PATCH 更新后的备注"
    project_name = "us001-test-notes"
    artifact_id: str | None = None

    try:
        # ── 2. create with notes ──
        print("\n── Step 1: create_artifact with notes ──")
        created = create_artifact(
            path=tmp_path,
            title="US001 Test Artifact",
            summary="用于测试 notes 字段的产物",
            project=project_name,
            deliverable="test-notes-deliverable",
            tags=["test", "notes"],
            notes=test_notes_original,
        )
        artifact_id = created["id"]
        check("返回了 id", bool(created.get("id")))
        check("notes 字段存在", "notes" in created)
        check(
            "notes 值正确",
            created.get("notes") == test_notes_original,
            f"期望 '{test_notes_original}', 得到 '{created.get('notes')}'",
        )

        # ── 3. get_artifact and verify notes ──
        print("\n── Step 2: get_artifact — verify notes ──")
        fetched = get_artifact(artifact_id)
        check("get_artifact 返回 notes 字段", "notes" in fetched)
        check(
            "notes 值一致",
            fetched.get("notes") == test_notes_original,
            f"期望 '{test_notes_original}', 得到 '{fetched.get('notes')}'",
        )

        # ── 4. PATCH notes ──
        print("\n── Step 3: patch_artifact — update notes ──")
        patched = patch_artifact(artifact_id, {"notes": test_notes_updated})
        check("patch 返回 notes 字段", "notes" in patched)
        check(
            "notes 已更新",
            patched.get("notes") == test_notes_updated,
            f"期望 '{test_notes_updated}', 得到 '{patched.get('notes')}'",
        )

        # re-fetch to confirm persistence
        refetched = get_artifact(artifact_id)
        check(
            "持久化确认",
            refetched.get("notes") == test_notes_updated,
            f"期望 '{test_notes_updated}', 得到 '{refetched.get('notes')}'",
        )

        # ── 5. list_artifacts — verify notes field present ──
        print("\n── Step 4: list_artifacts — verify notes visible ──")
        items = list_artifacts(project=project_name)
        found = [i for i in items if i.get("id") == artifact_id]
        check("列表中找到刚创建的产物", len(found) == 1, f"找到 {len(found)} 条")
        if found:
            check("列表中 notes 字段存在", "notes" in found[0])
            check(
                "列表中 notes 值正确",
                found[0].get("notes") == test_notes_updated,
                f"期望 '{test_notes_updated}', 得到 '{found[0].get('notes')}'",
            )

        # ── 6. empty notes test ──
        print("\n── Step 5: create with empty notes (default) ──")
        fd2, tmp_path2 = tempfile.mkstemp(suffix=".txt", prefix="us001_notes_empty_")
        with os.fdopen(fd2, "w", encoding="utf-8") as f:
            f.write("empty notes test\n")
        created2 = create_artifact(
            path=tmp_path2,
            title="US001 Empty Notes",
            summary="无备注测试",
            project=project_name,
            notes="",
        )
        check("空备注产物创建成功", bool(created2.get("id")))
        check("notes 字段为默认空字符串", created2.get("notes") == "")
        # cleanup (file is already moved to trash by move_to_trash)
        move_to_trash(created2["id"])
        if os.path.exists(tmp_path2):
            os.unlink(tmp_path2)

    finally:
        # ── cleanup: trash the test artifact & delete temp file ──
        if artifact_id:
            try:
                move_to_trash(artifact_id)
            except Exception:
                pass  # may already be cleaned
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # ── summary ──
    print(f"\n{'='*40}")
    print(f"  通过: {PASS}  /  失败: {FAIL}")
    if FAIL == 0:
        print("  🎉 ALL TESTS PASSED")
    else:
        print(f"  💥 {FAIL} 个测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
