"""Diafonía: matrices L/C por unidad de longitud (solver 2D) y solución exacta en frecuencia de la línea
acoplada de 2 conductores con terminaciones reales (driver Thevenin 40 ohm + 2 pF, receptor 5 pF), IFFT."""
import json, numpy as np
from scipy.linalg import expm
from rutas import RES
from si_solver2d import microstrip, modal_pair
H=0.1164; T=0.035; MASK=0.015; W=0.2; V=3.3
CASOS=[('SCK→MISO (QSPI host, F.Cu)',0.224,16.64),
       ('SPIM_SCLK→SPIM_MOSI (QSPI flash, F.Cu)',0.238,9.00),
       ('PCLK→DISP (B.Cu)',0.31,12.20),
       ('PCLK→DISP (F.Cu, junto a J1)',0.30,4.36),
       ('PCLK(U1)→R0 (F.Cu, tras R24)',0.30,3.41),
       ('PCLK→HSYNC (B.Cu)',0.766,1.85),
       ('SCK→B7: acercamiento mínimo QSPI–RGB (cota, supuesto paralelo 1 mm)',0.80,1.0)]
def matrices(gap):
    r=microstrip([W,W],[-(W+gap/2),gap/2],H,T,mask=MASK,hmin=0.001,hmax=0.03,ratio=1.08,boxw=4.0,boxh=2.5)
    m=modal_pair(r); return np.array(r['L']),np.array(r['C']),m
def simular(L,C,length_mm,tr_ns,rx='near',Rs_a=40.0,Rs_v=40.0,Cin=5e-12,Cdrv=2e-12):
    l=length_mm*1e-3; N=2**14; Tw=80e-9; dt=Tw/N; t=np.arange(N)*dt; tramp=tr_ns*1e-9/0.8
    ramp=lambda t0: np.clip((t-t0)/tramp,0,1)
    Sv=np.fft.rfft(V*(ramp(2e-9)-ramp(42e-9))); f=np.fft.rfftfreq(N,dt)
    oa=np.zeros_like(Sv); ov=np.zeros_like(Sv)
    for k,fk in enumerate(f):
        w=2*np.pi*max(fk,1e3)
        A=np.block([[np.zeros((2,2)),-1j*w*L],[-1j*w*C,np.zeros((2,2))]]); Phi=expm(A*l)
        z=lambda Cx,R=None: 1/(1j*w*Cx) if R is None else 1/(1/R+1j*w*Cx)
        Zrx=z(Cin,1e7); Zdv=z(Cdrv,Rs_v)
        Zv0,Zvl=(Zrx,Zdv) if rx=='near' else (Zdv,Zrx)
        E=np.zeros((4,4),complex); b=np.zeros(4,complex)
        E[0,0]=1; E[0,2]=Rs_a; b[0]=Sv[k]; E[1,1]=1; E[1,3]=Zv0
        E[2,:]=Phi[2,:]-Phi[0,:]/Zrx; E[3,:]=Phi[3,:]-Phi[1,:]/Zvl
        x=np.linalg.solve(E,b); Vl=Phi[:2,:]@x
        oa[k]=Vl[0]; ov[k]=x[1] if rx=='near' else Vl[1]
    va=np.fft.irfft(oa,N); vv=np.fft.irfft(ov,N); m=(t>1e-9)&(t<30e-9); i=np.argmax(np.abs(vv[m]))
    return float(vv[m][i]), float((va[m].max()-V)/V*100)
if __name__=='__main__':
    out=[]
    for nombre,gap,lmm in CASOS:
        L,C,m=matrices(gap); v=1/np.sqrt(L[0,0]*C[0,0]); Td=lmm*1e-3/v
        for tr in (1.0,2.0):
            tramp=tr*1e-9/0.8
            nx,_=simular(L,C,lmm,tr,'near'); fx,os_=simular(L,C,lmm,tr,'far')
            row=dict(caso=nombre,hueco_mm=gap,longitud_mm=lmm,tr_10_90_ns=tr,kL=m['kL'],kC=m['kC'],Td_ps=Td*1e12,
                     NEXT_analitico_mV=(m['kL']+m['kC'])/4*V*min(1,2*Td/tramp)*1e3,
                     FEXT_analitico_mV=(m['kC']-m['kL'])/2*V*Td/tramp*1e3,
                     receptor_extremo_cercano_mV=nx*1e3, receptor_extremo_lejano_mV=fx*1e3, sobreimpulso_agresor_pct=os_)
            out.append(row); print({k:(round(v,3) if isinstance(v,float) else v) for k,v in row.items()},flush=True)
    json.dump(out,open(RES/'si_diafonia.json','w'),indent=1,ensure_ascii=False)
