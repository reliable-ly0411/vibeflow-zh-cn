import pefile,capstone,json
from pathlib import Path
root=Path(__file__).resolve().parent
for fn in ['VibeFlowStudio.exe','pqCore-pv5.11.dll','pqApplicationComponents-pv5.11.dll','pqComponents-pv5.11.dll','pqWidgets-pv5.11.dll']:
 b=(root/'originals'/fn).read_bytes();p=pefile.PE(data=b);base=p.OPTIONAL_HEADER.ImageBase
 targets={i.address for d in p.DIRECTORY_ENTRY_IMPORT for i in d.imports if i.name and b'translate@QCoreApplication' in i.name};es=[]
 cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);cs.skipdata=True
 for sec in p.sections:
  if not sec.Characteristics&0x20000000:continue
  hist=[]
  for a,n,m,o in cs.disasm_lite(sec.get_data(),base+sec.VirtualAddress):
   if m=='call' and o.startswith('qword ptr [rip + '):
    dest=a+n+int(o.split('rip + ')[1].split(']')[0],16)
    if dest in targets:
     for v in reversed(hist[-4:]):
      if v[2]=='lea' and v[3].startswith('r8, [rip + '):
       rva=v[0]+v[1]+int(v[3].split('rip + ')[1].split(']')[0],16)-base;off=p.get_offset_from_rva(rva)
       text=b[off:b.index(0,off)].decode('utf-8');es.append({'call_rva':a-base,'lea_rva':v[0]-base,'offset':off,'source':text});break
   hist.append((a,n,m,o));hist=hist[-4:]
 (root/'work'/(fn+'.qt-calls.json')).write_text(json.dumps(es,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
 print(fn,len(es))
allstrings=sorted(set(e['source'] for f in (root/'work').glob('*.qt-calls.json') for e in json.loads(f.read_text(encoding='utf-8'))))
(root/'work/qt-candidates.txt').write_text('\n'.join(s for s in allstrings if '\n' not in s and len(s)<90), encoding='utf-8', newline='\n')
