from pathlib import Path
import pefile,json,hashlib,re
R=Path(__file__).resolve().parent;W=R/'work'
n='vtkRemotingApplication-pv5.11.dll';a=pefile.PE(str(R/'originals'/n));b=pefile.PE(str(W/n))
assert a.OPTIONAL_HEADER.AddressOfEntryPoint==b.OPTIONAL_HEADER.AddressOfEntryPoint
assert len(a.sections)==len(b.sections)
for sa,sb in zip(a.sections,b.sections):
 assert sa.Name==sb.Name and sa.VirtualAddress==sb.VirtualAddress and sa.PointerToRawData==sb.PointerToRawData
 if sa.Characteristics&0x20000000: assert sa.get_data()==sb.get_data()
assert b.OPTIONAL_HEADER.CheckSum==b.generate_checksum()
for fn in ['paraview-init.py','servermanager.py','smtrace.py']:compile((W/fn).read_text(encoding='utf-8'),fn,'exec')
m=json.loads((W/'api-label-map.json').read_text(encoding='utf-8'))
x=json.loads((W/'xml-manifest.json').read_text(encoding='utf-8'))
for e in x['vtk_labels']:
 if e['kind'] in ['label','new_proxy_label','new_property_label']:
  assert re.sub('[^a-zA-Z0-9_]','',m[e['translation']])==re.sub('[^a-zA-Z0-9_]','',e['source'])
out={'vtk_executable_sections':'byte-identical to original','vtk_pe_checksum':'pass','python_compile':3,'python_label_compatibility':len(m),'categories':len(x['categories']),'xml_text_entries':len(x['vtk_labels']),'changed_xml_documents':x['changed_xml_groups']}
(W/'v2-static-verification.json').write_text(json.dumps(out,indent=2), encoding='utf-8', newline='\n');print(json.dumps(out))
