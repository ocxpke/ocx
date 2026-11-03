"""Lector mínimo de .kicad_pcb (KiCad 10, S-expresiones): huellas, pads, pistas, vías y zonas."""
import re, math
from functools import lru_cache
from rutas import PCB
_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)
def parse(text):
    stack=[[]]; pos=0
    while True:
        m=_tok.match(text,pos)
        if not m: break
        pos=m.end()
        if m.group(1): stack.append([])
        elif m.group(2): x=stack.pop(); stack[-1].append(x)
        elif m.group(3) is not None: stack[-1].append(m.group(3).replace('\\"','"'))
        else: stack[-1].append(m.group(4))
    return stack[0][0]
def find(node,key): return [c for c in node if isinstance(c,list) and c and c[0]==key]
def find1(node,key,default=None):
    r=find(node,key); return r[0] if r else default
def val(node,key,default=None,idx=1):
    r=find1(node,key); return r[idx] if r is not None and len(r)>idx else default
@lru_cache(maxsize=1)
def pcb():
    return parse(PCB.read_text(encoding='utf-8'))
@lru_cache(maxsize=1)
def _fps():
    out=[]
    for f in find(pcb(),'footprint'):
        at=find1(f,'at'); x,y=float(at[1]),float(at[2]); rot=float(at[3]) if len(at)>3 else 0.0
        props={p[1]:p[2] for p in find(f,'property')}
        pads=[]
        for p in find(f,'pad'):
            pat=find1(p,'at'); px,py=float(pat[1]),float(pat[2])
            prot=float(pat[3]) if len(pat)>3 else 0.0   # orientación absoluta del pad (incluye la de la huella)
            a=math.radians(rot)
            ax= x + px*math.cos(a) + py*math.sin(a)
            ay= y - px*math.sin(a) + py*math.cos(a)
            size=find1(p,'size')
            pads.append(dict(num=p[1],type=p[2],shape=p[3],x=ax,y=ay,rot=prot,w=float(size[1]),h=float(size[2]),
                             net=val(p,'net'),layers=find1(p,'layers')[1:],drill=find1(p,'drill')))
        out.append(dict(lib=f[1],x=x,y=y,rot=rot,layer=val(f,'layer'),props=props,pads=pads,
                        ref=props.get('Reference'),value=props.get('Value')))
    return out
def fps(): return _fps()
@lru_cache(maxsize=1)
def _segments():
    out=[]
    for s in find(pcb(),'segment'):
        a=find1(s,'start'); b=find1(s,'end')
        out.append(dict(x1=float(a[1]),y1=float(a[2]),x2=float(b[1]),y2=float(b[2]),w=float(val(s,'width')),
                        layer=val(s,'layer'),net=val(s,'net')))
    return out
def segments(): return _segments()
@lru_cache(maxsize=1)
def _vias():
    out=[]
    for v in find(pcb(),'via'):
        at=find1(v,'at')
        out.append(dict(x=float(at[1]),y=float(at[2]),size=float(val(v,'size')),drill=float(val(v,'drill')),
                        layers=find1(v,'layers')[1:],net=val(v,'net')))
    return out
def vias(): return _vias()
def seglen(s): return math.hypot(s['x2']-s['x1'],s['y2']-s['y1'])
def zone_polygon(net, layer):
    import numpy as np
    for z in find(pcb(),'zone'):
        if val(z,'net')==net and val(z,'layer')==layer:
            fp_=find1(z,'filled_polygon')
            return np.array([[float(c[1]),float(c[2])] for c in find1(fp_,'pts')[1:]])
    raise KeyError((net,layer))
def stackup():
    st=find1(find1(pcb(),'setup'),'stackup'); out=[]
    for l in find(st,'layer'):
        out.append(dict(name=l[1],type=val(l,'type'),thickness=val(l,'thickness'),er=val(l,'epsilon_r'),tand=val(l,'loss_tangent')))
    return out
# Grupos de redes usados en el análisis
QSPI={'/SCK','/MOSI','/MISO','/CS_N','/GPIO0{slash}IO2','/GPIO1{slash}IO3'}
SPIM={'SPIM_SCLK','SPIM_SS_N','SPIM_MOSI','SPIM_MISO','SPIM_IO2','SPIM_IO3'}
RGB={f'{c}{i}' for c in 'RGB' for i in range(8)}|{'PCLK','Net-(U1-PCLK)','DE','HSYNC','VSYNC','DISP'}
USB={'/Power_Supply_USB/USB_C_D+','/Power_Supply_USB/USB_C_D-','USB_D+','USB_D-'}
