"""Monte Carlo de tolerancias: salida del LMR51430, corriente del retroiluminado (DIO5661) y corte del
filtro RC-RC de audio (con la carga de entrada del PAM8302A). Límites de tolerancia = ±3σ (gauss) o uniforme."""
import json, itertools, numpy as np
from rutas import RES
rng=np.random.default_rng(20261103)
def tol(nom,rel,n,dist): return nom*(1+(rng.uniform(-rel,rel,n) if dist=='uniforme' else rng.normal(0,rel/3,n)))
def st(x):
    p=np.percentile(x,[0.135,50,99.865])
    return dict(media=float(x.mean()),sigma=float(x.std()),min=float(x.min()),max=float(x.max()),p0_135=float(p[0]),p50=float(p[1]),p99_865=float(p[2]))
def H(f,R4,C10,R3,C29,Ri=10e3,Cc=0.22e-6,Rout=30.0):
    """AUDIO_L (BT817, Rout) -> R4 -> C10 || -> R3 -> C29 || -> C12 -> Ri (entrada PAM8302A). Devuelve V(Ri)/Vin."""
    s=2j*np.pi*f; ZL=Ri+1/(s*Cc); ZB=1/(s*C29+1/ZL); ZA=1/(s*C10+1/(R3+ZB))
    vA=ZA/(Rout+R4+ZA); vB=vA*ZB/(R3+ZB); return vB*Ri/ZL
def fc(R4,C10,R3,C29,Ri,Cc=0.22e-6,Rout=30.0,fref=1e3):
    R4=np.atleast_1d(R4).astype(float); ref=np.abs(H(fref,R4,C10,R3,C29,Ri,Cc,Rout)); lo=np.full_like(R4,1e3); hi=np.full_like(R4,2e5)
    for _ in range(60):
        mid=np.sqrt(lo*hi); m=np.abs(H(mid,R4,C10,R3,C29,Ri,Cc,Rout))/ref>1/np.sqrt(2); lo=np.where(m,mid,lo); hi=np.where(m,hi,mid)
    return np.sqrt(lo*hi)
if __name__=='__main__':
    N=200_000; res={}
    # 1) LMR51430: Vout = VFB (1 + R20/R21)
    res['buck_nominal_V']=0.6*(1+100/22)
    res['buck_peor_caso_V']=(0.594*(1+99/22.22),0.606*(1+101/21.78))
    for d in ('gauss','uniforme'):
        res[f'buck_{d}']=st(tol(0.6,0.01,N,d)*(1+tol(100e3,0.01,N,d)/tol(22e3,0.01,N,d)))
    # 2) DIO5661: I_LED = VFB/R22. Tolerancia de VFB NO verificada -> paramétrica
    res['iled_nominal_mA']=0.2/3.3*1e3
    for vt in (0.02,0.04,0.05):
        res[f'iled_vfb{int(vt*100)}pct_peor_caso_mA']=(0.2*(1-vt)/3.333*1e3,0.2*(1+vt)/3.267*1e3)
        for d in ('gauss','uniforme'):
            res[f'iled_vfb{int(vt*100)}pct_{d}']=st(tol(0.2,vt,N,d)/tol(3.3,0.01,N,d)*1e3)
    # 3) Filtro de audio
    a2=3.3e3*4.7e-9*1e3*4.7e-9; a1=3.3e3*4.7e-9+1e3*4.7e-9+3.3e3*4.7e-9
    res['audio_polos_sin_carga_Hz']=sorted((-np.roots([a2,a1,1])/(2*np.pi)).real.tolist())
    res['audio_etapas_aisladas_Hz']=(1/(2*np.pi*3.3e3*4.7e-9),1/(2*np.pi*1e3*4.7e-9))
    res['audio_paso_alto_C12_Ri10k_Hz']=1/(2*np.pi*10e3*0.22e-6)
    n=100_000
    for Ri in (1e12,40e3,20e3,10e3,5e3):
        R4=tol(3.3e3,0.01,n,'gauss'); R3=tol(1e3,0.01,n,'gauss'); C10=tol(4.7e-9,0.10,n,'gauss'); C29=tol(4.7e-9,0.10,n,'gauss')
        f=fc(R4,C10,R3,C29,np.full(n,Ri))
        corners=[fc(3.3e3*a,4.7e-9*c,1e3*b,4.7e-9*d,Ri)[0] for a,b,c,d in itertools.product((0.99,1.01),(0.99,1.01),(0.9,1.1),(0.9,1.1))]
        res[f'audio_fc_Ri_{int(Ri) if Ri<1e9 else "inf"}']=dict(nominal_Hz=float(fc(3.3e3,4.7e-9,1e3,4.7e-9,Ri)[0]),
            ganancia_banda_dB=float(20*np.log10(np.abs(H(1e3,3.3e3,4.7e-9,1e3,4.7e-9,Ri)))),
            peor_caso_Hz=(min(corners),max(corners)),mc_gauss=st(f))
    for fr in (20,100,1e3,10e3,20e3,48e3,100e3,250e3,1e6):
        res[f'audio_atenuacion_dB_{int(fr)}Hz_Ri10k']=float(20*np.log10(np.abs(H(fr,3.3e3,4.7e-9,1e3,4.7e-9))/np.abs(H(1e3,3.3e3,4.7e-9,1e3,4.7e-9))))
    json.dump(res,open(RES/'mc_tolerancias.json','w'),indent=1,default=float)
    for k,v in res.items(): print(k,v)
