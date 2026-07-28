# -*- coding: utf-8 -*-
"""QwenPaw Artifact Library — backend routes and agent registration tool."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Optional

PLUGIN_DIR = Path(__file__).resolve().parent
if str(PLUGIN_DIR) not in sys.path: sys.path.insert(0, str(PLUGIN_DIR))
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from qwenpaw.plugins.api import PluginApi
from qwenpaw_artifact_library_store import (STATUS_LABELS, TYPE_LABELS, choose_file, copy_artifact_path_to_clipboard, copy_artifact_to_clipboard, create_artifact, get_artifact, inspect_file, list_artifacts, media_info, move_to_trash, patch_artifact, reveal_in_folder, text_preview, thumbnail_path, get_stats, export_artifacts, batch_update, batch_delete, import_image_gen_gallery, list_generated_images, generated_image_facets, image_gen_source_status, send_generated_image_to_image_gen)

router = APIRouter()
class ArtifactCreate(BaseModel):
    path: str
    title: str
    summary: str
    project: str
    deliverable: str = ""
    artifact_type: str = ""
    tags: list[str] = Field(default_factory=list)
    status: str = "delivered"
    notes: str = ""
    asset_category: str = "general"
    source_plugin: str = ""
    source_id: str = ""
    generation_meta: dict[str, Any] = Field(default_factory=dict)

class ArtifactPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    summary: Optional[str] = None
    project: Optional[str] = None
    deliverable: Optional[str] = None
    artifact_type: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    asset_category: Optional[str] = None
    generation_meta: Optional[dict[str, Any]] = None
class BatchUpdatePayload(BaseModel):
    items: list[dict[str, Any]]
class BatchDeletePayload(BaseModel):
    ids: list[str]
class ImportImageGenPayload(BaseModel):
    project: str = "生图图库"
    limit: int = 0

def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (FileNotFoundError, KeyError)): return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError): return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=f"产物库操作失败：{exc}")

@router.get("/artifacts")
def api_list_artifacts(query:str="", project:str="", artifact_type:str="", status:str="", include_trashed:bool=False):
    try: return {"items":list_artifacts(query,project,artifact_type,status,include_trashed),"type_labels":TYPE_LABELS,"status_labels":STATUS_LABELS}
    except Exception as exc: raise _http_error(exc) from exc
@router.get("/artifacts/{artifact_id}")
def api_get_artifact(artifact_id:str):
    try: return get_artifact(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/artifacts",status_code=201)
def api_create_artifact(payload:ArtifactCreate):
    try: return create_artifact(**payload.model_dump())
    except Exception as exc: raise _http_error(exc) from exc
@router.patch("/artifacts/{artifact_id}")
def api_patch_artifact(artifact_id:str,payload:ArtifactPatch):
    try: return patch_artifact(artifact_id,payload.model_dump(exclude_none=True))
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/artifacts/{artifact_id}/trash")
def api_trash_artifact(artifact_id:str):
    try: return move_to_trash(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/picker")
def api_picker():
    try:
        path=choose_file(); return inspect_file(path)
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/artifacts/{artifact_id}/reveal")
def api_reveal(artifact_id:str):
    try: reveal_in_folder(artifact_id); return {"success":True}
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/artifacts/{artifact_id}/copy")
def api_copy_artifact(artifact_id:str):
    try: return copy_artifact_to_clipboard(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc
@router.post("/artifacts/{artifact_id}/copy-path")
def api_copy_path(artifact_id:str):
    try: return copy_artifact_path_to_clipboard(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc
@router.get("/artifacts/{artifact_id}/thumbnail")
def api_thumbnail(artifact_id:str):
    try: return FileResponse(thumbnail_path(artifact_id),media_type="image/jpeg",headers={"Cache-Control":"private, max-age=86400"})
    except Exception as exc: raise _http_error(exc) from exc
@router.get("/artifacts/{artifact_id}/image")
def api_image(artifact_id:str):
    try:
        item=get_artifact(artifact_id)
        if item.get("artifact_type")!="image": raise ValueError("该产物不是图片")
        path=Path(item["path"])
        if not path.is_file(): raise FileNotFoundError("原文件已不存在")
        return FileResponse(path,media_type=item.get("mime_type") or "application/octet-stream",headers={"Cache-Control":"private, max-age=3600"})
    except Exception as exc: raise _http_error(exc) from exc
@router.get("/artifacts/{artifact_id}/text")
def api_text(artifact_id:str):
    try: return text_preview(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc
@router.get("/artifacts/{artifact_id}/media")
def api_media(artifact_id:str):
    try: return media_info(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc

# ── US-003: 统计 / 导出 / 批量 ───────────────────────────────────────────────

@router.get("/stats")
def api_stats():
    try: return get_stats()
    except Exception as exc: raise _http_error(exc) from exc

@router.get("/export")
def api_export(format: str = "json"):
    try:
        content, media_type, filename = export_artifacts(format)
        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc: raise _http_error(exc) from exc

@router.post("/batch")
def api_batch_update(payload: BatchUpdatePayload):
    try:
        result = batch_update(payload.items)
        return {"updated": len(result), "items": result}
    except Exception as exc: raise _http_error(exc) from exc

@router.post("/batch/delete")
def api_batch_delete(payload: BatchDeletePayload):
    try:
        count = batch_delete(payload.ids)
        return {"deleted": count}
    except Exception as exc: raise _http_error(exc) from exc


# ── v0.4.0: 生图资产管理 ───────────────────────────────────────────────────

@router.get("/generated-images/source-status")
def api_generated_source_status():
    try: return image_gen_source_status()
    except Exception as exc: raise _http_error(exc) from exc

@router.post("/generated-images/import")
def api_import_generated_images(payload: ImportImageGenPayload):
    try: return import_image_gen_gallery(project=payload.project, limit=payload.limit)
    except Exception as exc: raise _http_error(exc) from exc

@router.get("/generated-images")
def api_list_generated_images(query: str = "", model_name: str = "", lora_name: str = "", min_rating: int = 0, sort: str = "newest"):
    try: return {"items": list_generated_images(query, model_name, lora_name, min_rating, sort), "facets": generated_image_facets()}
    except Exception as exc: raise _http_error(exc) from exc

@router.post("/generated-images/{artifact_id}/send-to-image-gen")
def api_send_generated_to_image_gen(artifact_id: str):
    try: return send_generated_image_to_image_gen(artifact_id)
    except Exception as exc: raise _http_error(exc) from exc

# ── Agent 工具函数 ──────────────────────────────────────────────────────────

def _cleanup_old_frontend(root_dir: Path) -> None:
    """启动时自动清理旧版本的版本化前端入口，只保留当前版本 + index.js 兼容副本。"""
    ui_dir = root_dir / "ui"
    if not ui_dir.is_dir():
        return
    try:
        pj = json.loads((root_dir / "plugin.json").read_text(encoding="utf-8"))
        version = pj.get("version", "")
    except Exception:
        return
    if not version:
        return
    current_entry = f"index.v{version}.js"
    for f in sorted(ui_dir.glob("index.*.js")):
        if f.name == current_entry or f.name == "index.js":
            continue
        try:
            f.unlink()
        except Exception:
            pass

def register_artifact(path:str,title:str,summary:str,project:str,deliverable:str="",artifact_type:str="",tags:list[str]|None=None,status:str="delivered",notes:str="",asset_category:str="general",source_plugin:str="",source_id:str="",generation_meta:dict[str,Any]|None=None)->dict[str,Any]:
    """Register a formal agent deliverable in the Artifact Library."""
    try:
        item=create_artifact(
            path=path,
            title=title,
            summary=summary,
            project=project,
            deliverable=deliverable,
            artifact_type=artifact_type,
            tags=tags,
            status=status,
            notes=notes,
            asset_category=asset_category,
            source_plugin=source_plugin,
            source_id=source_id,
            generation_meta=generation_meta or {},
        )
        message=f"已登记至产物库：{item['title']}（{TYPE_LABELS[item['artifact_type']]}·{STATUS_LABELS[item['status']]}）"
        if item.get("demoted_final_ids"): message+=f"；已归档 {len(item['demoted_final_ids'])} 个旧最终版"
        return {"success":True,"message":message,"artifact":item}
    except Exception as exc: return {"success":False,"message":f"登记失败：{exc}"}
class ArtifactLibraryPlugin:
    def register(self,api:PluginApi)->None:
        # 插件启动时清理旧版本前端，只保留当前版本入口 + 兼容副本
        _cleanup_old_frontend(PLUGIN_DIR.parent)
        api.register_http_router(router,prefix="/artifact-library",tags=["artifact-library"])
        api.register_tool(tool_name="register_artifact",tool_func=register_artifact,description="登记一个已经真实生成、值得长期保留的正式产物到产物库。仅在文件已写入磁盘且属于交付成果时调用；不要登记临时文件、缓存、日志或测试文件。同一项目、同一交付项、同一类型只能有一个最终版；登记新最终版会自动归档旧最终版。",icon="▣",enabled=True,tool_type="file",target_param="path")
        # 注册 skill provider，自动加载 skills/ 目录
        try:
            skills_dir = PLUGIN_DIR.parent / "skills"
            if skills_dir.is_dir():
                api.register_skill_provider(
                    skill_dirs=[str(skills_dir)],
                    skill_origin=__file__,
                )
        except Exception:
            pass  # 向后兼容，skill 注册失败不影响核心功能
plugin=ArtifactLibraryPlugin()
