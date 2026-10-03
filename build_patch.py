#!/usr/bin/env python3
"""Version-pinned display-string patch. Requires pefile and capstone.
QString literals keep their headers/identities; only size and relative text offset
change. ASCII call sites are patched only for verified direct fromAscii_helper
calls with an immediately preceding constant length. No executable logic changes.
"""
from pathlib import Path
import struct,json,hashlib,re
import pefile,capstone
ROOT=Path(__file__).resolve().parent
PINNED_HASHES=json.loads((ROOT/'original-hashes.json').read_text(encoding='utf-8'))
def align(n,a):return (n+a-1)//a*a

def build(src,dst,mapping):
 original=Path(src).read_bytes()
 assert hashlib.sha256(original).hexdigest()==PINNED_HASHES[Path(src).name], 'Unsupported input build'
 p=pefile.PE(data=original);out=bytearray(original)
 assert p.FILE_HEADER.Machine==0x8664
 assert not p.OPTIONAL_HEADER.DATA_DIRECTORY[4].VirtualAddress,'Signed PE: refuse to invalidate signature'
 newva=align(max(s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData) for s in p.sections),p.OPTIONAL_HEADER.SectionAlignment)
 raw=align(len(out),p.OPTIONAL_HEADER.FileAlignment);out.extend(b'\0'*(raw-len(out)));payload=bytearray();audit=[]
 def add(text,enc):
  while len(payload)%8:payload.append(0)
  rva=newva+len(payload);payload.extend(text.encode(enc)+ (b'\0\0' if enc=='utf-16le' else b'\0'));return rva
 # Qt's QArrayData header is stable in this exact Qt5 x64 build.
 for i in range(0,len(original)-26,8):
  ref,n,alloc,offset=struct.unpack_from('<iiQq',original,i)
  if ref!=-1 or alloc!=0 or offset!=24 or not 0<n<20000 or i+26+2*n>len(original):continue
  if original[i+24+2*n:i+26+2*n]!=b'\0\0':continue
  try:source=original[i+24:i+24+2*n].decode('utf-16le')
  except UnicodeError:continue
  if source not in mapping:continue
  target=mapping[source]
  if Path(src).name=='VibeFlowStudio.exe':
   target={0x3cdd20:'订阅方案',0x3ce560:'订阅方案',0x4a7a40:'行间',0x4c42b8:'行间'}.get(i,target)
  # Keep placeholder sequence exactly once for every source placeholder.
  assert sorted(re.findall(r'%[1-9]\d*',source))==sorted(re.findall(r'%[1-9]\d*',target)),source
  dest=add(target,'utf-16le');rva=p.get_rva_from_offset(i)
  struct.pack_into('<i',out,i+4,len(target.encode('utf-16le'))//2)
  struct.pack_into('<q',out,i+16,dest-rva)
  audit.append({'kind':'QStringLiteral','offset':i,'source':source,'translation':target,'target_rva':dest})
 imports={x.address:x.name for d in p.DIRECTORY_ENTRY_IMPORT for x in d.imports}
 helper={a for a,n in imports.items() if n and b'fromAscii_helper@QString' in n}
 cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);cs.detail=True;cs.skipdata=True
 # Three-instruction sequence: mov edx,len; lea rcx,[rip+str]; call [rip+helper].
 for sec in p.sections:
  if not sec.Characteristics & 0x20000000:continue
  recent=[]
  for a,n,m,ops in cs.disasm_lite(sec.get_data(),p.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress):
   recent.append((a,n,m,ops));recent=recent[-3:]
   if m!='call' or len(recent)!=3:continue
   v,lea,call=recent
   if v[2]!='mov' or not v[3].startswith('edx, ') or lea[2]!='lea' or not lea[3].startswith('rcx, [rip + ') or not ops.startswith('qword ptr [rip + '):continue
   try:
    func=a+n+int(ops.split('rip + ')[1].split(']')[0],16)
    if func not in helper:continue
    size=int(v[3].split(', ')[1],0)
    srva=lea[0]+lea[1]+int(lea[3].split('rip + ')[1].split(']')[0],16)-p.OPTIONAL_HEADER.ImageBase
    soff=p.get_offset_from_rva(srva)
    if not 0<size<5000:continue
    source=original[soff:soff+size].decode('ascii')
   except (ValueError,UnicodeError,IndexError):continue
   if source not in mapping:continue
   target=mapping[source];dest=add(target,'utf-8');voff=p.get_offset_from_rva(v[0]-p.OPTIONAL_HEADER.ImageBase);loff=p.get_offset_from_rva(lea[0]-p.OPTIONAL_HEADER.ImageBase)
   assert original[voff]==0xba and v[1]==5 and original[loff:loff+3]==b'\x48\x8d\x0d' and lea[1]==7
   struct.pack_into('<I',out,voff+1,len(target.encode('utf-8')))
   struct.pack_into('<i',out,loff+3,dest-(lea[0]+7-p.OPTIONAL_HEADER.ImageBase))
   audit.append({'kind':'QStringUtf8','offset':soff,'call_rva':a-p.OPTIONAL_HEADER.ImageBase,'source':source,'translation':target,'target_rva':dest})
 # The DLL call list records direct QCoreApplication::translate calls only.
 calls=ROOT/'work'/(Path(src).name+'.qt-calls.json')
 if calls.exists():
  for e in json.loads(calls.read_text(encoding='utf-8')):
   source=e['source']
   if source not in mapping:continue
   target=mapping[source];dest=add(target,'utf-8');loff=p.get_offset_from_rva(e['lea_rva'])
   assert original[loff:loff+3]==b'\x4c\x8d\x05'
   struct.pack_into('<i',out,loff+3,dest-(e['lea_rva']+7))
   audit.append({'kind':'QCoreApplicationTranslate','offset':e['offset'],'source':source,'translation':target,'target_rva':dest})
 assert audit
 section_header=p.sections[-1].get_file_offset()+40
 assert section_header+40<=min(s.PointerToRawData for s in p.sections)
 assert not any(out[section_header:section_header+40])
 header=struct.pack('<8sIIIIIIHHI',b'.vfzh\0\0\0',len(payload),newva,align(len(payload),p.OPTIONAL_HEADER.FileAlignment),raw,0,0,0,0,0x40000040)
 out[section_header:section_header+40]=header
 struct.pack_into('<H',out,p.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),len(p.sections)+1)
 struct.pack_into('<I',out,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(newva+len(payload),p.OPTIONAL_HEADER.SectionAlignment))
 struct.pack_into('<I',out,p.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'),p.OPTIONAL_HEADER.SizeOfInitializedData+align(len(payload),p.OPTIONAL_HEADER.FileAlignment))
 out.extend(payload);out.extend(b'\0'*(align(len(out),p.OPTIONAL_HEADER.FileAlignment)-len(out)))
 check=pefile.PE(data=out);struct.pack_into('<I',out,p.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),check.generate_checksum())
 # Re-read every redirected string through its actual mapped pointer.
 check=pefile.PE(data=out)
 for entry in audit:
  i=check.get_offset_from_rva(entry['target_rva']);encoded=entry['translation'].encode('utf-16le' if entry['kind']=='QStringLiteral' else 'utf-8')
  assert out[i:i+len(encoded)]==encoded
 Path(dst).write_bytes(out)
 return {'original_sha256':hashlib.sha256(original).hexdigest(),'patched_sha256':hashlib.sha256(out).hexdigest(),'entries':audit}
