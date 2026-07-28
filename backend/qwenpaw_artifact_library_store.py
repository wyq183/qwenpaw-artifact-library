# -*- coding: utf-8 -*-
"""Persistent storage, safe file actions and on-demand previews for Artifact Library."""

from __future__ import annotations

import ctypes
import datetime
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import wave
from pathlib import Path
from typing import Any

DATA_ROOT = Path(os.environ.get("APPDATA", str(Path.home() / ".qwenpaw"))) / "QwenPaw" / "artifact-library"
DATA_FILE = DATA_ROOT / "artifacts.json"
THUMB_DIR = DATA_ROOT / "thumbnails"
# Kept only for a one-time migration from development / v0.1 installations.
LEGACY_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "artifacts.json"
_LOCK = threading.RLock()

VALID_TYPES = {"image", "document", "web", "code", "video", "audio", "archive", "data", "other"}
VALID_STATUSES = {"draft", "delivered", "final", "archived", "trashed"}
TYPE_LABELS = {"image":"图片", "document":"文档", "web":"网页", "code":"代码", "video":"视频", "audio":"音频", "archive":"压缩包", "data":"数据", "other":"其他"}
STATUS_LABELS = {"draft":"草稿", "delivered":"已交付", "final":"最终版", "archived":"已归档", "trashed":"已移入回收站"}
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
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".tsv", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css", ".yaml", ".yml", ".java", ".cs", ".cpp", ".c", ".vue", ".sh", ".bat", ".ps1", ".sql", ".xml", ".log"}


def now() -> int:
    return int(time.time())


def infer_type(path: Path) -> str:
    ext = path.suffix.lower()
    return next((kind for kind, extensions in EXTENSION_TYPES.items() if ext in extensions), "other")


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
    return {"path": str(path), "filename": path.name, "extension": path.suffix.lower(), "size_bytes": stat.st_size,
            "file_modified_at": int(stat.st_mtime), "mime_type": mime or ""}


def _load() -> list[dict[str, Any]]:
    # v0.2 moves metadata out of the install folder so upgrades/reinstalls retain it.
    source = DATA_FILE if DATA_FILE.exists() else LEGACY_DATA_FILE
    if not source.exists():
        return []
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else []
        if source == LEGACY_DATA_FILE and items:
            _save(items)
        return items
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"产物库数据无法读取：{exc}") from exc


def _save(items: list[dict[str, Any]]) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=str(DATA_ROOT), prefix=".artifacts.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        os.replace(temporary, DATA_FILE)
    except BaseException:
        try: os.unlink(temporary)
        except OSError: pass
        raise


