"""Modelo DC multicapa de un plano interior (malla 2D rasterizada del relleno real) + pistas F.Cu/B.Cu (1D)
+ vías (resistencia de barril) + pads (THT con radios de alivio térmico). Caídas en +3,3 V (In2) y GND (In1)."""
import sys, math, json, numpy as np
from matplotlib.path import Path
import scipy.sparse as sp, scipy.sparse.linalg as spla
from rutas import RES
from kicad_pcb import segments, vias, seglen, fps, zone_polygon
RHO20=1.72e-8; ALPHA=0.00393
def rho(T): return RHO20*(1+ALPHA*(T-20))
X0,X1,Y0,Y1=15.0,245.0,14.0,131.0
def zone_mask(net, layer, h):
    pts=zone_polygon(net,layer)
    nx=int(round((X1-X0)/h)); ny=int(round((Y1-Y0)/h))
    xc=X0+(np.arange(nx)+0.5)*h; yc=Y0+(np.arange(ny)+0.5)*h
    XX,YY=np.meshgrid(xc,yc,indexing='ij')
    m=Path(pts).contains_points(np.c_[XX.ravel(),YY.ravel()]).reshape(nx,ny)
    return m,xc,yc
class Model:
    def __init__(s, net, plane_layer, h=0.2, t_plane=15.2e-6, t_outer=35e-6, T=25.0, t_plate=20e-6):
        s.net=net; s.h=h; s.T=T
        s.mask,s.xc,s.yc=zone_mask(net,plane_layer,h)
        nx,ny=s.mask.shape
        s.pid=-np.ones((nx,ny),dtype=np.int64); s.pid[s.mask]=np.arange(s.mask.sum())
        s.N=int(s.mask.sum())
        s.rows=[];s.cols=[];s.vals=[]
        gs=t_plane/rho(T)   # sheet conductance (square cells)
        # plane links
        a=s.pid[:-1,:]; b=s.pid[1:,:]; m=(a>=0)&(b>=0); s._add(a[m],b[m],np.full(m.sum(),gs))
        a=s.pid[:,:-1]; b=s.pid[:,1:]; m=(a>=0)&(b>=0); s._add(a[m],b[m],np.full(m.sum(),gs))
        s.extra_nodes=[]; s.coords={}
        s.t_outer=t_outer; s.t_plate=t_plate; s.plane_layer=plane_layer
        s.names={}
    def _add(s,a,b,g):
        s.rows.append(np.asarray(a)); s.cols.append(np.asarray(b)); s.vals.append(np.asarray(g,dtype=float))
    def newnode(s,key):
        if key in s.coords: return s.coords[key]
        k=s.N+len(s.extra_nodes); s.extra_nodes.append(key); s.coords[key]=k; return k
    def cell(s,x,y):
        i=int((x-X0)/s.h); j=int((y-Y0)/s.h)
        if 0<=i<s.pid.shape[0] and 0<=j<s.pid.shape[1] and s.pid[i,j]>=0: return int(s.pid[i,j])
        # search nearest copper cell within 1 mm
        best=None
        r=int(1.0/s.h)+1
        for di in range(-r,r+1):
            for dj in range(-r,r+1):
                ii,jj=i+di,j+dj
                if 0<=ii<s.pid.shape[0] and 0<=jj<s.pid.shape[1] and s.pid[ii,jj]>=0:
                    d=di*di+dj*dj
                    if best is None or d<best[0]: best=(d,int(s.pid[ii,jj]))
        return None if best is None else best[1]
    def build_tracks(s):
        S=[x for x in segments() if x['net']==s.net]
        s.segs=S
        # nodes on each layer keyed by rounded coords
        def key(layer,x,y): return (layer,round(x,2),round(y,2))
        pts={}
        for x in S:
            for (px,py) in ((x['x1'],x['y1']),(x['x2'],x['y2'])): pts.setdefault(x['layer'],[]).append((px,py))
        for x in S:
            L=seglen(x)
            if L<1e-6: 
                s._add([s.newnode(key(x['layer'],x['x1'],x['y1']))],[s.newnode(key(x['layer'],x['x2'],x['y2']))],[1e6]); continue
            cuts=[0,1]
            for (px,py) in pts[x['layer']]:
                dx,dy=x['x2']-x['x1'],x['y2']-x['y1']; t=((px-x['x1'])*dx+(py-x['y1'])*dy)/L**2
                if 1e-4<t<1-1e-4 and abs((px-x['x1'])*dy-(py-x['y1'])*dx)/L<x['w']/2: cuts.append(t)
            cuts=sorted(set(cuts))
            for a,b in zip(cuts[:-1],cuts[1:]):
                xa,ya=x['x1']+(x['x2']-x['x1'])*a,x['y1']+(x['y2']-x['y1'])*a; xb,yb=x['x1']+(x['x2']-x['x1'])*b,x['y1']+(x['y2']-x['y1'])*b
                R=rho(s.T)*L*(b-a)*1e-3/(x['w']*1e-3*s.t_outer)
                s._add([s.newnode(key(x['layer'],xa,ya))],[s.newnode(key(x['layer'],xb,yb))],[1/R])
        s.key=key
    def _nodes_near(s,layer,x,y,rad):
        out=[]
        for k,idx in s.coords.items():
            if isinstance(k,tuple) and len(k)==3 and k[0]==layer and abs(k[1]-x)<=rad and abs(k[2]-y)<=rad: out.append((k,idx))
        return out
    def via_R(s, length_mm, drill):
        return rho(s.T)*length_mm*1e-3/(math.pi*(drill*1e-3-s.t_plate)*s.t_plate)
    def depth(s,layer):
        # z (mm) of layer mid-plane from top: F.Cu 0, In1 0.15, In2 1.45, B.Cu 1.6 (JLC04161H-2116)
        return {'F.Cu':0.0,'In1.Cu':0.1164+0.035,'In2.Cu':0.1164+0.035+0.0152+1.265,'B.Cu':1.6}[layer]
    def build_vias(s):
        for v in vias():
            if v['net']!=s.net: continue
            c=s.cell(v['x'],v['y'])
            for layer in ('F.Cu','B.Cu'):
                near=s._nodes_near(layer,v['x'],v['y'],v['size']/2+0.01)
                kn=s.newnode(s.key(layer,v['x'],v['y']))
                for k,idx in near:
                    if idx!=kn: s._add([idx],[kn],[1e5])
                if c is not None:
                    R=s.via_R(abs(s.depth(layer)-s.depth(s.plane_layer)),v['drill'])
                    s._add([kn],[c],[1/R])
    def build_pads(s, thermal_spokes=4, spoke_w=0.5, spoke_l=0.5, t_plane=15.2e-6):
        s.padnode={}
        for f in fps():
            for p in f['pads']:
                if p['net']!=s.net: continue
                name=f"{f['ref']}.{p['num']}"
                w,h=p['w'],p['h']
                if abs(p['rot']%180-90)<1: w,h=h,w
                layers=[l for l in p['layers'] if l.endswith('.Cu')]
                tht = p['type'] in ('thru_hole',) or '*.Cu' in p['layers']
                k=s.newnode(('pad',name,round(p['x'],3),round(p['y'],3)))
                s.padnode.setdefault(name,[]).append(k)
                lay_list=['F.Cu','B.Cu'] if tht else [l for l in layers if l in ('F.Cu','B.Cu')]
                for layer in lay_list:
                    for kk,idx in s._nodes_near(layer,p['x'],p['y'],max(w,h)/2+0.01):
                        if abs(kk[1]-p['x'])<=w/2+0.01 and abs(kk[2]-p['y'])<=h/2+0.01:
                            d=math.hypot(kk[1]-p['x'],kk[2]-p['y'])
                            R=rho(s.T)*max(d,0.01)*1e-3/(min(w,h)*1e-3*s.t_outer)
                            s._add([idx],[k],[1/R])
                if tht:
                    c=s.cell(p['x'],p['y'])
                    if c is not None:
                        # thermal relief spokes on plane + barrel
                        Rsp=rho(s.T)*spoke_l*1e-3/(spoke_w*1e-3*t_plane)/thermal_spokes
                        s._add([k],[c],[1/(Rsp+0.3e-3)])
                # SMD pad lying directly on a via (via-in-pad) handled by via proximity
                for v in vias():
                    if v['net']==s.net and abs(v['x']-p['x'])<=w/2 and abs(v['y']-p['y'])<=h/2:
                        kv=s.newnode(s.key('F.Cu' if 'F.Cu' in layers else 'B.Cu',v['x'],v['y']))
                        s._add([k],[kv],[1e5])
    def matrix(s):
        n=s.N+len(s.extra_nodes)
        r=np.concatenate(s.rows); c=np.concatenate(s.cols); g=np.concatenate(s.vals)
        A=sp.coo_matrix((np.r_[g,g,-g,-g],(np.r_[r,c,r,c],np.r_[r,c,c,r])),shape=(n,n)).tocsr()
        return A
    def solve(s, inj, ref_nodes):
        """inj: dict node->current entering the copper (A). ref_nodes: nodes forced to 0 V."""
        A=s.matrix(); n=A.shape[0]
        I=np.zeros(n)
        for k,v in inj.items(): I[k]+=v
        ref=np.zeros(n,bool); ref[list(ref_nodes)]=True
        free=np.where(~ref)[0]
        Af=A[free][:,free].tocsc()
        V=np.zeros(n)
        V[free]=spla.spsolve(Af,I[free])
        return V
    def components(s):
        A=s.matrix(); from scipy.sparse.csgraph import connected_components
        return connected_components(A,directed=False)

