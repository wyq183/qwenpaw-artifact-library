# -*- coding: utf-8 -*-
"""Persistent storage and business rules for the Artifact Library."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "artifacts.json"
_LOCK = threading.RLock()

VALID_TYPES = {
    "image", "document", "web", "code", "video", "audio", "archive", "data", "other"
}
VALID_STATUSES = {"draft", "delivered", "final", "archived", "trashed"}

TYPE_LABELS = {
    "image": "图片", "document": "文档", "web": "网页", "code": "代码",
    "video": "视频", "audio": "音频", "archive": "压缩包", "data": "数据", "other": "其他",
}
STATUS_LABELS = {
    "draft": "草稿", "delivered": "已交付", "final": "最终版", "archived": "已归档", "trashed": "已移入回收站",
}

EXTENSION_TYPES = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff"},
    "document": {".txt", ".md", ".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf", ".epub"},
    "web": {".html", ".htm"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".json", ".yaml", ".yml", ".java", ".cs", ".cpp", ".c", ".vue", ".sh", ".bat", ".ps1"},
    "video": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv"},
    "audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "data": {".csv", ".tsv", ".sql", ".db", ".sqlite"},
}


def now() -> int:
    return int(time.time())


def infer_type(path: Path) -> str:
    ext = path.suffix.lower()
    for artifact_type, extensions in EXTENSION_TYPES.items():
        if ext in extensions:
            return artifact_type
    return "other"


def clean_text(value: str, max_len: int, field: str, required: bool = False) -> str:
    value = (value or "").strip()
    if required and not value:
        raise ValueError(f"{field}不能为空")
    if len(value) > max_len:
        raise ValueError(f"{field}不能超过{max_len}个字符")
    return value


def normalize_path(raw_path: str) -> Path:
    raw_path = clean_text(raw_path, 4096, "文件路径", required=True)
    path = Path(os.path.expandvars(os.path.expanduser(raw_path))).resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"文件不存在或不是普通文件：{path}")
    return path


def file_meta(path: Path) -> dict[str, Any]:
    stat = path.stat()
    mime, _ = mimetypes.guess_type(str(path))
    return {
        "path": str(path), "filename": path.name, "extension": path.suffix.lower(),
        "size_bytes": stat.st_size, "file_modified_at": int(stat.st_mtime), "mime_type": mime or "",
    }


def _load() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"产物库数据无法读取：{exc}") from exc


def _save(items: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=str(DATA_DIR), prefix=".artifacts.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, DATA_FILE)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _find(items: list[dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == artifact_id:
            return item
    raise KeyError("找不到该产物记录")


def _demote_other_finals(items: list[dict[str, Any]], current_id: str, project: str, deliverable: str, artifact_type: str, timestamp: int) -> list[str]:
    demoted: list[str] = []
    for item in items:
        if item.get("id") == current_id:
            continue
        if item.get("status") == "final" and item.get("project") == project and item.get("deliverable") == deliverable and item.get("artifact_type") == artifact_type:
            item["status"] = "archived"
            item["updated_at"] = timestamp
            demoted.append(item["id"])
    return demoted


def _record_context() -> tuple[str, str]:
    """Best-effort context. QwenPaw runtime context is optional for HTTP calls."""
    try:
        from qwenpaw.app.agent_context import get_current_agent_id  # type: ignore
        agent_id = get_current_agent_id() or "unknown"
    except Exception:
        agent_id = "unknown"
    return agent_id, ""


def create_artifact(*, path: str, title: str, summary: str, project: str, deliverable: str = "", artifact_type: str = "", tags: list[str] | None = None, status: str = "delivered", agent_id: str = "", session_id: str = "") -> dict[str, Any]:
    source = normalize_path(path)
    title = clean_text(title, 200, "显示名称", required=True)
    summary = clean_text(summary, 1000, "简述", required=True)
    project = clean_text(project, 160, "项目", required=True)
    artifact_type = (artifact_type or infer_type(source)).strip().lower()
    if artifact_type not in VALID_TYPES:
        raise ValueError("产物类型不合法")
    status = (status or "delivered").strip().lower()
    if status not in VALID_STATUSES - {"archived", "trashed"}:
        raise ValueError("登记时状态只能是草稿、已交付或最终版")
    deliverable = clean_text(deliverable, 160, "交付项") or title
    tags = [clean_text(str(t), 40, "标签") for t in (tags or []) if str(t).strip()]
    tags = list(dict.fromkeys(tags))[:12]
    context_agent, context_session = _record_context()
    timestamp = now()
    meta = file_meta(source)
    item = {
        "id": "art_" + uuid.uuid4().hex[:12],
        **meta,
        "title": title, "summary": summary, "project": project, "deliverable": deliverable,
        "artifact_type": artifact_type, "tags": tags, "status": status,
        "agent_id": agent_id or context_agent, "session_id": session_id or context_session,
        "created_at": timestamp, "updated_at": timestamp, "trashed_at": None,
    }
    with _LOCK:
        items = _load()
        # Keep duplicate registrations obvious rather than silently creating conflicting records.
        existing = next((x for x in items if x.get("path", "").lower() == str(source).lower() and x.get("status") != "trashed"), None)
        if existing:
            raise ValueError(f"这个文件已登记为产物：{existing.get('title')}（{existing.get('id')}）")
        demoted = _demote_other_finals(items, item["id"], project, deliverable, artifact_type, timestamp) if status == "final" else []
        item["demoted_final_ids"] = demoted
        items.append(item)
        _save(items)
    return item


def list_artifacts(query: str = "", project: str = "", artifact_type: str = "", status: str = "", include_trashed: bool = False) -> list[dict[str, Any]]:
    query = (query or "").strip().lower()
    with _LOCK:
        items = _load()
    result = []
    for item in items:
        if not include_trashed and item.get("status") == "trashed":
            continue
        if project and item.get("project") != project:
            continue
        if artifact_type and item.get("artifact_type") != artifact_type:
            continue
        if status and item.get("status") != status:
            continue
        haystack = " ".join([item.get("title", ""), item.get("summary", ""), item.get("project", ""), item.get("deliverable", ""), " ".join(item.get("tags", []))]).lower()
        if query and query not in haystack:
            continue
        item = dict(item)
        item["file_exists"] = Path(item["path"]).is_file()
        result.append(item)
    return sorted(result, key=lambda x: x.get("updated_at", 0), reverse=True)


def get_artifact(artifact_id: str) -> dict[str, Any]:
    with _LOCK:
        item = dict(_find(_load(), artifact_id))
    item["file_exists"] = Path(item["path"]).is_file()
    return item


def patch_artifact(artifact_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"title", "summary", "project", "deliverable", "artifact_type", "tags", "status"}
    unknown = set(patch) - allowed
    if unknown:
        raise ValueError("不支持修改的字段：" + ", ".join(sorted(unknown)))
    with _LOCK:
        items = _load()
        item = _find(items, artifact_id)
        if item.get("status") == "trashed":
            raise ValueError("已移入回收站的产物不能编辑")
        source = Path(item["path"])
        for key, value in patch.items():
            if value is None:
                continue
            if key in {"title", "summary", "project"}:
                item[key] = clean_text(str(value), 1000 if key == "summary" else 200, {"title": "显示名称", "summary": "简述", "project": "项目"}[key], required=True)
            elif key == "deliverable":
                item[key] = clean_text(str(value), 160, "交付项") or item["title"]
            elif key == "artifact_type":
                value = str(value).lower().strip()
                if value not in VALID_TYPES:
                    raise ValueError("产物类型不合法")
                item[key] = value
            elif key == "tags":
                if not isinstance(value, list):
                    raise ValueError("标签必须是数组")
                item[key] = list(dict.fromkeys(clean_text(str(v), 40, "标签") for v in value if str(v).strip()))[:12]
            elif key == "status":
                value = str(value).lower().strip()
                if value not in VALID_STATUSES - {"trashed"}:
                    raise ValueError("状态不合法")
                item[key] = value
        item["updated_at"] = now()
        if item["status"] == "final":
            item["demoted_final_ids"] = _demote_other_finals(items, item["id"], item["project"], item["deliverable"], item["artifact_type"], item["updated_at"])
        _save(items)
        return dict(item)


def move_to_trash(artifact_id: str) -> dict[str, Any]:
    try:
        from send2trash import send2trash
    except ImportError as exc:
        raise RuntimeError("缺少 send2trash 依赖，无法安全移入回收站") from exc
    with _LOCK:
        items = _load()
        item = _find(items, artifact_id)
        if item.get("status") == "trashed":
            return dict(item)
        source = Path(item["path"])
        if not source.is_file():
            raise FileNotFoundError("原文件已不存在，未执行删除")
        # send2trash uses the operating system recycle bin. Never fall back to os.remove.
        send2trash(str(source))
        item["status"] = "trashed"
        item["trashed_at"] = now()
        item["updated_at"] = item["trashed_at"]
        _save(items)
        return dict(item)
