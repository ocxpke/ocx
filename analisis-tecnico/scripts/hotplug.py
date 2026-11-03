"""Transitorio de enchufado USB (hot-plug) en ngspice. El netlist se genera a partir del grafo real de cobre de
+5V (R+L por tramo, L' del solver 2D), con los condensadores en sus pads, el cable (R y L del lazo VBUS/GND),
modelo opcional de puerto USB-A (condensador de host + interruptor) y limitadores opcionales (TVS D1, USBLC6)."""
import sys, os, json, subprocess, numpy as np, itertools
from rutas import TMP
from pdn_5v import build
coords,edges,pn=build(T=25)
def Lp(w):  # nH/mm del solver 2D (0,5 mm -> 0,173; 0,8 mm -> 0,125); pads anchos ~0,10
    if w>=1.0: return 0.10
    return 0.173+(w-0.5)*(0.125-0.173)/0.3
AWG={'AWG20':0.0333,'AWG28':0.2129}   # ohm/m por conductor (Cu macizo, 20 °C)

def reduce_graph(edges, keep):
    import collections
    parent=list(range(1+max(max(a,b) for a,b,*_ in edges)))
    def f(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    E=[]
    for a,b,R,w,l in edges:
        L=Lp(w)*l*1e3*1e-9
        if R<3e-4 and L<5e-11: parent[f(a)]=f(b)
        else: E.append([a,b,R,L])
    keepr={f(k) for k in keep}
    E=[[f(a),f(b),R,L] for a,b,R,L in E if f(a)!=f(b)]
    changed=True
    while changed:
        changed=False
        deg=collections.Counter()
        for a,b,R,L in E: deg[a]+=1; deg[b]+=1
        for n,dg in deg.items():
            if dg==2 and n not in keepr:
                ee=[e for e in E if n in (e[0],e[1])]
                o=[e[1] if e[0]==n else e[0] for e in ee]
                if o[0]==o[1]: continue
                for e in ee: E.remove(e)
                E.append([o[0],o[1],ee[0][2]+ee[1][2],ee[0][3]+ee[1][3]])
                changed=True; break
    # parallel edges are fine in SPICE
    return E, f

def netlist(V0=5.25, cable='AWG20', length=1.0, Lpm=0.75e-6, Rcont=0.010, Rsrc=0.010,
            host=None, cer=6.5e-6, c40=100e-6, c40_esr=0.028, c40_esl=2.5e-9, with_c40=True,
            tvs=False, usblc=False, cer_esr=0.005, tstop=400e-6, label='x', trise=10e-9):
    _E,_f=reduce_graph(edges,[pn[k] for k in ('J10.A9','J10.A4','C40.1','C15.1','C20.1','C7.2','C11.2','C8.1','C37.1','D1.1','U2.5','U6.3','U8.6','L2.1','U4.6')])
    P_J10=_f(pn['J10.A9'])
    Rloop=2*AWG[cable]*length+Rcont
    Lloop=Lpm*length+15e-9          # + lazo de conectores y entrada a la PCB
    s=[f"* hotplug {label}"]
    if host is None:
        s.append(f"Vsrc src 0 PWL(0 0 2u 0 {2e-6+trise} {V0})")
        s.append(f"Rsrc src port {Rsrc}")
    else:
        # puerto USB-A del host: regulador -> interruptor/PTC -> condensador del puerto
        s.append(f"Vsrc src 0 DC {V0}")
        s.append(f"Rup src up1 {host['Rsw']}")
        s.append(f"Lup up1 port {host.get('Lup',50e-9)}")
        s.append(f"Chost port hc {host['C']}")
        s.append(f"Rhc hc 0 {host['esr']}")
    s.append(f"Rcab port c1 {Rloop}")
    s.append(f"Lcab c1 c2 {Lloop}")
    s.append(f"Vmeas c2 c3 0")
    if host is None:
        s.append("Rplug c3 n%d 1e-4" % P_J10)
    else:
        # contacto del enchufe: conductancia que pasa de ~0 a 1/2 mOhm con un cierre suave (tanh, ~10 ns)
        s.append("Bsw c3 n%d I=V(c3,n%d)*(1e-9+500*0.5*(1+tanh((time-2.02e-6)/3e-9)))" % (P_J10,P_J10))
    # grafo de cobre +5V de la PCB (reducido)
    keep=[pn[k] for k in ('J10.A9','J10.A4','C40.1','C15.1','C20.1','C7.2','C11.2','C8.1','C37.1','D1.1','U2.5','U6.3','U8.6','L2.1','U4.6')]
    E,f=reduce_graph(edges,keep)
    for i,(a,b,R,L) in enumerate(E):
        s.append(f"Re{i} n{a} m{i} {max(R,1e-4):.6e}")
        s.append(f"Le{i} m{i} n{b} {max(L,2e-11):.6e}")
    P={k:f(v) for k,v in pn.items()}
    def cap(name,node,C,esr,esl):
        s.append(f"C{name} n{node} k{name}a {C}")
        s.append(f"R{name} k{name}a k{name}b {esr}")
        s.append(f"L{name} k{name}b 0 {esl}")
    if with_c40: cap('C40',P['C40.1'],c40,c40_esr,c40_esl)
    for nm in ('C15.1','C20.1','C7.2'): cap(nm.split('.')[0],P[nm],cer,cer_esr,0.5e-9)
    cap('C11',P['C11.2'],0.9e-6,0.010,0.5e-9)
    cap('C8',P['C8.1'],0.1e-6,0.020,0.5e-9)
    cap('C37',P['C37.1'],0.1e-6,0.020,0.5e-9)
    s.append("Rbleed n%d 0 1e6" % P['J10.A9'])
    if tvs:   # P6SMB6.8CA bidireccional: codo en VBR(min)=6,45 V a 10 mA, Rdin ~65 mOhm
        s.append("DTVS 0 n%d DTVS" % P['D1.1'])
        s.append(".model DTVS D(IS=1e-14 N=1 BV=6.45 IBV=10m RS=0.065 CJO=2n)")
    if usblc: # zener VBUS-GND del USBLC6-2 (VBR mín ~6 V a 1 mA, Rd ~1,5 ohm supuesta) - NO verificado
        s.append("DUL 0 n%d DUL" % P['U2.5'])
        s.append(".model DUL D(IS=1e-14 N=1 BV=6.0 IBV=1m RS=1.5 CJO=20p)")
    probes={'J10':P['J10.A9'],'C40':P['C40.1'],'BUCK_VIN':P['U6.3'],'DIO5661_VIN':P['U8.6'],'L2':P['L2.1'],'PAM_VDD':P['U4.6']}
    vec=' '.join(f"v(n{n})" for n in probes.values())
    s.append(f".tran 20n {tstop} 0 20n")
    s.append(".options method=gear reltol=1e-4 abstol=1e-9 vntol=1e-6")
    s.append(".control\nrun\nwrdata hp_%s.txt %s i(Vmeas) %s\nquit\n.endc\n.end" % (label,vec,'v(port)'))
    return '\n'.join(s), list(probes.keys())
def run(label, keep=False, **kw):
    net,keys=netlist(label=label,**kw)
    cir=TMP/f'hp_{label}.cir'; cir.write_text(net)
    subprocess.run(['ngspice','-b',str(cir)],capture_output=True,text=True,cwd=TMP)
    d=np.loadtxt(TMP/f'hp_{label}.txt')
    t=d[:,0]
    res={'label':label}
    for i,k in enumerate(keys):
        v=d[:,1+2*i]; res[k]=float(v.max())
    I=d[:,1+2*len(keys)]; res['Ipk']=float(I.max())
    vport=d[:,1+2*len(keys)+2]; res['Vport_min']=float(vport[t>2e-6].min())
    tt=t[t>=2e-6]; II=I[t>=2e-6]
    res['Q_100us_uC']=float(np.trapezoid(II[tt<102e-6],tt[tt<102e-6])*1e6)
    res['I2t_A2s']=float(np.trapezoid(II**2,tt))
    if not keep: os.remove(TMP/f'hp_{label}.txt')
    else: res['wave']={'t':t.tolist(),**{k:d[:,1+2*i].tolist() for i,k in enumerate(keys)},'I':I.tolist(),'Vport':vport.tolist()}
    return res
if __name__=='__main__':
    print(run('prueba',V0=5.25,cable='AWG20',length=1.0))