def _find(items: list[dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == artifact_id:
            return item
    raise KeyError("找不到该产物记录")


def _demote_other_finals(items: list[dict[str, Any]], current_id: str, project: str, deliverable: str, artifact_type: str, timestamp: int) -> list[str]:
    demoted = []
    for item in items:
        if item.get("id") != current_id and item.get("status") == "final" and item.get("project") == project and item.get("deliverable") == deliverable and item.get("artifact_type") == artifact_type:
            item["status"] = "archived"; item["updated_at"] = timestamp; demoted.append(item["id"])
    return demoted


def _record_context() -> tuple[str, str]:
    try:
        from qwenpaw.app.agent_context import get_current_agent_id  # type: ignore
        return get_current_agent_id() or "unknown", ""
    except Exception:
        return "unknown", ""


def create_artifact(*, path: str, title: str, summary: str, project: str, deliverable: str = "", artifact_type: str = "", tags: list[str] | None = None, status: str = "delivered", notes: str = "", agent_id: str = "", session_id: str = "") -> dict[str, Any]:
    source = normalize_path(path)
    title = clean_text(title, 200, "显示名称", required=True)
    summary = clean_text(summary, 1000, "简述", required=True)
    project = clean_text(project, 160, "项目", required=True)
    artifact_type = (artifact_type or infer_type(source)).strip().lower()
    if artifact_type not in VALID_TYPES: raise ValueError("产物类型不合法")
    status = (status or "delivered").strip().lower()
    if status not in VALID_STATUSES - {"archived", "trashed"}: raise ValueError("登记时状态只能是草稿、已交付或最终版")
    deliverable = clean_text(deliverable, 160, "交付项") or title
    tags = list(dict.fromkeys(clean_text(str(t), 40, "标签") for t in (tags or []) if str(t).strip()))[:12]
    notes = clean_text(notes, 2000, "备注")
    context_agent, context_session = _record_context(); timestamp = now()
    item = {"id":"art_" + uuid.uuid4().hex[:12], **file_meta(source), "title":title, "summary":summary, "project":project,
            "deliverable":deliverable, "artifact_type":artifact_type, "tags":tags, "status":status,
            "notes":notes,
            "agent_id":agent_id or context_agent, "session_id":session_id or context_session,
            "created_at":timestamp, "updated_at":timestamp, "trashed_at":None}
    with _LOCK:
        items = _load()
        existing = next((x for x in items if x.get("path", "").lower() == str(source).lower() and x.get("status") != "trashed"), None)
        if existing: raise ValueError(f"这个文件已登记为产物：{existing.get('title')}（{existing.get('id')}）")
        item["demoted_final_ids"] = _demote_other_finals(items, item["id"], project, deliverable, artifact_type, timestamp) if status == "final" else []
        items.append(item); _save(items)
    return item


def list_artifacts(query: str = "", project: str = "", artifact_type: str = "", status: str = "", include_trashed: bool = False) -> list[dict[str, Any]]:
    query = (query or "").strip().lower()
    with _LOCK: items = _load()
    result = []
    for raw in items:
        if (not include_trashed and raw.get("status") == "trashed") or (project and raw.get("project") != project) or (artifact_type and raw.get("artifact_type") != artifact_type) or (status and raw.get("status") != status): continue
        haystack = " ".join([raw.get("title", ""), raw.get("summary", ""), raw.get("project", ""), raw.get("deliverable", ""), " ".join(raw.get("tags", []))]).lower()
        if query and query not in haystack: continue
        item = dict(raw); item["file_exists"] = Path(item["path"]).is_file(); result.append(item)
    return sorted(result, key=lambda x: x.get("updated_at", 0), reverse=True)


def get_artifact(artifact_id: str) -> dict[str, Any]:
    with _LOCK: item = dict(_find(_load(), artifact_id))
    item["file_exists"] = Path(item["path"]).is_file(); return item


def patch_artifact(artifact_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"title", "summary", "project", "deliverable", "artifact_type", "tags", "status", "notes"}
    if set(patch) - allowed: raise ValueError("不支持修改的字段：" + ", ".join(sorted(set(patch)-allowed)))
    with _LOCK:
        items = _load(); item = _find(items, artifact_id)
        if item.get("status") == "trashed": raise ValueError("已移入回收站的产物不能编辑")
        for key, value in patch.items():
            if value is None: continue
            if key in {"title", "summary", "project"}:
                item[key] = clean_text(str(value), 1000 if key == "summary" else 200, {"title":"显示名称", "summary":"简述", "project":"项目"}[key], required=True)
            elif key == "deliverable": item[key] = clean_text(str(value), 160, "交付项") or item["title"]
            elif key == "notes": item[key] = clean_text(str(value), 2000, "备注")
            elif key == "artifact_type":
                if str(value).lower().strip() not in VALID_TYPES: raise ValueError("产物类型不合法")
                item[key] = str(value).lower().strip()
            elif key == "tags":
                if not isinstance(value, list): raise ValueError("标签必须是数组")
                item[key] = list(dict.fromkeys(clean_text(str(v),40,"标签") for v in value if str(v).strip()))[:12]
            elif key == "status":
                if str(value).lower().strip() not in VALID_STATUSES - {"trashed"}: raise ValueError("状态不合法")
                item[key] = str(value).lower().strip()
        item["updated_at"] = now()
        if item["status"] == "final": item["demoted_final_ids"] = _demote_other_finals(items, item["id"], item["project"], item["deliverable"], item["artifact_type"], item["updated_at"])
        _save(items); return dict(item)


def _send_to_windows_recycle_bin(source: Path) -> None:
    """Move via the Windows Shell recycle-bin namespace; never permanently delete."""
    # The embedded QwenPaw Python may not have send2trash even when the plugin
    # declares it. Shell.Application is built into Windows and keeps the same
    # safety guarantee: it moves into the Recycle Bin rather than os.remove.
    escaped = str(source).replace("'", "''")
    script = (
        "$shell=New-Object -ComObject Shell.Application;"
        "$bin=$shell.NameSpace(10);"
        f"$file=Get-Item -LiteralPath '{escaped}' -ErrorAction Stop;"
        "$bin.MoveHere($file.FullName,16); Start-Sleep -Milliseconds 300;"
        "if(Test-Path -LiteralPath $file.FullName){exit 1}"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], capture_output=True, text=True, timeout=12, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode != 0:
        raise RuntimeError("无法安全移入 Windows 回收站；已取消删除，原文件未被永久删除")


def _move_file_to_recycle_bin(source: Path) -> None:
    """Move a file to the OS recycle bin/trash without ever falling back to permanent deletion."""
    try:
        from send2trash import send2trash
        send2trash(str(source))
        return
    except Exception as first_exc:
        if os.name == "nt":
            try:
                _send_to_windows_recycle_bin(source)
                return
            except Exception as second_exc:
                raise RuntimeError(f"无法安全移入回收站：{second_exc}") from first_exc
        raise RuntimeError(f"无法安全移入回收站：{first_exc}") from first_exc


def move_to_trash(artifact_id: str) -> dict[str, Any]:
    with _LOCK:
        items = _load(); item = _find(items, artifact_id)
        if item.get("status") == "trashed": return dict(item)
        source = Path(item["path"])
        if not source.is_file(): raise FileNotFoundError("原文件已不存在，未执行删除")
        _move_file_to_recycle_bin(source)
        item["status"] = "trashed"; item["trashed_at"] = now(); item["updated_at"] = item["trashed_at"]
        _save(items); return dict(item)


def inspect_file(path: str) -> dict[str, Any]:
    source = normalize_path(path); meta = file_meta(source)
    return {**meta, "artifact_type":infer_type(source), "suggested_title":source.stem, "file_exists":True}


def choose_file() -> str:
    """Use the native Windows picker; no file is uploaded or copied."""
    if os.name != "nt": raise RuntimeError("当前版本的本地选择器仅支持 Windows")
    # A 30-second timeout prevents an abandoned native dialog from leaving the
    # browser page in a permanent loading state. Closing the dialog is treated
    # as a normal cancel, never an error.
    command = "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Title='选择要登记的正式产物'; $d.Filter='所有文件 (*.*)|*.*'; if($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){[Console]::Out.Write($d.FileName)}"
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", command], capture_output=True, text=True, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc: raise ValueError("未选择文件") from exc
    picked = result.stdout.strip()
    if not picked: raise ValueError("未选择文件")
    return str(normalize_path(picked))


def reveal_in_folder(artifact_id: str) -> None:
    item = get_artifact(artifact_id); source = Path(item["path"])
    if not source.is_file(): raise FileNotFoundError("原文件已不存在，无法定位")
    if os.name == "nt":
        # Do not use CREATE_NO_WINDOW here: explorer.exe is a GUI process and
        # some QwenPaw/Windows combinations hide it when launched via Popen.
        # ShellExecuteW reliably opens Explorer and selects the target file.
        rc = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", f'/select,"{source}"', None, 1)
        if rc <= 32:
            raise RuntimeError(f"无法打开资源管理器定位文件（ShellExecuteW={rc}）")
    else:
        raise RuntimeError("当前版本的定位功能仅支持 Windows")


def _artifact_path(artifact_id: str, expected_type: str | None = None) -> tuple[dict[str, Any], Path]:
    item = get_artifact(artifact_id); source = Path(item["path"])
    if expected_type and item.get("artifact_type") != expected_type: raise ValueError("该产物不支持此预览")
    if not source.is_file(): raise FileNotFoundError("原文件已不存在")
    return item, source


def thumbnail_path(artifact_id: str) -> Path:
    item, source = _artifact_path(artifact_id, "image")
    if source.stat().st_size > 80 * 1024 * 1024: raise ValueError("图片超过 80MB，为保护性能不生成缩略图")
    stamp = f"{source.stat().st_mtime_ns}-{source.stat().st_size}"
    key = hashlib.sha256((str(source).lower()+stamp).encode("utf-8")).hexdigest()
    output = THUMB_DIR / (key + ".jpg")
    if output.exists(): return output
    try:
        from PIL import Image, ImageOps
        with Image.open(source) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((480, 320), Image.Resampling.LANCZOS)
            if im.mode not in ("RGB", "L"): im = im.convert("RGB")
            THUMB_DIR.mkdir(parents=True, exist_ok=True)
            im.save(output, "JPEG", quality=80, optimize=True)
        return output
    except Exception as exc:
        # SVG and uncommon image formats can still be displayed by the full-preview endpoint.
        raise ValueError(f"无法生成该图片的缩略图：{exc}") from exc


def text_preview(artifact_id: str, limit: int = 16384) -> dict[str, Any]:
    item, source = _artifact_path(artifact_id)
    if source.suffix.lower() not in TEXT_EXTENSIONS: raise ValueError("该文件类型不提供文本摘要")
    if source.stat().st_size > 16 * 1024 * 1024: raise ValueError("文本文件超过 16MB，为保护性能不读取内容")
    raw = source.read_bytes()[:limit + 1]
    content = next((raw.decode(enc) for enc in ("utf-8-sig", "utf-8", "gb18030", "utf-16") if _can_decode(raw, enc)), raw.decode("utf-8", errors="replace"))
    return {"content":content[:limit], "truncated":len(raw)>limit, "language":"markdown" if source.suffix.lower()==".md" else "text", "size_bytes":item["size_bytes"]}


def _can_decode(raw: bytes, encoding: str) -> bool:
    try: raw.decode(encoding); return True
    except UnicodeDecodeError: return False


def media_info(artifact_id: str) -> dict[str, Any]:
    item, source = _artifact_path(artifact_id)
    if item.get("artifact_type") not in {"audio", "video"}: raise ValueError("该产物不是音频或视频")
    info = {"kind":item["artifact_type"], "extension":source.suffix.lower(), "size_bytes":source.stat().st_size, "duration_seconds":None, "width":None, "height":None, "bit_rate":None}
    if source.suffix.lower() == ".wav":
        try:
            with wave.open(str(source), "rb") as w: info["duration_seconds"] = round(w.getnframes() / float(w.getframerate()), 2)
        except (wave.Error, OSError): pass
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            cmd=[ffprobe,"-v","error","-show_entries","format=duration,bit_rate:stream=width,height","-of","json",str(source)]
            data=json.loads(subprocess.run(cmd,capture_output=True,text=True,timeout=4,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)).stdout or "{}")
            fmt=data.get("format",{}); streams=data.get("streams",[])
            if fmt.get("duration"): info["duration_seconds"]=round(float(fmt["duration"]),2)
            if fmt.get("bit_rate"): info["bit_rate"]=int(fmt["bit_rate"])
            stream=next((x for x in streams if x.get("width")), None)
            if stream: info["width"],info["height"]=stream.get("width"),stream.get("height")
        except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError): pass
    return info



