"""Read native core/cache masks without compiling a helper or sampling hardware."""
import ctypes as C
from ctypes import wintypes as W
import datetime
import json
from pathlib import Path
import struct
import sys

kernel=C.WinDLL('kernel32',use_last_error=True)
length=W.DWORD()
assert not kernel.GetLogicalProcessorInformation(None,C.byref(length)) and C.get_last_error()==122
buffer=C.create_string_buffer(length.value)
assert kernel.GetLogicalProcessorInformation(buffer,C.byref(length))
assert length.value%32==0
cores=[];caches=[]
for offset in range(0,length.value,32):
    mask,relationship=struct.unpack_from('<QI',buffer.raw,offset)
    if relationship==0:cores.append(mask)
    elif relationship==2 and buffer.raw[offset+16]==3:
        caches.append({'mask':mask,'bytes':struct.unpack_from('<I',buffer.raw,offset+20)[0]})
assert sorted(cores)==[3<<(2*n) for n in range(16)]
assert sorted(caches,key=lambda c:c['mask'])==[{'mask':65535,'bytes':96*1024**2},{'mask':4294901760,'bytes':32*1024**2}]
Path(sys.argv[1]).write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cores':cores,'l3_caches':caches},indent=2)+'\n')