def run33(T=25.0,h=0.2,t_plane=15.2e-6):
    m=Model('+3.3V','In2.Cu',h=h,T=T,t_plane=t_plane); m.build_tracks(); m.build_vias(); m.build_pads(t_plane=t_plane)
    P=lambda n: m.padnode[n][0]; src=P('L3.2')
    loads={'J2.1':0.175,'J2.2':0.175,'U1.9':0.012,'U1.17':0.012,'U1.24':0.012,'U1.27':0.012,'U1.28':0.012,
           'FB3.1':0.060,'J4.1':0.010,'U7.8':0.020,'U5.9':0.001,'D2.2':0.012,'J6.5':0.00033,'J7.5':0.00033}
    inj={P(k):-v for k,v in loads.items()}; tot=sum(loads.values()); inj[src]=inj.get(src,0)+tot
    V=m.solve(inj,[src]); vs=V[P('R20.2')]
    return dict(I_total=tot,T=T,malla_mm=h,cobre_um=t_plane*1e6,
                caida_desde_L3_mV={k:round(-V[P(k)]*1e3,2) for k in ['C9.1','R20.2','J2.1','J2.2','U1.9','U1.24','U1.28','U7.8','FB3.1','J4.1','U5.9','D2.2']},
                caida_desde_realimentacion_R20_mV={k:round((vs-V[P(k)])*1e3,2) for k in ['J2.1','J2.2','U1.24','U1.28','U7.8','FB3.1','J4.1']})
