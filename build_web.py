from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
# Explicit source snippets only: never rewrite user conversations, code, or protocol keys.
rules={
'agent-conversation.html':{
'aria-label="Back to bottom"':'aria-label="回到底部（Back to bottom）"',
"thinkingEl.textContent = 'Thinking ...';":"thinkingEl.textContent = '正在思考…（Thinking）';",
"payload.title || 'Plan'":"payload.title || '计划（Plan）'",
"payload.completed ? 'Context compressed' : 'Compressing context'":"payload.completed ? '上下文已压缩（Context compressed）' : '正在压缩上下文（Compressing context）'",
"payload.title || 'Thinking'":"payload.title || '正在思考（Thinking）'",
"title: 'Thought'":"title: '思考过程（Thought）'",
},
'cadviewer.html':{
'<title>VibeFlow Geometry Preview</title>':'<title>VibeFlow 几何预览（Geometry Preview）</title>',
'VibeFlow scene has no renderable geometry payload.':'VibeFlow 场景没有可渲染的几何数据。（VibeFlow scene has no renderable geometry payload.）',
},
'terminal.html':{
'Initializing terminal...':'正在初始化终端…（Initializing terminal...）',
'Connecting terminal bridge...':'正在连接终端桥接…（Connecting terminal bridge...）',
'Qt WebChannel is unavailable. Terminal bridge was not injected into the page.':'Qt WebChannel 不可用，页面未注入终端桥接。（Qt WebChannel is unavailable. Terminal bridge was not injected into the page.）',
'Qt WebChannel connected, but terminalBridge was not registered.':'Qt WebChannel 已连接，但 terminalBridge 未注册。（Qt WebChannel connected, but terminalBridge was not registered.）',
'Terminal JavaScript error:':'终端 JavaScript 错误（Terminal JavaScript error）：',
'Terminal startup error:':'终端启动错误（Terminal startup error）：',
'Terminal resources failed to load:':'终端资源加载失败（Terminal resources failed to load）：',
},
}
cad='''Collpase nodes with a single leaf|折叠只有一个叶节点的节点
Collpase tree|折叠树
Copy shape IDs to clipboard|复制形状 ID 到剪贴板
Edit material of selected object|编辑选中对象材质
Expand root node only|仅展开根节点
Expand tree|展开树
Explode tool|爆炸视图工具
Measure distance between shapes|测量形状间距
Open/close info box|打开／关闭信息框
Pause animation|暂停动画
Pin viewer as png|将视图固定为 PNG
Play animation|播放动画
Reset to default clip planes|恢复默认裁剪平面
Reset to default values|恢复默认值
Reset to default zebra settings|恢复默认斑马纹设置
Reset to original values|恢复原始值
Reset view|重置视图
Resize object|调整对象尺寸
Scale along the Z-axis|沿 Z 轴缩放
Select stripe color scheme|选择条纹配色
Select stripe mapping|选择条纹映射
Set blue clipping plane to view direction|蓝色裁剪平面对齐视线
Set green clipping plane to view direction|绿色裁剪平面对齐视线
Set red clipping plane to view direction|红色裁剪平面对齐视线
Show axes|显示坐标轴
Show axes at origin (0,0,0)|在原点 (0,0,0) 显示坐标轴
Show black edges|显示黑色边线
Show clipping planes|显示裁剪平面
Show grid|显示网格
Show shape properties|显示形状属性
Show transparent faces|显示透明表面
Stop and reset animation|停止并重置动画
Switch to back view|切换到后视图
Switch to bottom view|切换到底视图
Switch to front view|切换到前视图
Switch to iso view|切换到等轴测视图
Switch to left view|切换到左视图
Switch to right view|切换到右视图
Switch to top view|切换到顶视图
Use intersection clipping|使用交集裁剪
Use object color caps instead of RGB|裁剪封口使用对象颜色而非 RGB
Use perspective camera|使用透视相机'''
s=(R/'originals/three-cad-viewer.js').read_text(encoding='utf-8');entries=[]
for line in cad.splitlines():
 en,zh=line.split('|');target=zh+'（'+en+'）';count=0
 for quote in ['"','\\"']:
  old=quote+en+quote;new=quote+target+quote
  count+=s.count(old);s=s.replace(old,new)
 if not count:raise RuntimeError('No CAD match '+en)
 entries.append({'source':en,'translation':target,'occurrences':count})
(R/'work/three-cad-viewer.js').write_text(s, encoding='utf-8', newline='\n')
manifest={'three-cad-viewer.js':entries}
for fn,rs in rules.items():
 raw=(R/'originals'/fn).read_bytes();s=raw.decode();entries=[]
 for old,new in rs.items():
  count=s.count(old);assert count,(fn,old);s=s.replace(old,new)
  entries.append({'source':old,'translation':new,'occurrences':count})
 # In the agent pane, recognize translated native tool labels without touching payloads.
 if fn=='agent-conversation.html':
  old="var raw = String(title || 'Tool');"
  new="var raw = String(title || '工具');\n      var nativeLabels = {'读取文件':'Read File','列出文件':'List Files','搜索文本':'Search Text','网页搜索':'Web Search','读取网页':'Web Fetch','思考中':'Thinking','正在准备工具':'Preparing Tool'};\n      var originalLabel = nativeLabels[raw] || raw;"
  assert old in s;s=s.replace(old,new).replace("var key = raw.toLowerCase().replace", "var key = originalLabel.toLowerCase().replace")
 (R/'work'/fn).write_bytes(s.encode());manifest[fn]=entries
(R/'work/web-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
print('web translated occurrences',sum(e['occurrences'] for es in manifest.values() for e in es))
