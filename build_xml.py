from pathlib import Path
import json,re,zlib,struct,xml.etree.ElementTree as E,hashlib
R=Path(__file__).resolve().parent
mapping={}
for fn in ['translations.tsv','vtk-label-translations.tsv']:
 mapping.update(dict(l.split('\t') for l in (R/fn).read_text(encoding='utf-8').splitlines() if l))
# Exact compositional phrases whose meanings are stable display labels.
for pos,zh in [('Bottom','底部'),('Top','顶部'),('Left','左侧'),('Right','右侧'),('X','X'),('Y','Y'),('Z','Z'),('Polar','极坐标'),('Histogram','直方图'),('ActivePlot','当前图表'),('ScatterPlot','散点图')]:
 for suf,zhs in [('Axis','轴'),('Axis Label Properties','轴标签属性'),('Axis Labels','轴标签'),('Axis Range','轴范围'),('Axis Title Properties','轴标题属性'),('Axis Label Font Properties','轴标签字体属性'),('Axis Title Font Properties','轴标题字体属性'),('Axis Parameters','轴参数'),('Title Font Properties','标题字体属性')]:
  mapping[pos+' '+suf]=zh+zhs
categories={'Annotation':'标注','Data Objects':'数据对象','Geometric Shapes':'几何形状','Measurement Tools':'测量工具','Common':'常用','CosmoTools':'宇宙学工具','Data Analysis':'数据分析','AMR':'自适应网格细化（AMR）','CTH':'CTH 材料分析','Chemistry':'化学','Hyper Tree Grid':'超树网格','Material Analysis':'材料分析','Point Interpolation':'点插值','Quadrature Points':'求积点','Statistics':'统计','Temporal':'时间处理','Alphabetical':'按字母排序','Favorites':'收藏夹'}
def stripspace(root):
 for n in root.iter():
  if n.text and not n.text.strip():n.text=None
  if n.tail and not n.tail.strip():n.tail=None

def canon(root,remove):
 def rec(n):return (n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k not in remove)),(n.text or '').strip(),tuple(rec(c) for c in n))
 return rec(root)
catreport=[]
for fn in ['ParaViewSources.xml','ParaViewFilters.xml']:
 original=(R/'originals'/fn).read_bytes();root=E.fromstring(original)
 for c in root.iter('Category'):
  label=c.get('menu_label','');bare=label.replace('&','')
  if bare in categories:
   c.set('menu_label',categories[bare]);catreport.append({'resource':fn,'source':label,'translation':categories[bare]})
 stripspace(root);new=E.tostring(root,encoding='utf-8')
 assert canon(E.fromstring(original),{'menu_label'})==canon(E.fromstring(new),{'menu_label'})
 (R/'work'/fn).write_bytes(new)
# Qt's qCompress payload has a big-endian uncompressed size. Keep the resource
# allocation and name tables unchanged; trailing zero padding is ignored by zlib.
b=bytearray((R/'work/VibeFlowStudio.exe').read_bytes());original=(R/'originals/VibeFlowStudio.exe').read_bytes()
for fn,off in [('ParaViewSources.xml',0x303638),('ParaViewFilters.xml',0x30392b)]:
 decompressor=zlib.decompressobj();previous=decompressor.decompress(original[off:]);length=len(original)-off-len(decompressor.unused_data)
 assert E.fromstring(previous).tag==fn[:-4]
 new=(R/'work'/fn).read_bytes();packed=zlib.compress(new,9)
 assert len(packed)<=length,(fn,len(packed),length)
 b[off-4:off]=struct.pack('>I',len(new));b[off:off+length]=packed+b'\0'*(length-len(packed))
 assert zlib.decompress(b[off:off+length])==new