def rungnd(T=25.0,h=0.2,t_plane=15.2e-6,audio=0.32):
    m=Model('GND','In1.Cu',h=h,T=T,t_plane=t_plane); m.build_tracks(); m.build_vias(); m.build_pads(t_plane=t_plane)
    P=lambda n,i=0: m.padnode[n][i]; ref=[P('J10.A1'),P('J10.A12')]; inj={}
    def add(name,I):
        ks=m.padnode[name]
        for k in ks: inj[k]=inj.get(k,0)+I/len(ks)
    for n in ('J2.22','J3.1','J3.2','J3.22'): add(n,0.35/4)
    for n in ('U1.23','U1.33','U1.48','U1.65'): add(n,0.06/4)
    for n in ('J1.3','J1.29','J1.36'): add(n,0.06/3)
    add('J4.2',0.01); add('U7.4',0.02); add('U5.10',0.001); add('R9.2',0.012)
    add('U6.1',-0.130)                       # buck: I_out(0,514 A) - I_in(0,384 A) entra al CI por GND
    add('U8.2',0.239); add('R22.2',0.0606)   # boost: I_in*D por el interruptor + I_LED por R22
    add('U4.7',audio)
    V=m.solve(inj,ref)
    pts=('U6.1','C15.2','U8.2','R22.2','C20.2','U4.7','C7.1','J2.22','J3.1','U1.65','J1.3','U7.4')
    return dict(I_retorno=sum(v for v in inj.values() if v>0),audio_A=audio,T=T,
                V_gnd_respecto_J10_mV={n:round((np.mean([V[k] for k in m.padnode[n]]) if n=='U1.65' else max(V[k] for k in m.padnode[n]))*1e3,2) for n in pts})
if __name__=='__main__':
    res={'mas3v3':[run33(25,0.2),run33(25,0.1),run33(60,0.2),run33(25,0.2,30e-6)],
         'gnd':[rungnd(25,0.2,audio=0.32),rungnd(25,0.2,audio=0.92),rungnd(60,0.2,audio=0.92)]}
    json.dump(res,open(RES/'pdn_planos.json','w'),indent=1,ensure_ascii=False)
    print(json.dumps(res,indent=1,ensure_ascii=False))
