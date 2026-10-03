from pathlib import Path
import re,json,xml.etree.ElementTree as E
R=Path(__file__).resolve().parent;b=(R/'originals/vtkRemotingApplication-pv5.11.dll').read_bytes();groups=[]
for m in re.finditer(b'<ServerManagerConfiguration',b):
 start=m.start();cur=start;chunks=[];parts=[]
 for it in range(300):
  end=b.find(b'\0',cur);part=b[cur:end];chunks.append({'offset':cur,'length':len(part)});parts.append(part)
  if b'</ServerManagerConfiguration>' in part:break
  cur=end
  while b[cur]==0:cur+=1
  if not b[cur:cur+50].isascii():break
 try:root=E.fromstring(b''.join(parts))
 except Exception:continue
 groups.append({'chunks':chunks,'xml':b''.join(parts).decode()})
(R/'work/vtk-xml-groups.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
labels=[];proxies=[]
for g in groups:
 root=E.fromstring(g['xml'])
 for n in root.iter():
  if 'label' in n.attrib:labels.append(n.attrib['label'])
  if n.tag.endswith('Proxy') and n.get('label'):proxies.append((n.get('name'),n.get('label')))
(R/'work/vtk-labels.txt').write_text('\n'.join(sorted(set(labels))), encoding='utf-8', newline='\n')
(R/'work/vtk-proxy-labels.json').write_text(json.dumps(proxies,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
print('groups',len(groups),'labels',len(labels),'unique',len(set(labels)),'proxies',len(proxies))
