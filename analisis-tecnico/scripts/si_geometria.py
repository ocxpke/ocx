"""Geometría real de las redes rápidas: par USB (separación, longitudes, sesgo), tramos paralelos
QSPI↔RGB y dentro de cada bus, separación mínima entre grupos y continuidad del plano de referencia."""
import json, math, numpy as np
from collections import defaultdict
from matplotlib.path import Path
from rutas import RES
from kicad_pcb import segments, vias, seglen, zone_polygon, QSPI, SPIM, RGB, USB
S=segments()
def par_overlap(a,b,angtol=8.0):
    ax,ay=a['x2']-a['x1'],a['y2']-a['y1']; bx,by=b['x2']-b['x1'],b['y2']-b['y1']
    la=math.hypot(ax,ay); lb=math.hypot(bx,by)
    if la<1e-6 or lb<1e-6: return None
    ux,uy=ax/la,ay/la
    if abs(ux*by-uy*bx)/lb>math.sin(math.radians(angtol)): return None
    t1=(b['x1']-a['x1'])*ux+(b['y1']-a['y1'])*uy; t2=(b['x2']-a['x1'])*ux+(b['y2']-a['y1'])*uy
    lo=max(0,min(t1,t2)); hi=min(la,max(t1,t2))
    if hi-lo<=0: return None
    mx,my=(b['x1']+b['x2'])/2,(b['y1']+b['y2'])/2
    return hi-lo,abs((mx-a['x1'])*uy-(my-a['y1'])*ux)
def paralelos(G1,G2,maxcc):
    agg=defaultdict(lambda:[0.0,9e9])
    for a in S:
        if a['net'] not in G1: continue
        for b in S:
            if b['net'] not in G2 or b['layer']!=a['layer'] or a['net']==b['net']: continue
            r=par_overlap(a,b)
            if r and r[1]<=maxcc and r[0]>0.2:
                k=tuple(sorted((a['net'],b['net'])))+(a['layer'],)
                agg[k][0]+=r[0]/2 if (G1 is G2) else r[0]; agg[k][1]=min(agg[k][1],r[1]-(a['w']+b['w'])/2)
    return [dict(redes=k[:2],capa=k[2],paralelo_mm=round(v[0],2),hueco_min_mm=round(v[1],3)) for k,v in sorted(agg.items(),key=lambda kv:kv[1][1])]
def hueco_minimo(G1,G2):
    def pt_seg(px,py,s):
        dx,dy=s['x2']-s['x1'],s['y2']-s['y1']; L2=dx*dx+dy*dy
        t=0 if L2==0 else max(0,min(1,((px-s['x1'])*dx+(py-s['y1'])*dy)/L2))
        return math.hypot(px-s['x1']-t*dx,py-s['y1']-t*dy)
    best=(9e9,None)
    for a in S:
        if a['net'] not in G1: continue
        for b in S:
            if b['net'] not in G2 or b['layer']!=a['layer']: continue
            d=min(pt_seg(a['x1'],a['y1'],b),pt_seg(a['x2'],a['y2'],b),pt_seg(b['x1'],b['y1'],a),pt_seg(b['x2'],b['y2'],a))-(a['w']+b['w'])/2
            if d<best[0]: best=(d,dict(redes=(a['net'],b['net']),capa=a['layer'],cerca_de=(round(a['x1'],1),round(a['y1'],1))))
    return dict(hueco_mm=round(best[0],3),**best[1])
def huecos_plano():
    P={'F.Cu':Path(zone_polygon('GND','In1.Cu')),'B.Cu':Path(zone_polygon('+3.3V','In2.Cu'))}
    out={}; peor=[]
    for s in S:
        g='QSPI' if s['net'] in QSPI else 'SPIM' if s['net'] in SPIM else 'RGB' if s['net'] in RGB else 'USB' if s['net'] in USB else None
        if not g: continue
        L=seglen(s); n=max(2,int(L/0.05)); t=np.linspace(0,1,n)
        ok=P[s['layer']].contains_points(np.c_[s['x1']+(s['x2']-s['x1'])*t,s['y1']+(s['y2']-s['y1'])*t])
        v=L*(1-ok.mean()); o=out.setdefault(f'{g} {s["layer"]}',[0,0]); o[0]+=L; o[1]+=v
        if v>0.05: peor.append(v)
    return dict(por_grupo={k:dict(longitud_mm=round(a,1),sobre_hueco_mm=round(b,2)) for k,(a,b) in out.items()},
                tramo_continuo_max_sobre_hueco_mm=round(max(peor),2))
if __name__=='__main__':
    res={}
    U=['/Power_Supply_USB/USB_C_D+','USB_D+']; D=['/Power_Supply_USB/USB_C_D-','USB_D-']
    hist=defaultdict(float)
    for a in S:
        if a['net'] not in U: continue
        for b in S:
            if b['net'] in D and b['layer']==a['layer']:
                r=par_overlap(a,b)
                if r and r[1]<1.5: hist[f"{a['layer']} hueco {r[1]-0.2:.3f} mm"]+=r[0]
    res['usb_tramos_acoplados']={k:round(v,2) for k,v in sorted(hist.items(),key=lambda kv:-kv[1])}
    L={n:sum(seglen(s) for s in S if s['net']==n) for n in U+D}
    res['usb_longitudes_mm']={k:round(v,2) for k,v in L.items()}
    res['usb_sesgo_mm']=round((L[U[0]]+L[U[1]])-(L[D[0]]+L[D[1]]),2)
    res['usb_vias']=sum(1 for v in vias() if v['net'] in USB)
    res['qspi_vs_rgb_paralelos_3mm']=paralelos(QSPI,RGB,3.0)
    res['qspi_vs_rgb_hueco_minimo']=hueco_minimo(QSPI,RGB)
    res['spim_vs_rgb_hueco_minimo']=hueco_minimo(SPIM,RGB)
    res['qspi_interno']=paralelos(QSPI,QSPI,1.0)
    res['spim_interno']=paralelos(SPIM,SPIM,1.0)
    res['pclk_vecinos']=paralelos({'PCLK','Net-(U1-PCLK)'},RGB,1.0)
    res['plano_referencia']=huecos_plano()
    json.dump(res,open(RES/'si_geometria.json','w'),indent=1,ensure_ascii=False)
    print(json.dumps(res,indent=1,ensure_ascii=False)[:3000])
