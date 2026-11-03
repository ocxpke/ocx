"""Barridos de hot-plug: (A) fuente rígida con C40, (B) sin C40 / con limitadores, (C) puerto USB-A (corriente
de entrada y caída del host), (D) sensibilidad a ESR de C40, L' del cable y C40, (E) mitigación con R en serie
con C40, y formas de onda para las figuras. Resultados en resultados/hotplug_*.json"""
import json, os
from multiprocessing import Pool
from rutas import RES, TMP
from hotplug import run
CABLES=[('AWG20',0.3),('AWG20',1.0),('AWG28',0.3),('AWG28',1.0)]
NODOS=['J10','C40','BUCK_VIN','DIO5661_VIN','L2','PAM_VDD']
def trabajos():
    J=[]
    for V0 in (5.25,5.5):
        for cab,l in CABLES:
            for Lpm in (0.5e-6,0.75e-6,1.0e-6):
                for cer in (6.5e-6,10e-6):
                    for c40 in (80e-6,100e-6,120e-6):
                        J.append(dict(grupo='A_rigida',V0=V0,cable=cab,length=l,Lpm=Lpm,cer=cer,c40=c40,Rcont=0.010,Rsrc=0.010))
                J.append(dict(grupo='B_sinC40',V0=V0,cable=cab,length=l,Lpm=Lpm,cer=6.5e-6,with_c40=False,Rcont=0.010,Rsrc=0.010))
                J.append(dict(grupo='B_sinC40_limitadores',V0=V0,cable=cab,length=l,Lpm=Lpm,cer=6.5e-6,with_c40=False,tvs=True,usblc=True,Rcont=0.010,Rsrc=0.010))
    for V0 in (5.0,5.25):
        for cab,l in CABLES:
            for Lpm in (0.5e-6,0.75e-6,1.0e-6):
                for hC,hesr in ((150e-6,0.03),(120e-6,0.15)):
                    J.append(dict(grupo='C_puertoA',V0=V0,cable=cab,length=l,Lpm=Lpm,cer=6.5e-6,c40=100e-6,Rcont=0.025,
                                  host=dict(C=hC,esr=hesr,Rsw=0.10,Lup=50e-9)))
    for V0 in (5.25,5.5):
        for cab,l in (('AWG20',0.3),('AWG20',1.0),('AWG20',2.0)):
            for Lpm in (0.75e-6,1.0e-6,1.25e-6):
                for esr in (0.015,0.020,0.028,0.040):
                    for c40 in (80e-6,100e-6):
                        J.append(dict(grupo='D_sensibilidad',V0=V0,cable=cab,length=l,Lpm=Lpm,c40_esr=esr,c40=c40,cer=6.5e-6,Rcont=0.010,Rsrc=0.010))
    for esr in (0.028,0.068,0.10,0.15,0.22,0.33,0.47):
        for cab,l in (('AWG20',0.3),('AWG20',1.0)):
            for Lpm in (1.0e-6,1.25e-6):
                J.append(dict(grupo='E_mitigacion',V0=5.5,cable=cab,length=l,Lpm=Lpm,c40_esr=esr,c40=80e-6,cer=6.5e-6,Rcont=0.010,Rsrc=0.010))
    return J
ONDAS={'nominal_5V25_AWG20_1m':dict(V0=5.25,cable='AWG20',length=1.0,Lpm=0.75e-6,c40=100e-6,cer=6.5e-6,Rcont=0.010,Rsrc=0.010),
       'peor_5V5_AWG20_1m':dict(V0=5.5,cable='AWG20',length=1.0,Lpm=1.25e-6,c40=80e-6,c40_esr=0.028,cer=6.5e-6,Rcont=0.010,Rsrc=0.010),
       'sinC40_5V5_AWG20_1m':dict(V0=5.5,cable='AWG20',length=1.0,Lpm=1.25e-6,with_c40=False,cer=6.5e-6,Rcont=0.010,Rsrc=0.010),
       'mitigado_150m_5V5_AWG20_1m':dict(V0=5.5,cable='AWG20',length=1.0,Lpm=1.25e-6,c40=80e-6,c40_esr=0.150,cer=6.5e-6,Rcont=0.010,Rsrc=0.010),
       'peor_5V5_AWG28_1m':dict(V0=5.5,cable='AWG28',length=1.0,Lpm=1.25e-6,c40=80e-6,cer=6.5e-6,Rcont=0.010,Rsrc=0.010)}
for cab,l in CABLES:
    ONDAS[f'puertoA_{cab}_{l}m']=dict(V0=5.0,cable=cab,length=l,Lpm=0.75e-6,c40=100e-6,cer=6.5e-6,Rcont=0.025,host=dict(C=150e-6,esr=0.03,Rsw=0.10,Lup=50e-9),tstop=300e-6)
def _w(a):
    i,j=a; kw={k:v for k,v in j.items() if k!='grupo'}; r=run(f'b{i}',**kw); r.update(j)
    r['Vmax']=max(r[n] for n in NODOS); r['nodo_Vmax']=max(NODOS,key=lambda n:r[n]); return r
def _o(a):
    k,kw=a; r=run(f'o_{k}',keep=True,**kw); return k,r
if __name__=='__main__':
    J=trabajos()
    with Pool(os.cpu_count()) as p:
        R=p.map(_w,list(enumerate(J)))
        W=dict(p.map(_o,list(ONDAS.items())))
    json.dump(R,open(RES/'hotplug_barridos.json','w'),indent=0)
    json.dump(W,open(TMP/'hotplug_ondas.json','w'))   # grande: solo para las figuras
    print(len(R),'simulaciones;',len(W),'formas de onda')