def _run_clipboard_powershell(script: str) -> None:
    if os.name != "nt":
        raise RuntimeError("快捷分享目前仅支持 Windows")
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", script],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("写入系统剪贴板超时") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "未知错误").strip().replace("\n", " ")
        raise RuntimeError(f"无法写入系统剪贴板：{detail[:240]}")


def _ps_quote(value: str) -> str:
    return value.replace("'", "''")


def _clipboard_text(value: str) -> None:
    # Avoid shell interpolation: content is passed as Base64 UTF-16LE.
    import base64
    payload = base64.b64encode(value.encode("utf-16le")).decode("ascii")
    command = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        f"$b=[Convert]::FromBase64String('{payload}');"
        "$t=[Text.Encoding]::Unicode.GetString($b);"
        "[Windows.Forms.Clipboard]::SetText($t)"
    )
    _run_clipboard_powershell(command)


def _clipboard_image(source: Path) -> None:
    path = _ps_quote(str(source))
    command = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        f"$i=[Drawing.Image]::FromFile('{path}');"
        "try {[Windows.Forms.Clipboard]::SetImage($i)} finally {$i.Dispose()}"
    )
    _run_clipboard_powershell(command)


def _clipboard_file(source: Path) -> None:
    path = _ps_quote(str(source))
    command = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Collections;"
        "$files=New-Object System.Collections.Specialized.StringCollection;"
        f"[void]$files.Add('{path}');"
        "[Windows.Forms.Clipboard]::SetFileDropList($files)"
    )
    _run_clipboard_powershell(command)