catpath=R/'work/VibeFlowStudio.exe';catpath.write_bytes(b)
# Native ServerManager XML is stored as adjacent C string chunks. Keep all
# chunk addresses/lengths; split serialized XML only after complete tags.
original=(R/'originals/vtkRemotingApplication-pv5.11.dll').read_bytes();out=bytearray(original);audit=[];groups=json.loads((R/'work/vtk-xml-groups.json').read_text(encoding='utf-8'))
shortdocs={
'Calculator':'根据已有标量或向量数组计算新数组或新点坐标。',
'Contour':'从选定的点标量生成等值线或等值面。',
'Clip':'使用隐式函数裁去部分数据；保留数据维度，输出为非结构网格。',
'Threshold':'提取标量落在指定阈值范围内的单元。',
'Glyph':'在点或单元中心生成符号，使用数据属性控制方向和缩放。',
'Cut':'使用隐式函数切取数据截面。',
'StreamTracer':'沿向量场积分生成流线。',
'WarpVector':'根据向量场移动点，显示数据的变形。',
'WarpScalar':'根据标量值沿指定方向移动点。',
'GroupDataSets':'将多个输入组织为一个复合数据集。',
'ExtractBlock':'从复合数据集中提取选定的数据块。',
'ExtractSelection':'提取当前选区中的点或单元。',
'IntegrateAttributes':'对数据集中的属性进行空间积分。',
'MeshQuality':'计算网格单元质量指标，供检查网格使用。',
'CellDatatoPointData':'将单元中心数据转换到网格点。',
'PointDatatoCellData':'将点数据转换到单元中心。',
'SphereSource':'根据中心位置和半径生成三维球体。',
'CubeSource':'生成指定尺寸和中心位置的长方体。',
'ConeSource':'生成圆锥几何。',
'CylinderSource':'生成圆柱几何。',
'PlaneSource':'生成平面几何。',
'LineSource':'在两个端点之间生成直线。',
'PointSource':'在指定区域生成点。',
'RTAnalyticSource':'生成用于测试和演示的解析小波数据。',
}
def translate(s):
 if s in mapping:return mapping[s]
 # Format/product names stay intact; reader/writer roles become Chinese.
 for suffix,zh in [(' Series Reader','序列读取器'),(' reader','读取器'),(' Reader','读取器'),(' Writer','写入器')]:
  if s.endswith(suffix):return s[:-len(suffix)]+' '+zh
 return None
# Resolve only display-label collisions that would otherwise alias Python names.
collisions=set(json.loads((R/'xml-label-collisions.json').read_text(encoding='utf-8')))
def api_safe_label(target,source):
 return target+'（'+source+'）' if target in collisions else target
changed_groups=0
for g in groups:
 root=E.fromstring(g['xml']);before=E.fromstring(g['xml']);local=[]
 for n in root.iter():
  old=n.get('label')
  if old and (zh:=translate(old)):
   # Scientific source/filter names retain original text to match literature.
   isproxy=n.tag.endswith('Proxy')
   new=zh+'（'+old+'）' if isproxy else zh
   new=api_safe_label(new,old)
   n.set('label',new);local.append({'kind':'label','source':old,'translation':new,'name':n.get('name')})
 for pg in root.findall('ProxyGroup'):
  for n in pg:
   name=n.get('name','')
   if n.tag.endswith('Proxy') and not n.get('label'):
    bare=re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',name)
    zh=translate(bare) or translate(name)
    if zh:n.set('label',zh+'（'+bare+'）');local.append({'kind':'new_proxy_label','source':name,'translation':n.get('label')})
   if name in shortdocs:
    doc=n.find('Documentation')
    if doc is not None:
     for attr in ['short_help','long_help']:
      old=doc.get(attr)
      if old:
       doc.set(attr,shortdocs[name]+'（'+old+'）');local.append({'kind':attr,'source':old,'translation':doc.get(attr)})
 # Add explicit display labels for otherwise auto-prettified property names.
 for n in root.iter():
  if n.tag.endswith('Property') and n.get('name') and not n.get('label'):
   name=n.get('name');bare=re.sub(r'(?<=[a-z0-9])(?=[A-Z])',' ',name)
   zh=translate(bare)
   if zh:n.set('label',api_safe_label(zh,name));local.append({'kind':'new_property_label','source':name,'translation':n.get('label')})
 if not local:continue
 # All functional attributes, proxy IDs, defaults, domains, and child order preserved.
 assert canon(before,{'label','short_help','long_help'})==canon(root,{'label','short_help','long_help'})
 stripspace(root);new=E.tostring(root,encoding='utf-8');remainder=new;parts=[]
 for c in g['chunks']:
  cap=c['length']
  if len(remainder)<=cap:part=remainder;remainder=b''
  else:
   split=remainder.rfind(b'>',0,cap)+1
   assert split>0,('oversized XML tag',g['chunks'][0],cap)
   part=remainder[:split];remainder=remainder[split:]
  parts.append(part+b' '*(cap-len(part)))
 assert not remainder,('XML exceeds original allocation',g['chunks'][0],len(remainder))
 assert canon(E.fromstring(b''.join(parts)),set())==canon(root,set())
 for c,part in zip(g['chunks'],parts):out[c['offset']:c['offset']+c['length']]=part
 audit.extend(local);changed_groups+=1
