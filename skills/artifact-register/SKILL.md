# artifact-register

Use this skill to register agent deliverables in the Artifact Library when the agent completes a task that produces a file worth keeping.

## When to trigger

Trigger when any of these conditions are met:
- You generated a deliverable file (zip, exe, PDF, image, PPT, doc, CSV, etc.)
- The user says "登记到产物库" or "register this"
- You completed a project task that produces a real output file
- A task's completion criteria include registering the artifact

## How to use

Call the `register_artifact` tool with these parameters:

- `path` (required): Full path to the file on disk
- `title` (required): Display name for the artifact
- `summary` (required): What this is and what it solves
- `project` (required): Project name
- `deliverable`: What kind of deliverable (defaults to title)
- `artifact_type`: One of image, document, web, code, video, audio, archive, data, other (auto-detected if omitted)
- `tags`: Array of keyword tags
- `status`: One of draft, delivered, final (defaults to "delivered")
- `notes`: Optional remarks for later review

## Example

```
register_artifact(
  path="C:\\output\\report.pdf",
  title="季度总结报告",
  summary="2026 Q3 项目总结，包含核心指标与改进建议",
  project="项目A",
  tags=["报告","季度"],
  notes="可选备注"
)
```

## Important notes

- Only register files that were actually generated and saved to disk
- Do NOT register temporary files, logs, caches, or test data
- Same project + same deliverable + same type = only one "final" version; registering new final auto-archives the old one
- The API returns success/failure message
