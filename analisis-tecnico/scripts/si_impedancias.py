"""Impedancias del par USB y de las pistas QSPI (0,2 mm) con atlc y con el solver propio.
Apilado JLC04161H-2116: preimpregnado 0,1164 mm, er 4,16; Cu exterior 35 um; máscara 15 um, er 3,8.
Uso: python3 si_impedancias.py [--atlc] [--mc N]"""
import sys, json, shutil, subprocess, re, argparse, numpy as np
from rutas import RES, TMP
from si_solver2d import microstrip, modal_pair, single
import si_atlc_bmp
H=0.1164; ER=4.16; T=0.035; MASK=0.015; ERM=3.8
CASOS=[  # nombre, w, s, h, t, mask, nlíneas, er, er_mask
 ('se_0p2_mascara',0.2,0.25,H,T,MASK,1,ER,ERM),
 ('se_0p2_sin_mascara',0.2,0.25,H,T,0.0,1,ER,ERM),
 ('se_0p2_apilado_kicad',0.2,0.25,0.100,T,0.010,1,4.5,3.3),
 ('usb_0p2_0p25_mascara',0.2,0.25,H,T,MASK,2,ER,ERM),
 ('usb_0p2_0p25_sin_mascara',0.2,0.25,H,T,0.0,2,ER,ERM),
 ('usb_0p2_0p30_mascara',0.2,0.30,H,T,MASK,2,ER,ERM),
 ('usb_0p2_0p25_apilado_kicad',0.2,0.25,0.100,T,0.010,2,4.5,3.3)]
def propio(w,s,h,t,m,n,er,erm,fine=True):
    kw=dict(hmin=0.001,hmax=0.03,ratio=1.08) if fine else dict(hmin=0.002,hmax=0.05,ratio=1.12)
    if n==1:
        r=microstrip([w],[-w/2],h,t,mask=m,er=er,erm=erm,**kw); d=single(r)
        return dict(Z0=d['Z0'],ereff=d['ereff'])
    r=microstrip([w,w],[-(w+s/2),s/2],h,t,mask=m,er=er,erm=erm,**kw); d=modal_pair(r)
    return {k:float(v) for k,v in d.items()}
def atlc(nombre,w,s,h,t,m,n,er,erm,p=0.00291):
    bmp=TMP/f'{nombre}.bmp'
    g=si_atlc_bmp.make(str(bmp),w,s,h,t,m,p,nlines=n)
    out=subprocess.run(['atlc','-s','-S','-d',f'AC82AC={er}','-d',f'8C1C01={erm}',str(bmp)],capture_output=True,text=True).stdout
    nums=dict(re.findall(r'(Zo|Zodd|Zeven|Zdiff|Zcomm|Er|Er_odd|Er_even)=\s*([-\d.eE+]+)',out))
    return dict(geom_px={k:g[k] for k in ('w_eff','s_eff','h_eff','t_eff','mask_eff')},**{k:float(v) for k,v in nums.items()})
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--atlc',action='store_true'); ap.add_argument('--mc',type=int,default=300)
    a=ap.parse_args()
    res={}
    for c in CASOS:
        res[c[0]]={'propio':propio(*c[1:])}
        if a.atlc and shutil.which('atlc'): res[c[0]]['atlc']=atlc(*c)
        print(c[0],json.dumps(res[c[0]],default=float)[:300],flush=True)
    # Monte Carlo de fabricación (solver propio, malla media): h ±10 %, er ±0,15, w ±0,02 mm, t 30-45 um, máscara 10-25 um
    rng=np.random.default_rng(42); zd=[]; z0=[]
    for i in range(a.mc):
        h=H*(1+rng.uniform(-0.10,0.10)); er=ER+rng.uniform(-0.15,0.15); w=0.2+rng.uniform(-0.02,0.02)
        t=rng.uniform(0.030,0.045); m=rng.uniform(0.010,0.025); s=0.45-w   # paso entre ejes fijo 0,45 mm
        zd.append(propio(w,s,h,t,m,2,er,ERM,fine=False)['Zdiff']); z0.append(propio(w,0,h,t,m,1,er,ERM,fine=False)['Z0'])
    zd=np.array(zd); z0=np.array(z0)
    res['mc_fabricacion']=dict(N=a.mc,Zdiff=dict(media=zd.mean(),min=zd.min(),max=zd.max(),p1=np.percentile(zd,1),p99=np.percentile(zd,99)),
                               Z0=dict(media=z0.mean(),min=z0.min(),max=z0.max(),p1=np.percentile(z0,1),p99=np.percentile(z0,99)))
    print(res['mc_fabricacion'])
    json.dump(res,open(RES/'si_impedancias.json','w'),indent=1,default=float)