def copy_artifact_to_clipboard(artifact_id: str) -> dict[str, str]:
    """Copy the actual artifact, not merely its path, to the Windows clipboard."""
    item, source = _artifact_path(artifact_id)
    if item.get("artifact_type") == "image":
        _clipboard_image(source)
        return {"mode": "image", "message": "图片已复制，可直接粘贴到聊天软件"}
    if source.suffix.lower() in TEXT_EXTENSIONS:
        preview = text_preview(artifact_id, limit=16 * 1024 * 1024)
        _clipboard_text(preview["content"])
        return {"mode": "text", "message": "文本内容已复制"}
    _clipboard_file(source)
    return {"mode": "file", "message": "文件已复制，可尝试直接粘贴到支持文件发送的软件"}


def copy_artifact_path_to_clipboard(artifact_id: str) -> dict[str, str]:
    """Copy only a local path. Kept separate from shortcut sharing by design."""
    _, source = _artifact_path(artifact_id)
    _clipboard_text(str(source))
    return {"mode": "path", "message": "文件路径已复制"}


# ── US-003: 统计 / 导出 / 批量 ────────────────────────────────────────────


def get_stats() -> dict[str, Any]:
    """返回统计。total 含全部记录；分类统计默认只统计未移入回收站的活动记录。"""
    with _LOCK:
        items = _load()

    total = len(items)
    active_items = [i for i in items if i.get("status") != "trashed"]

    by_project: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for item in active_items:
        p = item.get("project", "未知") or "未知"
        by_project[p] = by_project.get(p, 0) + 1
        t = item.get("artifact_type", "other") or "other"
        by_type[t] = by_type.get(t, 0) + 1
        st = item.get("status", "unknown") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total": total,
        "active": len(active_items),
        "trashed": total - len(active_items),
        "by_project": by_project,
        "by_type": by_type,
        "by_status": by_status,
    }


