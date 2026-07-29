# -*- coding: utf-8 -*-
"""发布前：检查 ZIP 白名单与典型个人化数据。"""
from pathlib import Path
import json, sys, tempfile, zipfile
root = Path(__file__).resolve().parent
package = root / "qwenpaw-artifact-library-0.5.0.zip"
allowed = {"plugin.json", "README.md", "requirements.txt", "backend/plugin.py", "backend/qwenpaw_artifact_library_store.py", "ui/index.js", "ui/index.v0.5.0.js", "skills/artifact-register/SKILL.md"}
banned = ["C:\\Users\\Administrator", "C:\\baidunetdiskdownload", "洛天依", "luotianyi", "Juggernaut", "waiIllustrious", "token173", "wyq183", "荒野曙光", "共鸣深渊"]
assert package.is_file(), package
with zipfile.ZipFile(package) as z:
    names = set(z.namelist())
    assert names == allowed, f"意外文件：{sorted(names ^ allowed)}"
    plugin = json.loads(z.read("plugin.json"))
    assert plugin["version"] == "0.5.0"
    assert plugin["entry"]["frontend"] == "ui/index.v0.5.0.js"
    frontend = z.read(plugin["entry"]["frontend"]).decode("utf-8")
    assert 'var PLUGIN_VERSION = "0.5.0";' in frontend, "前端运行时版本必须与清单一致"
    assert "0.4.7" not in frontend, "禁止把旧前端版本打进安装包"
    assert plugin.get("min_version"), "缺少市场最低版本"
    hits = []
    for name in names:
        text = z.read(name).decode("utf-8", errors="ignore")
        hits += [(name, term) for term in banned if term.lower() in text.lower()]
    assert not hits, f"发现个人化数据：{hits}"
    assert not any(n.endswith((".db", ".png", ".jpg", ".log", ".zip")) for n in names), "禁止打入数据或二进制产物"
print("社区包检查通过：文件白名单、版本入口、最低版本、隐私词扫描均正常")
