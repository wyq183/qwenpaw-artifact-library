# Browser Community Upload

Use this skill when you need to upload a QwenPaw plugin ZIP to the AgentScope community platform using browser automation. This skill covers **only the browser upload part** — not packaging, not testing, not GitHub release.

## Prerequisites

Before starting, make sure:

- [ ] Plugin ZIP is ready (e.g. `qwenpaw-artifact-library-0.5.1.zip`)
- [ ] Plugin has been pushed to GitHub and a GitHub Release has been created
- [ ] You know the ZIP's local path and the GitHub Release URL
- [ ] The user's Edge browser login is saved in `--user-data-dir=C:\temp\chromebrowser_use`

## Step 1: Start Edge Browser

Always use Edge. Never use Chrome (Chrome's single-instance mode opens tabs in existing windows, causing memory bloat).

```javascript
browser_use(action="start", headed=True,
  executable_path="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  browser_args="--user-data-dir=C:\\temp\\chromebrowser_use --no-first-run")
```

## Step 2: Open Community Upload Page

Navigate to the platform:

```javascript
browser_use(action="open", url="https://platform.agentscope.io/plugins/publish?pluginId=qwenpaw-artifact-library&mode=version")
```

If that's not the right plugin, use the alternate path:
- Go to `https://platform.agentscope.io/`
- Log in (if needed) — browser should auto-login from saved session
- Navigate to personal homepage → 插件 Plugin tab → find the plugin card → click "more" → "上传新版本"

## Step 3: Upload the ZIP File

### Method A: File Upload (Recommended)

```javascript
// Step 3a: First, look for a file input. Snapshot to get refs.
browser_use(action="snapshot")

// Step 3b: If there's a "选择文件" button, click it then upload
browser_use(action="click", ref="eXX")  // the 选择文件 button
// Then immediately:
browser_use(action="file_upload",
  selector="input[type=file]",
  paths_json='["C:\\Users\\Administrator\\Desktop\\qwenpaw-artifact-library-0.5.1.zip"]')

// OR: if you can't click then upload, try direct file_upload first
browser_use(action="file_upload",
  selector="input[type=file]",
  paths_json='["C:\\path\\to\\your\\plugin.zip"]')
```

**IMPORTANT**: If the platform shows an error saying the plugin already exists, you must first remove the old entry:
1. Click the "×" button next to the old upload
2. Wait for the field to clear
3. Then upload the new one

If the form keeps the old state, refresh the page and start fresh.

### Method B: URL Upload (GitHub Release)

If file upload doesn't work, use the GitHub Release URL:

```javascript
// Step 3a: Find the URL input field and paste the GitHub Release ZIP URL
browser_use(action="snapshot")
browser_use(action="type", ref="eXX",
  text="https://github.com/wyq183/qwenpaw-artifact-library/releases/download/v0.5.1/qwenpaw-artifact-library-0.5.1.zip")

// Step 3b: Click "解析URL" button to let the platform parse it
browser_use(action="click", ref="eYY")
// Wait for parsing
browser_use(action="wait_for", wait_time=3)
browser_use(action="snapshot")
```

## Step 4: Verify Parsed Results

After upload/parse, the platform auto-reads `plugin.json`. Check:

- ✅ **名称** shows plugin name (read-only)
- ✅ **版本** shows X.Y.Z (read-only)
- ✅ **QwenPaw 最低版本** shows a value like `2.0.1` — if empty, the form will reject!
  - Fix: Add `"min_version": "X.Y.Z"` to `plugin.json`, rebuild ZIP, re-upload
- ✅ **前端入口** shows versioned path like `ui/index.vX.Y.Z.js`
- ✅ **后端入口** shows `backend/plugin.py`

## Step 5: Fill Manual Fields

### Fill version changelog

```javascript
// Find the 版本变更说明 textarea and type the changelog
browser_use(action="snapshot")
browser_use(action="type", ref="eXX",
  text="v0.5.1 修复：\n- 生图库改用真实生成时间排序\n- 删除"送回生图助手"功能\n- 优化视图切换入口\n- 前端缓存彻底根治")
```

### Fill source repository URL

```javascript
// The repo URL might be auto-filled from previous upload.
// If the form shows "请输入一个有效的github仓库地址" error:
// Select all text, delete, then re-type the full URL
browser_use(action="press_key", ref="eXX", key="Control+a")
browser_use(action="press_key", ref="eXX", key="Delete")
browser_use(action="type", ref="eXX",
  text="https://github.com/wyq183/qwenpaw-artifact-library")
```

**IMPORTANT**: The repo URL validation is VERY picky:
- Must include `https://`
- Must not have trailing slash
- Add `.git` suffix if validation fails
- If it still fails: delete ALL text → click somewhere else to blur → re-type from scratch

### Check the agreement checkbox

```javascript
// Find the Apache 2.0 agreement checkbox and click it
browser_use(action="snapshot")
browser_use(action="click", ref="eXX")  // the checkbox
```

## Step 6: Click Next Step

```javascript
browser_use(action="snapshot")
browser_use(action="click", ref="eXX")  // "下一步" button

// Wait for the preview page to load
browser_use(action="wait_for", wait_time=5)
browser_use(action="snapshot")
```

**If the button does nothing**:
1. Refresh the page: `browser_use(action="navigate", url="https://platform.agentscope.io/plugins/publish?pluginId=...&mode=version")`
2. Start over from Step 3
3. The form state is cached in React — only a full refresh clears it

## Step 7: Preview & Submit

On the preview page, verify:
- README renders correctly
- Version is X.Y.Z
- All features are listed

```javascript
// Click 提交扫描
browser_use(action="click", ref="eXX")  // "提交扫描" button

// Wait for scan result
browser_use(action="wait_for", wait_time=10)
browser_use(action="snapshot")
```

After submitting, the plugin appears in **插件草稿箱** tab with status **"扫描中"**. Eventually it changes to **"已扫描"** or **"安全"**.

## Step 8: Close Browser

```javascript
browser_use(action="stop")
```

## Common Pitfalls & Fixes

### Button clicks do nothing
**Root cause**: React state not synced — old file state cached.  
**Fix**: Refresh page → re-upload ZIP → re-fill all fields.

### "请输入一个有效的github仓库地址"
**Root cause**: Stale form validation from previous upload.  
**Fix**: `Control+a` + `Delete` + re-type `https://github.com/...` from scratch.  
**Last resort**: Add `.git` suffix.

### "QwenPaw 最低版本" empty
**Root cause**: `plugin.json` missing the top-level `min_version` field.  
**Fix**:
```json
{
  "qwenpaw_version": { "min": "2.0.1" },
  "min_version": "2.0.1"
}
```
Rebuild package, re-upload.

### Upload says "该插件已存在"
**Root cause**: Uploading a new version over an existing entry. The form has a stale old file.  
**Fix**: Click the "×" to remove old file → upload new ZIP. Or refresh page and start fresh.

### Cannot find the right buttons in snapshot
The platform UI uses buttons with text like "选择文件", "解析URL", "下一步", "提交扫描", "more". Use evaluate to find them:

```javascript
// Find button by text and get its ref
browser_use(action="eval", code="
  (() => {
    const btns = document.querySelectorAll('button');
    const target = Array.from(btns).find(x => x.innerText.includes('下一步'));
    if (target) {
      target.scrollIntoView({block:'center'});
      target.style.outline = '3px solid red';
      return 'found: ' + target.innerText;
    }
    return 'not found';
  })()
")
browser_use(action="snapshot")
// Now the button should be visible in snapshot
browser_use(action="click", ref="eXX")
```

### XHR debugging (advanced)
The platform uses XMLHttpRequest, not fetch. To debug submit failures:

```javascript
browser_use(action="eval", code="
  (() => {
    window.__xhrLogs = [];
    const OrigXHR = window.XMLHttpRequest;
    function WrappedXHR() {
      const xhr = new OrigXHR();
      xhr.addEventListener('loadend', function() {
        if (this.responseURL.includes('/api/v1/plugins'))
          window.__xhrLogs.push({url: this.responseURL, status: this.status, response: this.responseText.slice(0,500)});
      });
      return xhr;
    }
    window.XMLHttpRequest = WrappedXHR;
    return 'xhr hook installed';
  })()
")
// After clicking submit, read logs:
browser_use(action="eval", code="window.__xhrLogs")
```

## Quick Reference: Full Upload Flow

```
1. browser_use(start, headed, Edge)
2. browser_use(open, platform URL)
3. browser_use(snapshot)
4. browser_use(file_upload, paths_json=["..."])   — upload ZIP
5. browser_use(wait_for, 3) + snapshot             — verify parsed
6. browser_use(type, "版本变更说明", changelog)    — fill changelog
7. browser_use(type, "源码仓库地址", repo URL)     — fill repo
8. browser_use(click, checkbox)                     — agree
9. browser_use(click, "下一步")                     — next
10. browser_use(wait_for, 5) + snapshot             — preview
11. browser_use(click, "提交扫描")                  — submit
12. browser_use(wait_for, 10) + snapshot            — verify
13. browser_use(stop)                               — done
```

## ⚠️ Golden Rules

1. **If a button click does nothing → Refresh the page and start over.** Don't try to fix the React state — it won't work.
2. **Always use Edge** with `--user-data-dir=C:\temp\chromebrowser_use` for saved login.
3. **Keep max 3 tabs open** — close extra tabs after snapshot.
4. **Take snapshots after every action** so you can see what's happening.
5. **If the form rejects the repo URL → Delete all text → Blur → Re-type.** Don't paste, don't append.
