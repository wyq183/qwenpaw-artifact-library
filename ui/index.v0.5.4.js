/* QwenPaw Artifact Library — runtime frontend plugin. v0.5.1 */
(function () {
  var Q = window.QwenPaw;
  if (!Q || !Q.host) return console.error("[artifact-library] Host SDK unavailable");
  var React = Q.host.React, antd = Q.host.antd, h = React.createElement;
  var Button = antd.Button, Input = antd.Input, Select = antd.Select, Tag = antd.Tag,
    Table = antd.Table, Empty = antd.Empty, Modal = antd.Modal, Drawer = antd.Drawer,
    Descriptions = antd.Descriptions, Space = antd.Space, message = antd.message,
    Spin = antd.Spin, Dropdown = antd.Dropdown, Card = antd.Card, Radio = antd.Radio, Rate = antd.Rate;
  var pluginId = "qwenpaw-artifact-library";
  var PLUGIN_VERSION = "0.5.4";
  var TYPES = { image: "图片", document: "文档", web: "网页", code: "代码", video: "视频", audio: "音频", archive: "压缩包", data: "数据", other: "其他" };
  var STATUS = { draft: "草稿", delivered: "已交付", final: "最终版", archived: "已归档", trashed: "已移入回收站" };
  var TYPE_COLOR = { image:"magenta", document:"blue", web:"cyan", code:"purple", video:"volcano", audio:"gold", archive:"orange", data:"geekblue", other:"default" };
  var STATUS_COLOR = { draft:"default", delivered:"blue", final:"green", archived:"gold", trashed:"red" };
  var TEXT_TYPES = { document:1, code:1, web:1, data:1 };

  function request(path, opts) { opts = opts || {}; opts.headers = Object.assign({"Cache-Control":"no-cache","Pragma":"no-cache"}, opts.headers || {}); return Q.host.fetch("/artifact-library" + path, opts).then(function (r) { return r.json().then(function (body) { if (!r.ok) throw new Error(body.detail || "请求失败"); return body; }); }); }
  function runtimeVersion() { return Q.host.fetch("/artifact-library/version?_=" + Date.now(), {headers:{"Cache-Control":"no-store, no-cache, must-revalidate","Pragma":"no-cache"}, cache:"no-store"}).then(function(r){return r.json();}); }
  function post(path, body) { return request(path, { method:"POST", headers:{"Content-Type":"application/json"}, body: body ? JSON.stringify(body) : undefined }); }
  function patch(path, body) { return request(path, { method:"PATCH", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) }); }
  function fmtTime(v) { return v ? new Date(v * 1000).toLocaleString("zh-CN", { hour12:false }) : "—"; }
  function fmtSize(v) { if (v === undefined || v === null) return "—"; var u=["B","KB","MB","GB"], i=0; while(v>=1024 && i<3){v/=1024;i++;} return (i ? v.toFixed(v>=10?1:2) : v) + " " + u[i]; }
  function basename(path) { return (path || "").split(/[\\/]/).pop(); }
  function shortName(v) { v = v || ""; return v.length > 34 ? v.slice(0, 16) + "…" + v.slice(-14) : v; }
  function fileIcon(type) { return { image:"▧", document:"▤", web:"◫", code:"</>", video:"▷", audio:"♪", archive:"▥", data:"▦", other:"□" }[type] || "□"; }
  function StatusTag(p) { return h(Tag, { color: STATUS_COLOR[p.status] }, STATUS[p.status] || p.status); }
  function TypeTag(p) { return h(Tag, { color: TYPE_COLOR[p.type] }, fileIcon(p.type) + " " + (TYPES[p.type] || p.type)); }
  function GenMeta(item) { return (item && item.generation_meta && typeof item.generation_meta === "object") ? item.generation_meta : {}; }

  function StatsModal(p) {
    var sd = React.useState(null), statsData = sd[0], setStatsData = sd[1];
    React.useEffect(function() { if (!p.open) return; setStatsData(null); request("/stats").then(setStatsData).catch(function(e) { message.error(e.message); }); }, [p.open]);
    return h(Modal, { title: "产物统计", open: p.open, onCancel: p.close, footer: null, width: 520 },
      statsData ? h("div", { style: { padding: "8px 0" } },
        h("div", { style: { fontSize: 20, fontWeight: 700, textAlign: "center", marginBottom: 18 } }, statsData.active + " 项活动产物 / 共 " + statsData.total + " 条记录"),
        h("div", { style: { color:"#8c8c8c", textAlign:"center", marginBottom:16 } }, "回收站：" + statsData.trashed + " 项"),
        h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 } }, statBlock("按项目", statsData.by_project, null), statBlock("按类型", statsData.by_type, TYPES)), statBlock("按状态", statsData.by_status, STATUS)
      ) : h("div", { style: { padding: 40, textAlign: "center" } }, h(Spin, null))
    );
  }
  function statBlock(title, obj, labels) { return h("div", { style:{marginTop:8} }, h("div", { style:{fontWeight:600,marginBottom:8} }, title), Object.keys(obj || {}).length ? Object.keys(obj || {}).map(function(k){ return h("div", { key:k, style:{display:"flex",justifyContent:"space-between",padding:"3px 0",fontSize:13} }, h("span", null, (labels && labels[k]) || k), h("b", null, obj[k])); }) : h("span", {style:{color:"#bfbfbf"}}, "暂无")); }

  function PreviewBlock(p) {
    var item = p.item, st = React.useState(null), preview = st[0], setPreview = st[1], loading = React.useState(false), busy = loading[0], setBusy = loading[1];
    React.useEffect(function(){
      setPreview(null); if (!item || item.status === "trashed") return;
      if (item.artifact_type === "image") { setPreview({kind:"image", url:"/api/artifact-library/artifacts/" + item.id + "/image?_=" + Date.now()}); return; }
      if (item.artifact_type === "audio" || item.artifact_type === "video") { setBusy(true); request("/artifacts/" + item.id + "/media").then(function(d){setPreview({kind:"media", data:d});}).catch(function(e){setPreview({kind:"error", text:e.message});}).finally(function(){setBusy(false);}); return; }
      if (TEXT_TYPES[item.artifact_type]) { setBusy(true); request("/artifacts/" + item.id + "/text").then(function(d){setPreview({kind:"text", data:d});}).catch(function(e){setPreview({kind:"error", text:e.message});}).finally(function(){setBusy(false);}); }
    }, [item && item.id]);
    if (!item) return null; if (busy) return h("div", {style:{padding:24,textAlign:"center"}}, h(Spin, null));
    if (!preview) return h("div", {style:{padding:14,color:"#8c8c8c",background:"#fafafa",borderRadius:8}}, "该类型暂无预览，只显示元数据。");
    if (preview.kind === "image") return h("div", {style:{padding:10,background:"#fafafa",borderRadius:8,textAlign:"center"}}, h("img", {src:preview.url, style:{maxWidth:"100%",maxHeight:420,borderRadius:6}}));
    if (preview.kind === "text") return h("pre", {style:{maxHeight:320,overflow:"auto",whiteSpace:"pre-wrap",fontSize:12,background:"#0f172a",color:"#e5e7eb",padding:12,borderRadius:8}}, preview.data.content + (preview.data.truncated ? "\n\n……已截断" : ""));
    if (preview.kind === "media") return h(Descriptions, {column:1,size:"small",bordered:true}, h(Descriptions.Item,{label:"格式"}, preview.data.extension), h(Descriptions.Item,{label:"时长"}, preview.data.duration_seconds == null ? "未知" : preview.data.duration_seconds + " 秒"), h(Descriptions.Item,{label:"尺寸"}, preview.data.width ? preview.data.width + "×" + preview.data.height : "未知"), h(Descriptions.Item,{label:"码率"}, preview.data.bit_rate || "未知"));
    return h("div", {style:{padding:14,color:"#cf1322",background:"#fff1f0",borderRadius:8}}, preview.text);
  }

  function ArtifactLibrary() {
    var dataState = React.useState([]), items = dataState[0], setItems = dataState[1];
    var genState = React.useState([]), genItems = genState[0], setGenItems = genState[1];
    var facetsState = React.useState({models:{},loras:{},ratings:{},total:0}), facets = facetsState[0], setFacets = facetsState[1];
    var busyState = React.useState(true), busy = busyState[0], setBusy = busyState[1];
    var queryState = React.useState(""), query = queryState[0], setQuery = queryState[1];
    var typeState = React.useState(""), type = typeState[0], setType = typeState[1];
    var statusState = React.useState(""), status = statusState[0], setStatus = statusState[1];
    var projectState = React.useState(""), project = projectState[0], setProject = projectState[1];
    var selectedState = React.useState(null), selected = selectedState[0], setSelected = selectedState[1];
    var trashState = React.useState(false), includeTrash = trashState[0], setIncludeTrash = trashState[1];
    var statsOpenState = React.useState(false), statsOpen = statsOpenState[0], setStatsOpen = statsOpenState[1];
    var selKeysState = React.useState([]), selectedRowKeys = selKeysState[0], setSelectedRowKeys = selKeysState[1];
    var notesEditState = React.useState(false), notesEditing = notesEditState[0], setNotesEditing = notesEditState[1];
    var notesValState = React.useState(""), notesVal = notesValState[0], setNotesVal = notesValState[1];
    var viewState = React.useState("list"), view = viewState[0], setView = viewState[1];
    var genModelState = React.useState(""), genModel = genModelState[0], setGenModel = genModelState[1];
    var genLoraState = React.useState(""), genLora = genLoraState[0], setGenLora = genLoraState[1];
    var genCategoryState = React.useState(""), genCategory = genCategoryState[0], setGenCategory = genCategoryState[1];
    var genRatingState = React.useState(0), genRating = genRatingState[0], setGenRating = genRatingState[1];
    var genSortState = React.useState("newest"), genSort = genSortState[0], setGenSort = genSortState[1];
    var runtimeState = React.useState("checking"), runtimeStatus = runtimeState[0], setRuntimeStatus = runtimeState[1];

    React.useEffect(function(){
      var alive = true, key = pluginId + "-version-reload-" + PLUGIN_VERSION;
      runtimeVersion().then(function(d){
        if (!alive) return;
        if (d && d.version === PLUGIN_VERSION) { setRuntimeStatus("ok"); return; }
        var seen = sessionStorage.getItem(key);
        if (!seen) { sessionStorage.setItem(key, "1"); window.location.reload(); return; }
        setRuntimeStatus("mismatch:" + ((d && d.version) || "unknown"));
      }).catch(function(){ if (alive) setRuntimeStatus("unavailable"); });
      return function(){alive=false;};
    }, []);

    var load = React.useCallback(function () { setBusy(true); var p = new URLSearchParams(); if(query)p.set("query",query); if(type)p.set("artifact_type",type); if(status)p.set("status",status); if(project)p.set("project",project); if(includeTrash)p.set("include_trashed","true"); request("/artifacts?" + p.toString()).then(function (d) { setItems(d.items || []); }).catch(function(e){ message.error(e.message); }).finally(function(){setBusy(false);}); }, [query,type,status,project,includeTrash]);
    var loadGenerated = React.useCallback(function(){ setBusy(true); var p = new URLSearchParams(); if(query)p.set("query",query); if(genModel)p.set("model_name",genModel); if(genLora)p.set("lora_name",genLora); if(genCategory)p.set("category",genCategory); if(genRating)p.set("min_rating",genRating); if(genSort)p.set("sort",genSort); request("/generated-images?" + p.toString()).then(function(d){ setGenItems(d.items || []); setFacets(d.facets || {}); }).catch(function(e){ message.error(e.message); }).finally(function(){setBusy(false);}); }, [query, genModel, genLora, genCategory, genRating, genSort]);
    React.useEffect(function(){ var id=setTimeout(view === "generated" ? loadGenerated : load,180); return function(){clearTimeout(id);}; },[load, loadGenerated, view]);
    var projects = Array.from(new Set(items.map(function(x){return x.project;}).filter(Boolean))).sort();
    var softRefresh = function(){ setSelected(null); view === "generated" ? loadGenerated() : load(); };
    var openDetail = function(x){ setSelected(x); setNotesEditing(false); setNotesVal(x.notes || ""); };
    var trash = function(item) { Modal.confirm({ title:"移入回收站？", content:"将把「"+item.title+"」的原文件移入 Windows 回收站。它不会被永久删除，可从系统回收站恢复。", okText:"移入回收站", okButtonProps:{danger:true}, cancelText:"取消", onOk:function(){return post("/artifacts/"+item.id+"/trash").then(function(){message.success("已移入回收站");softRefresh();});} }); };
    var markFinal = function(item) { return patch("/artifacts/"+item.id,{status:"final"}).then(function(d){message.success(d.demoted_final_ids && d.demoted_final_ids.length ? "已设为最终版，旧最终版已归档" : "已设为最终版");softRefresh();}); };
    var reveal = function(item) { return post("/artifacts/" + item.id + "/reveal").then(function(){message.success("已打开资源管理器定位文件");}).catch(function(e){message.error(e.message);}); };
    var copyArtifact = function(item) { return post("/artifacts/" + item.id + "/copy").then(function(d){message.success(d.message || "已复制产物");}).catch(function(e){message.error(e.message);}); };
    var copyPath = function(item) { return post("/artifacts/" + item.id + "/copy-path").then(function(d){message.success(d.message || "路径已复制");}).catch(function(e){message.error(e.message);}); };
    var copyText = function(text, label) { if (!text) return message.warning("没有可复制内容"); if (navigator.clipboard) navigator.clipboard.writeText(text).then(function(){message.success((label||"内容")+"已复制");}).catch(function(){message.error("复制失败");}); else message.warning("当前环境不支持直接写剪贴板"); };
    var saveNotes = function(){ if(!selected)return; patch("/artifacts/"+selected.id,{notes:notesVal}).then(function(d){message.success("备注已保存");setNotesEditing(false);setSelected(d);softRefresh();}).catch(function(e){message.error(e.message);}); };
    var manualRegister = function(){ post("/picker").then(function(meta){ var title = prompt("显示名称", meta.suggested_title || meta.filename); if (!title) return; var summary = prompt("简述", "手动登记的产物：" + meta.filename); if (!summary) return; var proj = prompt("项目", project || "未分类"); if (!proj) return; var deliverable = prompt("交付项（可空）", title) || title; var tagsText = prompt("标签（用逗号分隔，可空）", ""); var notesText = prompt("备注（可空）", "") || ""; return post("/artifacts", {path:meta.path,title:title,summary:summary,project:proj,deliverable:deliverable,artifact_type:meta.artifact_type,tags:(tagsText||"").split(/[,，]/).map(function(x){return x.trim();}).filter(Boolean),status:"delivered",notes:notesText}).then(function(){message.success("已登记文件");load();}); }).catch(function(e){ if(e.message !== "未选择文件") message.error(e.message); }); };
    var importGenerated = function(){ var proj = prompt("导入到哪个项目？", "生图图库"); if (!proj) return; post("/generated-images/import", {project:proj, limit:0}).then(function(d){message.success("导入 " + d.imported + " 张，修复 " + (d.repaired||0) + " 张，跳过 " + d.skipped + " 张"); loadGenerated();}).catch(function(e){message.error(e.message);}); };
    var downloadExport = function(fmt){ Q.host.fetch("/artifact-library/export?format="+fmt).then(function(r){if(!r.ok)throw new Error("导出失败");return r.blob();}).then(function(blob){var url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="artifacts."+(fmt==="markdown"?"md":fmt);document.body.appendChild(a);a.click();setTimeout(function(){document.body.removeChild(a);URL.revokeObjectURL(url);},200);}).catch(function(e){message.error(e.message);}); };
    var doBatchUpdate = function(field){ var val=prompt("新的"+(field==="project"?"项目名":"类型")); if(!val)return; post("/batch",{items:selectedRowKeys.map(function(id){var o={id:id};o[field]=val;return o;})}).then(function(d){message.success("已更新 "+d.updated+" 项");setSelectedRowKeys([]);softRefresh();}).catch(function(e){message.error(e.message);}); };
    var doBatchDelete = function(){ Modal.confirm({title:"批量移入回收站",content:"确定将选中的 "+selectedRowKeys.length+" 项移入 Windows 回收站？不会永久删除。",okText:"移入回收站",okButtonProps:{danger:true},cancelText:"取消",onOk:function(){return post("/batch/delete",{ids:selectedRowKeys}).then(function(d){message.success("已移入回收站 "+d.deleted+" 项");setSelectedRowKeys([]);softRefresh();});}}); };
    var orphanCount = items.filter(function(x){return x.file_exists===false && x.status!=="trashed";}).length;
    var cleanupOrphans = function(){ Modal.confirm({title:"清理无源文件记录",content:"将删除 "+orphanCount+" 条源文件已不存在的记录（元数据标记为回收站，文件已不存在无需回收）。确定继续？",okText:"清理",okButtonProps:{danger:true},cancelText:"保留",onOk:function(){return post("/batch/delete",{ids:items.filter(function(x){return x.file_exists===false && x.status!=="trashed";}).map(function(x){return x.id;}), force:true}).then(function(d){message.success("已清理 "+d.deleted+" 条无源记录");softRefresh();});}}); };
    var rowSelection = { selectedRowKeys: selectedRowKeys, onChange: function(keys){ setSelectedRowKeys(keys); } };
    var actionButtons = function(x) { return h(Space,{size:2,wrap:true}, x.file_exists===false?h("span",{style:{color:"#faad14",fontSize:16,marginRight:4}},"⚠"):null, h(Button,{type:"link",size:"small",onClick:function(){openDetail(x);}},"详情"), x.status!=="trashed"?h(Button,{type:"link",size:"small",onClick:function(){reveal(x);}},"打开位置"):null, x.status!=="trashed"?h(Button,{type:"link",size:"small",onClick:function(){copyArtifact(x);}},"复制产物"):null, h(Button,{type:"link",size:"small",onClick:function(){copyPath(x);}},"复制路径"), x.status!=="trashed"&&x.status!=="final"?h(Button,{type:"link",size:"small",onClick:function(){markFinal(x).catch(function(e){message.error(e.message);});}},"设终版"):null, x.status!=="trashed"?h(Button,{type:"link",danger:true,size:"small",onClick:function(){trash(x);}},"删除"):null); };

    var columns = [
      { title:"产物", dataIndex:"title", key:"title", width:300, render:function(_,x){return h("div",{style:{display:"flex",gap:10,alignItems:"center"}},h("span",{style:{fontFamily:"ui-monospace,Consolas",fontSize:16,color:"#1677ff",width:22,textAlign:"center"}},fileIcon(x.artifact_type)),h("div",null,h("div",{style:{fontWeight:600,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:240}},x.title),h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:240}},x.summary)));}},
      { title:"归属", key:"scope", width:210, render:function(_,x){return h("div",null,h("div",{style:{fontSize:13}},x.project),h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:3}},x.deliverable));}},
      { title:"类型", dataIndex:"artifact_type", width:105, render:function(v){return h(TypeTag,{type:v});}}, { title:"状态", dataIndex:"status", width:115, render:function(v){return h(StatusTag,{status:v});}},
      { title:"登记时间", dataIndex:"created_at", width:170, render:function(v){return h("span",{style:{fontSize:12,color:"#595959"}},fmtTime(v));}}, { title:"操作", key:"actions", width:310, render:function(_,x){return actionButtons(x);}}
    ];
    var renderCards = function(){ return h("div", {style:{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(250px,1fr))",gap:14}}, items.map(function(x){ return h(Card, {key:x.id, hoverable:true, onDoubleClick:function(){openDetail(x);}, cover:x.artifact_type==="image"?h("img",{src:"/api/artifact-library/artifacts/"+x.id+"/thumbnail?_="+Date.now(), style:{height:150,objectFit:"cover"}, onError:function(e){e.currentTarget.style.display='none';}}):null}, h("div",{style:{display:"flex",gap:8,alignItems:"center",marginBottom:8}}, h("b",{style:{fontSize:18,color:"#1677ff"}},fileIcon(x.artifact_type)), h("b",{style:{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}},x.title)), h("div",{style:{fontSize:12,color:"#8c8c8c",height:36,overflow:"hidden"}},x.summary), h("div",{style:{marginTop:10}}, h(TypeTag,{type:x.artifact_type}), h(StatusTag,{status:x.status})), h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:8}},x.project), h("div",{style:{marginTop:10}}, actionButtons(x))); })); };
    var renderProjects = function(){ var grouped={}; items.forEach(function(x){(grouped[x.project||"未分类"]||(grouped[x.project||"未分类"]=[])).push(x);}); return h("div", null, Object.keys(grouped).sort().map(function(k){return h("div",{key:k,style:{marginBottom:18}}, h("h3",{style:{margin:"8px 0"}},k+" · "+grouped[k].length+" 项"), h(Table,{dataSource:grouped[k],rowKey:"id",columns:columns,pagination:false,size:"small",onRow:function(x){return {onDoubleClick:function(){openDetail(x);},style:{cursor:"pointer"}};}}));})); };
    var renderGenerated = function(){ return h("div", null,
      h("div",{style:{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center",marginBottom:14,padding:"10px 12px",background:"#fff7e6",border:"1px solid #ffd591",borderRadius:8}},
        h("b",null,"生图资产 · "+(facets.total||genItems.length)+" 张"),
        h(Select,{allowClear:true,value:genModel||undefined,onChange:function(v){setGenModel(v||"");},placeholder:"按模型",options:Object.keys(facets.models||{}).map(function(k){return {label:shortName(k)+" · "+facets.models[k],value:k};}),style:{width:220}}),
        h(Select,{allowClear:true,value:genLora||undefined,onChange:function(v){setGenLora(v||"");},placeholder:"按 LoRA",options:Object.keys(facets.loras||{}).map(function(k){return {label:shortName(k)+" · "+facets.loras[k],value:k};}),style:{width:220}}),
        h(Select,{allowClear:true,value:genCategory||undefined,onChange:function(v){setGenCategory(v||"");},placeholder:"生图分类",options:Object.keys(facets.categories||{}).sort().map(function(k){return {label:k+" · "+facets.categories[k],value:k};}),style:{width:170}}),
        h(Select,{value:genRating,onChange:setGenRating,options:[0,1,2,3,4,5].map(function(n){return {label:n?"≥"+n+" 星":"全部星级",value:n};}),style:{width:120}}),
        h(Select,{value:genSort,onChange:setGenSort,options:[{label:"最新",value:"newest"},{label:"星级优先",value:"rating"},{label:"按模型",value:"model"}],style:{width:120}}),
        h("span",{style:{flex:1}}), h(Button,{type:"primary",onClick:importGenerated},"从生图助手导入"), h(Button,{onClick:loadGenerated},"刷新")
      ),
      genItems.length ? h("div",{style:{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(220px,1fr))",gap:14}}, genItems.map(function(x){ var m=GenMeta(x); return h(Card,{key:x.id,hoverable:true,onDoubleClick:function(){openDetail(x);},cover:h("img",{src:"/api/artifact-library/artifacts/"+x.id+"/thumbnail?_="+Date.now(),style:{height:190,objectFit:"cover"},onError:function(e){e.currentTarget.style.display='none';}})},
        h("div",{style:{fontWeight:700,overflow:"hidden",whiteSpace:"nowrap",textOverflow:"ellipsis"}},x.title),
        h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:5}},(m.width||"?")+"×"+(m.height||"?")+" · Seed "+(m.seed==null?"—":m.seed)),
        h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:4}},"模型："+shortName(m.model_name||"未记录")),
        h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:4}},"LoRA："+shortName(m.lora_name||"未记录")),
        h("div",{style:{fontSize:12,color:"#1677ff",marginTop:4}},"分类："+(m.category||"未分类")),
        h("div",{style:{marginTop:8,display:"flex",alignItems:"center",justifyContent:"space-between"}}, h(Rate,{disabled:true,value:Number(m.rating||0),style:{fontSize:14}}), h("div",{style:{display:"flex",gap:4}},h(Button,{size:"small",onClick:function(e){e.stopPropagation();copyText(m.prompt,"Prompt");}},"复制Prompt"),m.negative_prompt?h(Button,{size:"small",onClick:function(e){e.stopPropagation();copyText(m.negative_prompt,"Negative Prompt");}},"复制负向"):null)),
        h("div",{style:{marginTop:8}}, actionButtons(x))
      ); })) : h(Empty,{description:"还没有导入生图资产。点击“从生图助手导入”会读取本机 qwenpaw-image-gen 图库。",image:Empty.PRESENTED_IMAGE_SIMPLE})
    ); };

    var body = busy?h("div",{style:{padding:70,textAlign:"center"}},h(Spin,null)):(view==="generated"?renderGenerated():items.length?(view==="cards"?renderCards():view==="projects"?renderProjects():h(Table,{rowSelection:rowSelection,dataSource:items,rowKey:"id",columns:columns,pagination:{pageSize:12,showSizeChanger:false},size:"middle",onRow:function(x){return {onDoubleClick:function(){openDetail(x);},style:{cursor:"pointer"}};} })):h(Empty,{description:"还没有登记的正式产物。Agent 交付文件后调用 register_artifact 即可收录。",image:Empty.PRESENTED_IMAGE_SIMPLE}));

    return h("div",{style:{height:"100%",minHeight:"100%",background:"var(--ant-color-bg-layout,#f5f5f5)",padding:"28px 32px",boxSizing:"border-box"}}, h("div",{style:{maxWidth:1500,margin:"0 auto"}},
      h("header",{style:{display:"flex",alignItems:"end",justifyContent:"space-between",marginBottom:24}},h("div",null,h("div",{style:{fontSize:12,letterSpacing:".14em",fontWeight:700,color:"#1677ff",marginBottom:7}},"ARTIFACT LIBRARY"),h("h1",{style:{margin:0,fontSize:28,lineHeight:1.2,letterSpacing:"-.03em"}},"产物库"),h("div",{style:{color:"#8c8c8c",fontSize:13,marginTop:8}},"正式成果 + 生图资产管理 · "+(view==="generated"?genItems.length:items.length)+" 项"+(orphanCount>0?" · ⚠ "+orphanCount+" 条无源文件":""))),h("div",{style:{fontSize:12,color:"#8c8c8c",maxWidth:500,textAlign:"right",lineHeight:1.6}},"v" + PLUGIN_VERSION + "：已使用版本化前端入口，升级后可避开旧版界面缓存；生图资产、备注、星级与交付归档继续可用。")),
      runtimeStatus.indexOf("mismatch:")===0?h("div",{style:{marginBottom:14,padding:"10px 12px",borderRadius:8,background:"#fff2f0",border:"1px solid #ffccc7",color:"#cf1322",fontSize:13,lineHeight:1.6}},"版本不同步：当前界面是 v"+PLUGIN_VERSION+"，但运行中的产物库后端是 v"+runtimeStatus.slice(9)+"。已自动刷新一次仍未同步，请完全退出并重新打开 QwenPaw 后再使用，避免旧界面与新数据混用。 ",h(Button,{size:"small",danger:true,onClick:function(){sessionStorage.removeItem(pluginId+"-version-reload-"+PLUGIN_VERSION);window.location.reload();}},"再次检查")):runtimeStatus==="unavailable"?h("div",{style:{marginBottom:14,padding:"8px 12px",borderRadius:8,background:"#fffbe6",border:"1px solid #ffe58f",color:"#ad6800",fontSize:13}},"暂时无法确认运行版本；当前功能仍可使用。若刚升级插件，请重启 QwenPaw 后再确认版本。 ",h(Button,{size:"small",onClick:function(){window.location.reload();}},"重新检查")):null,
      h("section",{style:{background:"var(--ant-color-bg-container,#fff)",border:"1px solid var(--ant-color-border-secondary,#f0f0f0)",borderRadius:12,padding:16,boxShadow:"0 2px 12px rgba(0,0,0,.025)"}},
        h("div",{style:{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center",marginBottom:16}},
          h(Input,{allowClear:true,value:query,onChange:function(e){setQuery(e.target.value);},placeholder:view==="generated"?"搜索 prompt、模型、LoRA、备注":"搜索名称、项目、交付项、标签或说明",prefix:"⌕",style:{width:310}}),
          view!=="generated"?h(Select,{allowClear:true,value:project||undefined,onChange:function(v){setProject(v||"");},placeholder:"全部项目",options:projects.map(function(x){return {label:x,value:x};}),style:{width:170}}):null,
          view!=="generated"?h(Select,{allowClear:true,value:type||undefined,onChange:function(v){setType(v||"");},placeholder:"全部类型",options:Object.keys(TYPES).map(function(x){return {label:TYPES[x],value:x};}),style:{width:130}}):null,
          view!=="generated"?h(Select,{allowClear:true,value:status||undefined,onChange:function(v){setStatus(v||"");},placeholder:"全部状态",options:Object.keys(STATUS).map(function(x){return {label:STATUS[x],value:x};}),style:{width:130}}):null,
          h("div",{style:{display:"flex",alignItems:"center",gap:8}},h(Radio.Group,{value:view,onChange:function(e){setView(e.target.value);setSelectedRowKeys([]);},optionType:"button",buttonStyle:"solid",options:[{label:"列表",value:"list"},{label:"卡片",value:"cards"},{label:"项目",value:"projects"}]}),h(Button,{type:view==="generated"?"primary":"default",onClick:function(){setView("generated");setSelectedRowKeys([]);},style:{borderColor:view==="generated"?"#ff8c42":"#d9d9d9",background:view==="generated"?"#ff8c42":"#fff"}},"生图库 · "+genItems.length)),
          h("span",{style:{flex:1}}), view!=="generated"?h(Button,{type:"primary",onClick:manualRegister},"登记文件"):null, view!=="generated"?h(Button,{type:includeTrash?"primary":"default",onClick:function(){setIncludeTrash(!includeTrash);}},includeTrash?"显示全部记录":"含回收站记录"):null, h(Button,{onClick:view==="generated"?loadGenerated:load},"刷新"), h(Button,{onClick:function(){setStatsOpen(true);}},"统计"), h(Dropdown,{menu:{items:[{key:"json",label:"导出为 JSON",onClick:function(){downloadExport("json");}},{key:"csv",label:"导出为 CSV",onClick:function(){downloadExport("csv");}},{key:"md",label:"导出为 Markdown",onClick:function(){downloadExport("markdown");}}]}},h(Button,null,"导出 ▾"))
        ),
        selectedRowKeys.length>0?h("div",{style:{display:"flex",gap:8,alignItems:"center",marginBottom:12,padding:"6px 12px",background:"#e6f4ff",borderRadius:6}},h("span",{style:{fontSize:13,color:"#1677ff"}},"已选择 "+selectedRowKeys.length+" 项"),h(Button,{size:"small",onClick:function(){doBatchUpdate("project");}},"修改项目"),h(Button,{size:"small",onClick:function(){doBatchUpdate("artifact_type");}},"修改类型"),h(Button,{size:"small",danger:true,onClick:doBatchDelete},"批量删除"),h(Button,{size:"small",onClick:function(){setSelectedRowKeys([]);}},"取消选择")):(orphanCount>0?h("div",{style:{display:"flex",gap:8,alignItems:"center",marginBottom:12,padding:"6px 12px",background:"#fffbe6",borderRadius:6}},h("span",{style:{fontSize:13,color:"#faad14"}},"⚠ "+orphanCount+" 条记录的源文件已不存在"),h(Button,{size:"small",danger:true,onClick:cleanupOrphans},"清理无源文件")):null),
        body
      ),
      h(StatsModal,{open:statsOpen,close:function(){setStatsOpen(false);}}),
      h(Drawer,{title:selected?selected.title:"产物详情",open:!!selected,onClose:function(){setSelected(null);},width:680,extra:selected?h(Space,{wrap:true},selected.status!=="trashed"?h(Button,{onClick:function(){reveal(selected);}},"打开位置"):null,selected.status!=="trashed"?h(Button,{onClick:function(){copyArtifact(selected);}},"复制产物"):null,h(Button,{onClick:function(){copyPath(selected);}},"复制路径"),selected.status!=="trashed"?h(Button,{danger:true,onClick:function(){trash(selected);}},"移入回收站"):null):null},selected?(function(){ var gm=GenMeta(selected); var paramText = ["model="+(gm.model_name||""), "lora="+(gm.lora_name||""), "steps="+(gm.steps||""), "cfg="+(gm.cfg||""), "seed="+(gm.seed==null?"":gm.seed), "size="+(gm.width||"?")+"x"+(gm.height||"?")].join("\n"); return h("div",null,
        h("div",{style:{display:"flex",alignItems:"center",gap:10,marginBottom:20}},h("span",{style:{fontSize:28,color:"#1677ff"}},fileIcon(selected.artifact_type)),h("div",null,h("div",{style:{fontWeight:700,fontSize:16}},selected.title),h("div",{style:{marginTop:6}},h(TypeTag,{type:selected.artifact_type})," ",h(StatusTag,{status:selected.status}),selected.asset_category==="generated_image"?h(Tag,{color:"orange"},"生图资产"):null))),
        h(PreviewBlock,{item:selected}), h("div",{style:{height:16}}),
        selected.asset_category==="generated_image"?h("div",{style:{marginBottom:16,padding:12,border:"1px solid #ffd591",background:"#fff7e6",borderRadius:8}}, h("div",{style:{fontWeight:700,marginBottom:8}},"生图参数"), h(Space,{wrap:true},h(Button,{size:"small",onClick:function(){copyText(gm.prompt,"Prompt");}},"复制 Prompt"),h(Button,{size:"small",onClick:function(){copyText(gm.negative_prompt,"Negative Prompt");}},"复制负向"),h(Button,{size:"small",onClick:function(){copyText(paramText,"参数摘要");}},"复制参数")), h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:8}},"模型："+(gm.model_name||"—")+"｜LoRA："+(gm.lora_name||"—")+"｜星级："+(gm.rating||0)), gm.prompt?h("div",{style:{fontSize:12,color:"#333",marginTop:8,background:"#f5f5f5",padding:"6px 8px",borderRadius:4,wordBreak:"break-all"}},"正向："+gm.prompt):null, gm.negative_prompt?h("div",{style:{fontSize:12,color:"#8c8c8c",marginTop:6,background:"#f5f5f5",padding:"6px 8px",borderRadius:4,wordBreak:"break-all"}},"负向："+gm.negative_prompt):null):null,
        selected.status==="final"?h("div",{style:{margin:"0 0 20px",padding:"10px 12px",background:"#f6ffed",border:"1px solid #b7eb8f",borderRadius:8,fontSize:13,color:"#389e0d"}},"这是当前交付项的最终版。登记新最终版时，本记录会自动归档。 "):null,
        h(Descriptions,{column:1,size:"small",bordered:true},h(Descriptions.Item,{label:"说明"},selected.summary),h(Descriptions.Item,{label:"项目"},selected.project),h(Descriptions.Item,{label:"交付项"},selected.deliverable),h(Descriptions.Item,{label:"标签"},(selected.tags||[]).length?selected.tags.map(function(t){return h(Tag,{key:t},t);}):"—"),h(Descriptions.Item,{label:"文件"},h("div",null,h("div",{style:{wordBreak:"break-all"}},basename(selected.path)),h("div",{style:{fontSize:12,color:"#8c8c8c",wordBreak:"break-all",marginTop:4}},selected.path))),h(Descriptions.Item,{label:"文件信息"},fmtSize(selected.size_bytes)+" · "+(selected.extension||"无后缀")+" · "+(selected.file_exists?"文件存在":"原文件未找到")),h(Descriptions.Item,{label:"来源"},(selected.agent_id||"未知 Agent")+(selected.session_id?" · "+selected.session_id:"")),h(Descriptions.Item,{label:"备注"},notesEditing?h("div",{style:{display:"flex",gap:8,flexDirection:"column"}},h(Input.TextArea,{value:notesVal,onChange:function(e){setNotesVal(e.target.value);},rows:2,placeholder:"添加备注"}),h("div",{style:{display:"flex",gap:8}},h(Button,{size:"small",type:"primary",onClick:saveNotes},"保存"),h(Button,{size:"small",onClick:function(){setNotesEditing(false);}},"取消"))):h("div",{style:{display:"flex",gap:8,alignItems:"center"}},h("span",{style:{color:selected.notes?"inherit":"#bfbfbf"}},selected.notes||"暂无备注"),selected.status!=="trashed"?h(Button,{type:"link",size:"small",onClick:function(){setNotesVal(selected.notes||"");setNotesEditing(true);}},"编辑"):null)),h(Descriptions.Item,{label:"登记于"},fmtTime(selected.created_at)))
      ); })():null)
    ));
  }
  if (Q.menu && Q.route) {
    Q.route.add(pluginId,{id:"qwenpaw-artifact-library.page",path:"/artifacts",component:ArtifactLibrary});
    Q.menu.add(pluginId,{id:"qwenpaw-artifact-library.menu",label:"产物库",icon:h("span",{style:{fontFamily:"ui-monospace,Consolas",fontWeight:700}},"▣"),route:"qwenpaw-artifact-library.page",location:"primary.agentScoped",order:65});
  } else if (Q.registerRoutes) Q.registerRoutes(pluginId,[{path:"/artifacts",component:ArtifactLibrary,label:"产物库",icon:"▣"}]);
})();
