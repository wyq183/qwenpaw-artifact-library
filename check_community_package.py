# -*- coding: utf-8 -*-
"""发布前：检查 ZIP 白名单与典型个人化数据。"""
from pathlib import Path
import json, sys, tempfile, zipfile, re
root = Path(__file__).resolve().parent
package = root / "qwenpaw-artifact-library-*.zip"
package = sorted(root.glob("qwenpaw-artifact-library-*.zip"))[-1] if list(root.glob("qwenpaw-artifact-library-*.zip")) else root / "qwenpaw-artifact-library-0.5.0.zip"
# 白名单用正则表达式匹配：只允许指定模式的路径
allowed_patterns = [
    r"^plugin\.json$", r"^README\.md$", r"^requirements\.txt$",
    r"^backend/plugin\.py$", r"^backend/qwenpaw_artifact_library_store\.py$",
    r"^ui/index\.js$", r"^ui/index\.v\d+\.\d+\.\d+\.js$",
    r"^skills/artifact-register/SKILL\.md$",
]
# 隐私检查模式：用通用正则替代个人化关键词
privacy_patterns = [
    r"[A-Z]:\\\\Users\\\\.+",            # Windows 用户路径
    r"[A-Z]:\\\\baidunetdiskdownload",   # 百度网盘路径
    r"\bwyq183\b",                       # GitHub 账号
    r"\btoken173\b",                     # API 中转站
    r"[\u4e00-\u9fff]{2,5}(曙光|深渊|之歌|之剑|天依)",  # 中文作品/角色名
]
assert package.is_file(), f"未找到包：{package}"
version = re.search(r"(\d+\.\d+\.\d+)", package.name).group(1) if re.search(r"(\d+\.\d+\.\d+)", package.name) else "0.0.0"
with zipfile.ZipFile(package) as z:
    names = set(z.namelist())
    for name in names:
        ok = any(re.match(pat, name) for pat in allowed_patterns)
        assert ok, f"意外文件：{name}"
    plugin = json.loads(z.read("plugin.json"))
    assert plugin["version"] == version, f"版本不匹配：{plugin['version']} vs {version}"
    assert plugin["entry"]["frontend"] == f"ui/index.v{version}.js"
    frontend = z.read(plugin["entry"]["frontend"]).decode("utf-8")
    assert f'var PLUGIN_VERSION = "{version}";' in frontend, "前端运行时版本必须与清单一致"
    assert plugin.get("min_version"), "缺少市场最低版本"
    hits = []
    for name in names:
        text = z.read(name).decode("utf-8", errors="ignore")
        for pat in privacy_patterns:
            m = re.search(pat, text)
            if m:
                hits.append((name, pat, m.group()[:60]))
    assert not hits, f"发现可能的个人化数据：{hits}"
    assert not any(n.endswith((".db", ".png", ".jpg", ".log", ".zip")) for n in names), "禁止打入数据或二进制产物"
print(f"社区包检查通过：{package.name} — 文件白名单、版本入口、最低版本、隐私词扫描均正常")
