"""Modelo térmico 2D de la placa: conducción en el plano (In1/In2 + pistas exteriores + FR4) con convección y
radiación por ambas caras. Tj = T_placa(bajo el CI) + P·(θJB del encapsulado + placa→planos).
Las pérdidas y las θ de encapsulado son estimaciones (rangos) NO verificadas contra la hoja de datos."""
import json, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spla
from rutas import RES, TMP
from pdn_planos import zone_mask, X0, Y0
from kicad_pcb import segments, fps
K_CU=390.0; K_FR4_PLANO=0.8
def mascara_placa(xc,yc):
    XX,YY=np.meshgrid(xc,yc,indexing='ij')
    m=(XX>16)&(XX<244)&(YY>14.5)&(YY<129.9)
    return m&~((XX>136)&(XX<176)&(YY<22.3))     # recorte de la antena
def construir(h=0.5):
    m1,xc,yc=zone_mask('GND','In1.Cu',h); m2,_,_=zone_mask('+3.3V','In2.Cu',h)
    nx,ny=len(xc),len(yc); sub=5; hs=h/sub
    xs=X0+(np.arange(nx*sub)+0.5)*hs; ys=Y0+(np.arange(ny*sub)+0.5)*hs; fino=np.zeros((nx*sub,ny*sub),bool)
    for s in segments():
        x1,y1,x2,y2,w=s['x1'],s['y1'],s['x2'],s['y2'],s['w']
        i0=max(0,int((min(x1,x2)-w-X0)/hs)); i1=min(nx*sub,int((max(x1,x2)+w-X0)/hs)+1)
        j0=max(0,int((min(y1,y2)-w-Y0)/hs)); j1=min(ny*sub,int((max(y1,y2)+w-Y0)/hs)+1)
        if i1<=i0 or j1<=j0: continue
        XX,YY=np.meshgrid(xs[i0:i1],ys[j0:j1],indexing='ij'); dx,dy=x2-x1,y2-y1; L2=dx*dx+dy*dy
        t=np.clip(((XX-x1)*dx+(YY-y1)*dy)/L2,0,1) if L2>0 else 0
        fino[i0:i1,j0:j1]|=np.hypot(XX-x1-t*dx,YY-y1-t*dy)<=w/2
    for f in fps():
        for p in f['pads']:
            w,hh=(p['h'],p['w']) if abs(p['rot']%180-90)<1 else (p['w'],p['h'])
            i0=max(0,int((p['x']-w/2-X0)/hs)); i1=min(nx*sub,int((p['x']+w/2-X0)/hs)+1)
            j0=max(0,int((p['y']-hh/2-Y0)/hs)); j1=min(ny*sub,int((p['y']+hh/2-Y0)/hs)+1)
            fino[i0:i1,j0:j1]=True
    cov=fino.reshape(nx,sub,ny,sub).mean(axis=(1,3)); bm=mascara_placa(xc,yc)
    G=np.where(bm,K_CU*(15.2e-6*m1+15.2e-6*m2+35e-6*cov)+K_FR4_PLANO*1.5e-3,0.0)   # W/K por cuadro
    return dict(G=G,xc=xc,yc=yc,bm=bm,h=h)
def resolver(B,fuentes,h_tot=20.0,Ta=25.0):
    G=B['G']; bm=B['bm']; h=B['h']*1e-3; nx,ny=G.shape
    idx=-np.ones((nx,ny),int); idx[bm]=np.arange(bm.sum()); N=bm.sum()
    rows=[];cols=[];vals=[]; diag=np.full(N,h_tot*h*h)
    for a,b,Ga,Gb in ((idx[:-1,:],idx[1:,:],G[:-1,:],G[1:,:]),(idx[:,:-1],idx[:,1:],G[:,:-1],G[:,1:])):
        m=(a>=0)&(b>=0); g=2*Ga[m]*Gb[m]/(Ga[m]+Gb[m]+1e-30); aa=a[m]; bb=b[m]
        rows+=[aa,bb]; cols+=[bb,aa]; vals+=[-g,-g]; np.add.at(diag,aa,g); np.add.at(diag,bb,g)
    A=sp.coo_matrix((np.concatenate(vals+[diag]),(np.concatenate(rows+[np.arange(N)]),np.concatenate(cols+[np.arange(N)]))),shape=(N,N)).tocsc()
    q=np.zeros(N); XX,YY=np.meshgrid(B['xc'],B['yc'],indexing='ij'); sel=[]
    for (x0,x1,y0,y1,P) in fuentes:
        mm=bm&(XX>=x0)&(XX<=x1)&(YY>=y0)&(YY<=y1); q[idx[mm]]+=P/mm.sum(); sel.append(mm)
    T=spla.spsolve(A,q); TT=np.full((nx,ny),np.nan); TT[bm]=T+Ta
    return TT,[float(np.nanmean(TT[mm])) for mm in sel]
F={f['ref']:f for f in fps()}
def caja(ref):
    xs=[p['x'] for p in F[ref]['pads']]; ys=[p['y'] for p in F[ref]['pads']]
    return (min(xs)-0.5,max(xs)+0.5,min(ys)-0.5,max(ys)+0.5)
# Pérdidas (W): (nominal, mínima, máxima) con el presupuesto de 1 A (ver INFORME §5)
P={'U6':(0.18,0.12,0.22),'U8':(0.10,0.06,0.15),'U1':(0.25,0.15,0.33),'U4':(0.20,0.20,0.20),
   'L3':(0.013,0.013,0.013),'L2':(0.025,0.025,0.025),'D3':(0.027,0.027,0.027),'R22':(0.012,0.012,0.012)}
# θ local = θJB(encapsulado) + placa→planos (preimpregnado/vías): (nominal, mín, máx) en K/W
TH={'U6':(50,35,75),'U8':(70,50,105),'U1':(7,4.5,12)}
if __name__=='__main__':
    B=construir(0.5); res={}
    for esc,(htot,Ta) in {'abierta_25C':(20.0,25.0),'carcasa_40C':(8.0,40.0)}.items():
        for esq,ci in (('nom',0),('max',2)):
            TT,Tb=resolver(B,[(*caja(r),P[r][ci]) for r in P],h_tot=htot,Ta=Ta); fila={}
            for k,r in enumerate(P):
                if r in TH:
                    th=TH[r][0] if esq=='nom' else TH[r][2]
                    fila[r]=dict(P_W=P[r][ci],T_placa=round(Tb[k],1),theta_local=th,Tj=round(Tb[k]+P[r][ci]*th,1))
            res[f'{esc}_{esq}']=fila; print(esc,esq,fila)
            if esq=='nom': np.save(TMP/f'termico_mapa_{esc}.npy',TT)
    for r in ('U6','U8','U1'):
        for htot in (20.0,8.0):
            _,Tb=resolver(B,[(*caja(r),1.0)],h_tot=htot,Ta=0.0); res[f'R_placa_ambiente_{r}_h{int(htot)}']=round(Tb[0],1)
    res['malla']=dict(xc0=float(B['xc'][0]),xc1=float(B['xc'][-1]),yc0=float(B['yc'][0]),yc1=float(B['yc'][-1]),h=B['h'])
    json.dump(res,open(RES/'termico.json','w'),indent=1)
    print({k:v for k,v in res.items() if k.startswith('R_')})