if __name__=='__main__':
 mapping={}
 for line in (ROOT/'translations.tsv').read_text(encoding='utf-8').splitlines():
  if line and not line.startswith('# '):
   en,zh=line.split('\t');mapping[en]=zh
 extra=ROOT/'translations-extra.json'
 if extra.exists():mapping.update(json.loads(extra.read_text(encoding='utf-8')))
 # Preserve original keyboard mnemonics for ParaView menu actions.
 for en in (ROOT/'work/qt-candidates.txt').read_text(encoding='utf-8').splitlines():
  bare=en.replace('&','')
  if '&' in en and bare in mapping:
   key=en[en.index('&')+1:en.index('&')+2]
   mapping[en]=mapping[bare]+'(&'+key.upper()+')'
 reports={};used=set()
 for fn in ['VibeFlowStudio.exe','pqCore-pv5.11.dll','pqApplicationComponents-pv5.11.dll','pqComponents-pv5.11.dll','pqWidgets-pv5.11.dll']:
  file_mapping=dict(mapping)
  if fn=='pqComponents-pv5.11.dll':file_mapping['Rank']='进程编号（Rank）'
  report=build(ROOT/'originals'/fn,ROOT/'work'/fn,file_mapping);reports[fn]=report
  used.update(e['source'] for e in report['entries'])
  print(fn,len(report['entries']))
 (ROOT/'work/patch-manifest.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
 (ROOT/'work/unmatched.json').write_text(json.dumps(sorted(set(mapping)-used),ensure_ascii=False,indent=2), encoding='utf-8', newline='\n')
 print(json.dumps({'entries':sum(len(r['entries']) for r in reports.values()),'unique_sources':len(used),'unmatched':len(set(mapping)-used)}))