def export_artifacts(format: str = "json") -> tuple[str, str, str]:
    """Export all artifacts in the requested format.
    Returns (content_string, media_type, filename_suggestion)."""
    with _LOCK:
        items = _load()

    timestamp = now()

    if format == "json":
        content = json.dumps(
            {"exported_at": timestamp, "count": len(items), "items": items},
            ensure_ascii=False,
            indent=2,
        )
        return content, "application/json", f"artifacts-{timestamp}.json"

    elif format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "title",
                "summary",
                "project",
                "deliverable",
                "artifact_type",
                "tags",
                "status",
                "path",
                "size_bytes",
                "created_at",
                "updated_at",
                "notes",
            ]
        )
        for item in items:
            writer.writerow(
                [
                    item.get("id", ""),
                    item.get("title", ""),
                    item.get("summary", ""),
                    item.get("project", ""),
                    item.get("deliverable", ""),
                    item.get("artifact_type", ""),
                    ",".join(item.get("tags", []) if item.get("tags") else []),
                    item.get("status", ""),
                    item.get("path", ""),
                    item.get("size_bytes", 0),
                    item.get("created_at", ""),
                    item.get("updated_at", ""),
                    item.get("notes", ""),
                ]
            )
        return output.getvalue(), "text/csv; charset=utf-8", f"artifacts-{timestamp}.csv"

    elif format in ("md", "markdown"):
        lines = [
            f"# 产物库导出 ({datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')})",
            "",
            f"共 {len(items)} 项",
            "",
        ]
        for item in items:
            lines.append(f"## {item.get('title', '')}")
            lines.append(f"- **项目**: {item.get('project', '')}")
            lines.append(f"- **类型**: {item.get('artifact_type', '')}")
            lines.append(f"- **状态**: {item.get('status', '')}")
            lines.append(f"- **说明**: {item.get('summary', '')}")
            if item.get("notes"):
                lines.append(f"- **备注**: {item['notes']}")
            lines.append("")
        return "\n".join(lines), "text/markdown; charset=utf-8", f"artifacts-{timestamp}.md"

    else:
        raise ValueError(f"不支持的导出格式: {format}")


