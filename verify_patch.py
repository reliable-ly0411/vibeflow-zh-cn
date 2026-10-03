from pathlib import Path
import json,struct,hashlib,subprocess,re
import pefile
R=Path(__file__).resolve().parent
report=json.loads((R/'work/patch-manifest.json').read_text(encoding='utf-8'))
checks=[]
for fn,info in report.items():
 old=(R/'originals'/fn).read_bytes();new=(R/'work'/fn).read_bytes();a=pefile.PE(data=old);b=pefile.PE(data=new)
 assert hashlib.sha256(old).hexdigest()==info['original_sha256']
 assert hashlib.sha256(new).hexdigest()==info['patched_sha256']
 assert b.verify_checksum()
 assert a.OPTIONAL_HEADER.AddressOfEntryPoint==b.OPTIONAL_HEADER.AddressOfEntryPoint
 assert [(d.dll,[(i.name,i.ordinal,i.address) for i in d.imports]) for d in a.DIRECTORY_ENTRY_IMPORT]==[(d.dll,[(i.name,i.ordinal,i.address) for i in d.imports]) for d in b.DIRECTORY_ENTRY_IMPORT]
 assert [(d.VirtualAddress,d.Size) for d in a.OPTIONAL_HEADER.DATA_DIRECTORY]==[(d.VirtualAddress,d.Size) for d in b.OPTIONAL_HEADER.DATA_DIRECTORY]
 for sec in a.sections:
  if sec.Name.rstrip(b'\0') in [b'.rsrc',b'.reloc',b'.pdata']:
   start=sec.PointerToRawData;end=start+sec.SizeOfRawData
   assert old[start:end]==new[start:end]
 for e in info['entries']:
  target=b.get_offset_from_rva(e['target_rva']);enc='utf-16le' if e['kind']=='QStringLiteral' else 'utf-8';expected=e['translation'].encode(enc)
  assert new[target:target+len(expected)]==expected
  assert sorted(re.findall(r'%[1-9]\d*',e['source']))==sorted(re.findall(r'%[1-9]\d*',e['translation']))
  if e['kind']=='QStringLiteral':
   i=e['offset'];n=struct.unpack_from('<i',new,i+4)[0];offset=struct.unpack_from('<q',new,i+16)[0]
   assert b.get_rva_from_offset(i)+offset==e['target_rva'] and n*2==len(expected)
 checks.append({'file':fn,'references':len(info['entries']),'checksum':'pass','imports_and_entrypoint':'unchanged','exception_resource_relocation_tables':'unchanged'})
# Parse all changed JavaScript, including inline scripts, with Node.
from html.parser import HTMLParser
class Scripts(HTMLParser):
 def __init__(self):super().__init__();self.ins=False;self.s=[];self.cur='';self.kind=''
 def handle_starttag(self,t,a):
  if t=='script':self.ins=True;self.cur='';self.kind=dict(a).get('type','')
 def handle_endtag(self,t):
  if t=='script':
   if self.cur.strip():self.s.append((self.cur,self.kind))
   self.ins=False
 def handle_data(self,d):
  if self.ins:self.cur+=d
subprocess.run(['node','--check',str(R/'work/three-cad-viewer.js')],check=True)
ns=1
for fn in ['agent-conversation.html','cadviewer.html','terminal.html']:
 h=Scripts();h.feed((R/'work'/fn).read_text(encoding='utf-8'))
 for i,(s,k) in enumerate(h.s):
  path=R/'work'/f'check-{fn}-{i}.mjs';path.write_text(s, encoding='utf-8', newline='\n')
  subprocess.run(['node','--check',str(path)],check=True);ns+=1
checks.append({'javascript_syntax_checks':ns,'result':'pass'})
(R/'work/verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
print(json.dumps(checks,ensure_ascii=False))