(R/'work/vtkRemotingApplication-pv5.11.dll').write_bytes(out)
(R/'work/xml-manifest.json').write_text(json.dumps({'categories':catreport,'vtk_labels':audit,'changed_xml_groups':changed_groups},ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
# Refresh checksums after in-place data modifications, preserving all PE offsets.
import pefile
for fn in ['VibeFlowStudio.exe','vtkRemotingApplication-pv5.11.dll']:
 p=R/'work'/fn;data=bytearray(p.read_bytes());pe=pefile.PE(data=data);struct.pack_into('<I',data,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),pe.generate_checksum());p.write_bytes(data)
print('categories',len(catreport),'XML text entries',len(audit),'XML documents',changed_groups)

# Preserve ParaView's generated public Python API names while displaying Chinese.
api_names={}
for entry in audit:
 if entry['kind'] not in ['label','new_proxy_label','new_property_label']:continue
 target=entry['translation'];source=entry['source']
 if target in api_names:assert re.sub('[^a-zA-Z0-9_]','',api_names[target])==re.sub('[^a-zA-Z0-9_]','',source),(target,api_names[target],source)
 api_names[target]=source
text=(R/'originals/paraview-init.py').read_text(encoding='utf-8')
needle='def make_name_valid(name):'
assert text.count(needle)==1
block='_VIBEFLOW_ZH_ORIGINAL_LABELS = '+repr(api_names)+'\n\n'
text=text.replace(needle,block+needle)
text=text.replace('    """Make a string into a valid Python variable name."""','    """Make a string into a valid Python variable name."""\n    name = _VIBEFLOW_ZH_ORIGINAL_LABELS.get(name, name)')
compile(text,'paraview/__init__.py','exec')
(R/'work/paraview-init.py').write_text(text, encoding='utf-8', newline='\n')
(R/'work/api-label-map.json').write_text(json.dumps(api_names,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
print('API compatibility labels',len(api_names),'ambiguous translations disambiguated',len(collisions))

# Domain-choice strings and generated trace scripts are API surfaces, too.
text=(R/'originals/servermanager.py').read_text(encoding='utf-8')
old='retval.append(proxy.GetXMLLabel())'
assert text.count(old)==1
text=text.replace(old,'retval.append(paraview._VIBEFLOW_ZH_ORIGINAL_LABELS.get(proxy.GetXMLLabel(), proxy.GetXMLLabel()))')
(R/'work/servermanager.py').write_text(text, encoding='utf-8', newline='\n')
text=(R/'originals/smtrace.py').read_text(encoding='utf-8')
text=text.replace('x.GetXMLLabel() for x in data','sm.paraview._VIBEFLOW_ZH_ORIGINAL_LABELS.get(x.GetXMLLabel(), x.GetXMLLabel()) for x in data')
text=text.replace('self.Proxy.GetXMLLabel() == "Extract Selection"','sm.paraview._VIBEFLOW_ZH_ORIGINAL_LABELS.get(self.Proxy.GetXMLLabel(), self.Proxy.GetXMLLabel()) == "Extract Selection"')
(R/'work/smtrace.py').write_text(text, encoding='utf-8', newline='\n')

manifest_path=R/'work/patch-manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['VibeFlowStudio.exe']['patched_sha256']=hashlib.sha256((R/'work/VibeFlowStudio.exe').read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
