# -*- coding: utf-8 -*-
"""QwenPaw Artifact Library — backend routes and agent registration tool."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

PLUGIN_DIR = Path(__file__).resolve().parent
# Plugin loaders may execute the entry from a different working directory.
# Import sibling modules by absolute path instead of relying on cwd.
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from qwenpaw.plugins.api import PluginApi

from artifact_store import (
    STATUS_LABELS,
    TYPE_LABELS,
    create_artifact,
    get_artifact,
    list_artifacts,
    move_to_trash,
    patch_artifact,
)

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


class ArtifactPatch(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    project: Optional[str] = None
    deliverable: Optional[str] = None
    artifact_type: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=f"产物库操作失败：{exc}")


@router.get("/artifacts")
def api_list_artifacts(
    query: str = "",
    project: str = "",
    artifact_type: str = "",
    status: str = "",
    include_trashed: bool = False,
):
    try:
        return {"items": list_artifacts(query, project, artifact_type, status, include_trashed), "type_labels": TYPE_LABELS, "status_labels": STATUS_LABELS}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/artifacts/{artifact_id}")
def api_get_artifact(artifact_id: str):
    try:
        return get_artifact(artifact_id)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/artifacts", status_code=201)
def api_create_artifact(payload: ArtifactCreate):
    try:
        return create_artifact(**payload.model_dump())
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/artifacts/{artifact_id}")
def api_patch_artifact(artifact_id: str, payload: ArtifactPatch):
    try:
        return patch_artifact(artifact_id, payload.model_dump(exclude_none=True))
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/artifacts/{artifact_id}/trash")
def api_trash_artifact(artifact_id: str):
    try:
        return move_to_trash(artifact_id)
    except Exception as exc:
        raise _http_error(exc) from exc


def register_artifact(
    path: str,
    title: str,
    summary: str,
    project: str,
    deliverable: str = "",
    artifact_type: str = "",
    tags: list[str] | None = None,
    status: str = "delivered",
) -> dict[str, Any]:
    """Register a formal agent deliverable in the Artifact Library.

    Args:
        path: Absolute or workspace-relative path to an existing ordinary file.
        title: Human-readable artifact title.
        summary: One sentence explaining what it is and its intended use.
        project: Broad project name, e.g. "运动会物料" or "荒野曙光".
        deliverable: Specific deliverable/slot inside the project, e.g. "主视觉KV".
            Leave empty only when the title itself is the deliverable.
        artifact_type: image/document/web/code/video/audio/archive/data/other.
            Leave empty to infer from file extension.
        tags: Optional short retrieval tags.
        status: draft/delivered/final. A new final automatically archives an
            old final with the same project + deliverable + type.
    """
    try:
        item = create_artifact(
            path=path, title=title, summary=summary, project=project,
            deliverable=deliverable, artifact_type=artifact_type, tags=tags,
            status=status,
        )
        message = f"已登记至产物库：{item['title']}（{TYPE_LABELS[item['artifact_type']]}·{STATUS_LABELS[item['status']]}）"
        if item.get("demoted_final_ids"):
            message += f"；已归档 {len(item['demoted_final_ids'])} 个旧最终版"
        return {"success": True, "message": message, "artifact": item}
    except Exception as exc:
        return {"success": False, "message": f"登记失败：{exc}"}


class ArtifactLibraryPlugin:
    """Register the API and artifact tool through the stable PluginApi."""

    def register(self, api: PluginApi) -> None:
        api.register_http_router(router, prefix="/artifact-library", tags=["artifact-library"])
        api.register_tool(
            tool_name="register_artifact",
            tool_func=register_artifact,
            description=(
                "登记一个已经真实生成、值得长期保留的正式产物到产物库。"
                "仅在文件已写入磁盘且属于交付成果时调用；不要登记临时文件、缓存、日志或测试文件。"
                "同一项目、同一交付项、同一类型只能有一个最终版；登记新最终版会自动归档旧最终版。"
            ),
            icon="▣",
            enabled=True,
            tool_type="file",
            target_param="path",
        )


plugin = ArtifactLibraryPlugin()