def batch_update(items_to_update: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量更新多个产物的 project/type/tags。
    items_to_update: [{"id": "...", "project": "...", ...}, ...]
    每个字典必须包含 "id"，其余字段可选。
    返回更新后的完整产物列表（仅成功更新的条目）。"""
    allowed_batch = {"project", "artifact_type", "tags"}
    updated = []
    with _LOCK:
        all_items = _load()
        for patch in items_to_update:
            artifact_id = patch.get("id")
            if not artifact_id:
                continue
            try:
                item = _find(all_items, artifact_id)
                if item.get("status") == "trashed":
                    continue
                changed = False
                for key, value in patch.items():
                    if key == "id" or value is None:
                        continue
                    if key not in allowed_batch:
                        continue
                    if key == "project":
                        item[key] = clean_text(str(value), 160, "项目", required=True)
                    elif key == "artifact_type":
                        v = str(value).lower().strip()
                        if v not in VALID_TYPES:
                            raise ValueError(f"类型不合法：{v}")
                        item[key] = v
                    elif key == "tags":
                        if not isinstance(value, list):
                            raise ValueError("标签必须是数组")
                        item[key] = list(
                            dict.fromkeys(
                                clean_text(str(v), 40, "标签") for v in value if str(v).strip()
                            )
                        )[:12]
                    changed = True
                if changed:
                    item["updated_at"] = now()
                    updated.append(dict(item))
            except (KeyError, ValueError):
                continue
        if updated:
            _save(all_items)
    return updated


def batch_delete(item_ids: list[str]) -> int:
    """批量移入 Windows 回收站。
    与单个删除保持一致：先安全移动原文件，再把元数据标记为 trashed。
    单项失败会跳过，绝不永久删除。返回成功处理的条目数。"""
    count = 0
    with _LOCK:
        all_items = _load()
        changed = False
        for artifact_id in item_ids:
            try:
                item = _find(all_items, artifact_id)
                if item.get("status") == "trashed":
                    continue
                source = Path(item["path"])
                if not source.is_file():
                    continue
                _move_file_to_recycle_bin(source)
                item["status"] = "trashed"
                item["trashed_at"] = now()
                item["updated_at"] = item["trashed_at"]
                count += 1
                changed = True
            except (KeyError, OSError, RuntimeError):
                continue
        if changed:
            _save(all_items)
    return count
