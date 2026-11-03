"""Red resistiva 1D de +5V (solo pistas en F.Cu, sin vías ni zonas) -> caídas DC desde J10 a cada carga.
También genera la tabla de tensión extremo a extremo (fuente + cable + PCB) con el presupuesto de 1 A."""
import json, math, numpy as np
from rutas import RES
from kicad_pcb import segments, fps, seglen
RHO20=1.72e-8; ALPHA=0.00393
def rho(T): return RHO20*(1+ALPHA*(T-20))
def build(net='+5V', t_cu=35e-6, T=25.0):
    S=[s for s in segments() if s['net']==net]
    pads=[(f['ref']+'.'+p['num'],p) for f in fps() for p in f['pads'] if p['net']==net]
    coords=[]
    def node(x,y):
        for k,(xx,yy) in enumerate(coords):
            if abs(xx-x)<2e-3 and abs(yy-y)<2e-3: return k
        coords.append((x,y)); return len(coords)-1
    edges=[]; pts=[(s['x1'],s['y1']) for s in S]+[(s['x2'],s['y2']) for s in S]
    for s in S:
        x1,y1,x2,y2=s['x1'],s['y1'],s['x2'],s['y2']; L=seglen(s); cuts=[0.0,1.0]
        for (px,py) in pts:   # uniones en T
            if L<1e-9: continue
            t=((px-x1)*(x2-x1)+(py-y1)*(y2-y1))/L**2
            if 1e-4<t<1-1e-4 and abs((px-x1)*(y2-y1)-(py-y1)*(x2-x1))/L<s['w']/2: cuts.append(t)
        cuts=sorted(set(cuts))
        for a,b in zip(cuts[:-1],cuts[1:]):
            l=L*(b-a)*1e-3
            edges.append((node(x1+(x2-x1)*a,y1+(y2-y1)*a),node(x1+(x2-x1)*b,y1+(y2-y1)*b),rho(T)*l/(s['w']*1e-3*t_cu),s['w'],l))
    padnode={}
    for name,p in pads:
        c=node(p['x'],p['y']); padnode[name]=c; w,h=p['w'],p['h']
        if abs(p['rot']%180-90)<1: w,h=h,w
        for k,(x,y) in enumerate(coords):
            if k!=c and abs(x-p['x'])<=w/2+1e-3 and abs(y-p['y'])<=h/2+1e-3:
                d=math.hypot(x-p['x'],y-p['y'])*1e-3
                edges.append((k,c,rho(T)*max(d,1e-5)/(min(w,h)*1e-3*t_cu),min(w,h),d))
    return coords,edges,padnode
def solve(coords,edges,source_nodes,loads):
    n=len(coords); G=np.zeros((n,n))
    for a,b,R,w,l in edges:
        g=1/R; G[a,a]+=g; G[b,b]+=g; G[a,b]-=g; G[b,a]-=g
    I=np.zeros(n)
    for k,i in loads.items(): I[k]-=i
    free=[k for k in range(n) if k not in set(source_nodes)]; V=np.zeros(n)
    V[free]=np.linalg.solve(G[np.ix_(free,free)],I[free]); return V
# Presupuesto de corriente en +5V (peor caso pedido: ~1 A)
CARGAS={'presupuesto_1A':{'L2.1':0.310,'U8.6':0.002,'U6.3':0.375,'U4.6':0.320},
        'pico_audio_4ohm':{'L2.1':0.310,'U8.6':0.002,'U6.3':0.375,'U4.6':0.920}}
PUNTOS=['U6.3','C15.1','C40.1','D1.1','L2.1','U8.6','C20.1','U4.6','C7.2']
if __name__=='__main__':
    res={}
    for T in (25.0,60.0):
        coords,edges,pn=build(T=T); src=[pn['J10.A4'],pn['J10.A9']]
        for nombre,ld in CARGAS.items():
            V=solve(coords,edges,src,{pn[k]:v for k,v in ld.items()})
            res[f'{nombre}_{int(T)}C']=dict(I_total=sum(ld.values()),caidas_mV={k:round(-V[pn[k]]*1e3,1) for k in PUNTOS})
        if T==25.0:
            res['R_J10_a_pin_mOhm']={k:round(-solve(coords,edges,src,{pn[k]:1.0})[pn[k]]*1e3,1) for k in ('U6.3','L2.1','U8.6','U4.6','C40.1','C20.1','C7.2')}
    # Tabla extremo a extremo: cobre del cable (ambos conductores) + contactos, + PCB (+5V) + GND (de pdn_planos)
    AWG={'AWG20':0.0333,'AWG28':0.2129}
    gnd={'U6.3':0.0015,'U8.6':0.0039,'U4.6':0.0041}  # retorno por In1 con 1 A (pdn_planos.py)
    pcb={k:res['presupuesto_1A_25C']['caidas_mV'][k]/1e3+gnd[k] for k in gnd}
    tabla=[]
    for Vs in (5.0,4.75):
        for cab in ('AWG20','AWG28'):
            for l in (0.3,1.0):
                for tipo,rc in (('C-C',0.020),('A-C',0.040)):
                    R=2*AWG[cab]*l+rc; vj=Vs-1.007*R
                    tabla.append(dict(fuente_V=Vs,cable=f'{cab} {l} m {tipo}',R_lazo_mOhm=round(R*1e3),V_J10=round(vj,3),
                                      V_LMR51430=round(vj-pcb['U6.3'],3),V_DIO5661=round(vj-pcb['U8.6'],3),V_PAM8302A=round(vj-pcb['U4.6'],3),
                                      V_J10_pico_1p6A=round(Vs-1.607*R,3)))
    res['tabla_extremo_a_extremo_1A']=tabla
    json.dump(res,open(RES/'pdn_5v.json','w'),indent=1,ensure_ascii=False)
    for k,v in res.items():
        if k!='tabla_extremo_a_extremo_1A': print(k,v)
