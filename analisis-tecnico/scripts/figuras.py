"""Figuras del informe (PNG). Requiere haber ejecutado los scripts de resultados (ver ejecutar_todo.sh)."""
import json, numpy as np, matplotlib as mpl
mpl.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from rutas import RES, FIG, TMP
from kicad_pcb import segments, fps, QSPI, SPIM, RGB, USB
# Paleta categórica de referencia (orden fijo) y colores de texto/superficie
S=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300','#6250d6','#e34948']
CRIT='#d03b3b'; SURF='#fcfcfb'; T1='#0b0b0b'; T2='#52514e'; GRID='#e4e3df'
plt.rcParams.update({'figure.facecolor':SURF,'axes.facecolor':SURF,'savefig.facecolor':SURF,'axes.edgecolor':'#bdbbb5',
    'axes.labelcolor':T2,'xtick.color':T2,'ytick.color':T2,'text.color':T1,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.6,
    'axes.spines.top':False,'axes.spines.right':False,'font.size':10,'axes.titlesize':11,'axes.titleweight':'bold',
    'legend.frameon':False,'lines.linewidth':2})
SEG=segments(); F=fps(); FD={f['ref']:f for f in F}
def fig_layout():
    PCLK={'PCLK','Net-(U1-PCLK)'}; RGBd=RGB-PCLK
    grupos=[('QSPI host (ESP32↔BT817)',QSPI,S[1]),('Bus RGB + sincronismos',RGBd,S[0]),('PCLK',PCLK,S[6]),('QSPI flash (BT817↔W25Q128)',SPIM,S[2])]
    def col(n):
        for _,g,c in grupos:
            if n in g: return c
        return '#d6d4ce'
    fig,ax=plt.subplots(1,2,figsize=(12,6.2))
    for a,capa in zip(ax,('F.Cu','B.Cu')):
        for s in SEG:
            if s['layer']!=capa: continue
            c=col(s['net']); z=3 if c!='#d6d4ce' else 1
            a.plot([s['x1'],s['x2']],[s['y1'],s['y2']],color=c,lw=1.6 if z==3 else 0.8,solid_capstyle='round',zorder=z)
        for r in ('U1','U7','J1','R24'):
            f=FD[r]; a.text(f['x'],f['y'],r,fontsize=9,ha='center',va='center',zorder=5,clip_on=True,bbox=dict(fc=SURF,ec='none',alpha=0.7,pad=0.5))
        a.set_xlim(100,150); a.set_ylim(106,45); a.set_aspect('equal'); a.set_title(f'{capa} (zona BT817)'); a.set_xlabel('x (mm)'); a.set_ylabel('y (mm)')
    ax[1].legend(handles=[Line2D([0],[0],color=c,lw=2,label=l) for l,_,c in grupos],fontsize=8,loc='lower right')
    plt.tight_layout(); plt.savefig(FIG/'fig1_layout_bt817.png',dpi=150); plt.close()
def fig_caida5v():
    from pdn_5v import build, solve, CARGAS
    coords,edges,pn=build(T=25); V=solve(coords,edges,[pn['J10.A4'],pn['J10.A9']],{pn[k]:v for k,v in CARGAS['presupuesto_1A'].items()})
    fig,ax=plt.subplots(figsize=(12,5.2))
    for s in SEG:
        if s['layer']=='F.Cu' and s['net']!='+5V': ax.plot([s['x1'],s['x2']],[s['y1'],s['y2']],color='#e4e3df',lw=0.6,zorder=1)
    cmap=mpl.colors.LinearSegmentedColormap.from_list('azul',['#cde2fb','#86b6ef','#3987e5','#1c5cab','#0d366b']); vmax=70
    xy=np.array(coords)
    for a,b,R,w,l in edges:
        d=-(V[a]+V[b])/2*1e3; ax.plot([xy[a,0],xy[b,0]],[xy[a,1],xy[b,1]],color=cmap(min(d/vmax,1)),lw=3.0,solid_capstyle='round',zorder=3)
    lab={'J10.A9':('J10 (USB-C)',(4,6)),'C40.1':('C40',(4,-6)),'U6.3':('U6 LMR51430',(-30,-6)),'L2.1':('L2/U8 DIO5661',(4,-8)),'U4.6':('U4 PAM8302A',(-6,-9))}
    for k,(t,o) in lab.items():
        x,y=xy[pn[k]]; d=abs(V[pn[k]])*1e3
        ax.annotate(f"{t}\n−{d:.0f} mV" if d>=0.5 else f"{t}\nreferencia",(x,y),xytext=(x+o[0],y+o[1]),fontsize=8.5,arrowprops=dict(arrowstyle='-',color=T2,lw=0.8),zorder=6)
    sm=mpl.cm.ScalarMappable(cmap=cmap,norm=mpl.colors.Normalize(0,vmax)); cb=plt.colorbar(sm,ax=ax,fraction=0.025,pad=0.01); cb.set_label('caída desde J10 (mV)')
    ax.set_xlim(40,232); ax.set_ylim(128,75); ax.set_aspect('equal'); ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')
    ax.set_title('Red +5V (solo F.Cu, sin vías): caída con el presupuesto de 1 A, 25 °C')
    plt.tight_layout(); plt.savefig(FIG/'fig2_caida_5v.png',dpi=150); plt.close()
def fig_montecarlo():
    from mc_tolerancias import H, fc
    rng=np.random.default_rng(1); g=lambda nom,rel,n: nom*(1+rng.normal(0,rel/3,n)); N=200000
    vout=g(0.6,0.01,N)*(1+g(100e3,0.01,N)/g(22e3,0.01,N)); iled=g(0.2,0.04,N)/g(3.3,0.01,N)*1e3
    n=60000; R4=g(3.3e3,0.01,n); R3=g(1e3,0.01,n); C10=g(4.7e-9,0.1,n); C29=g(4.7e-9,0.1,n)
    fc10=fc(R4,C10,R3,C29,np.full(n,10e3))/1e3; fcinf=fc(R4,C10,R3,C29,np.full(n,1e12))/1e3
    fig,ax=plt.subplots(2,2,figsize=(12,7.6))
    def hist(a,x,c,lab,b=80): a.hist(x,bins=b,color=c,alpha=0.9,label=lab,edgecolor=SURF,linewidth=0.3)
    hist(ax[0,0],vout,S[0],'MC')
    for v in (3.2405,3.4162): ax[0,0].axvline(v,color=T2,ls=':',lw=1.2)
    y=ax[0,0].get_ylim()[1]*0.9
    ax[0,0].text(3.2405,y,' peor caso\n 3,241 V',fontsize=8,color=T2); ax[0,0].text(3.4162,y,'peor caso \n3,416 V ',fontsize=8,color=T2,ha='right')
    ax[0,0].set_title('LMR51430: V_OUT (R20/R21 1 %, VFB 0,6 V ±1 %)'); ax[0,0].set_xlabel('V_OUT (V)'); ax[0,0].set_yticks([])
    hist(ax[0,1],iled,S[1],'VFB ±4 %'); ax[0,1].set_title('DIO5661: I_LED = VFB/R22 (VFB ±4 % supuesto, R22 1 %)'); ax[0,1].set_xlabel('I_LED (mA)'); ax[0,1].set_yticks([])
    hist(ax[1,0],fcinf,S[2],'sin carga (Ri→∞)',60); hist(ax[1,0],fc10,S[6],'con entrada PAM8302A, Ri≈10 kΩ',60)
    ax[1,0].axvline(10.26,color=T2,ls=':',lw=1.2); ax[1,0].text(10.15,ax[1,0].get_ylim()[1]*0.85,'1/(2π·R4·C10)\n= 10,26 kHz',fontsize=8,color=T2,ha='right')
    ax[1,0].set_title('Filtro RC-RC de audio: f(−3 dB) respecto a 1 kHz'); ax[1,0].set_xlabel('f −3 dB (kHz)'); ax[1,0].set_yticks([])
    ax[1,0].legend(fontsize=8,loc='center',bbox_to_anchor=(0.62,0.55))
    f=np.logspace(1,6.3,400)
    for Ri,c,lab in ((1e12,S[2],'Ri→∞'),(10e3,S[6],'Ri≈10 kΩ')):
        ax[1,1].semilogx(f,20*np.log10(np.abs(H(f,3.3e3,4.7e-9,1e3,4.7e-9,Ri))),color=c,label=f'nominal, {lab}')
        m=400; a=g(3.3e3,0.01,m); b=g(1e3,0.01,m); c1=g(4.7e-9,0.1,m); c2=g(4.7e-9,0.1,m)
        Hs=np.array([20*np.log10(np.abs(H(f,a[i],c1[i],b[i],c2[i],Ri))) for i in range(m)])
        ax[1,1].fill_between(f,Hs.min(0),Hs.max(0),color=c,alpha=0.18,linewidth=0)
    ax[1,1].set_ylim(-70,3); ax[1,1].set_xlabel('frecuencia (Hz)'); ax[1,1].set_ylabel('|H| hasta la entrada del amplificador (dB)')
    ax[1,1].set_title('Respuesta del filtro (banda: 400 muestras MC)'); ax[1,1].legend(fontsize=8,loc='lower left')
    plt.tight_layout(); plt.savefig(FIG/'fig3_montecarlo.png',dpi=150); plt.close()
def fig_hotplug():
    W=json.load(open(TMP/'hotplug_ondas.json'))
    fig,ax=plt.subplots(1,2,figsize=(12,4.4))
    ser=[('nominal_5V25_AWG20_1m','5,25 V · AWG20 1 m · nominal (L′ 0,75 µH/m, C40 100 µF)'),
         ('peor_5V5_AWG20_1m','5,5 V · AWG20 1 m · peor caso (L′ 1,25 µH/m, C40 80 µF)'),
         ('sinC40_5V5_AWG20_1m','5,5 V · AWG20 1 m · sin C40 (solo cerámicos)'),
         ('mitigado_150m_5V5_AWG20_1m','5,5 V · AWG20 1 m · peor caso con 150 mΩ en la rama de C40'),
         ('peor_5V5_AWG28_1m','5,5 V · AWG28 1 m · peor caso')]
    for i,(k,lab) in enumerate(ser):
        w=W[k]['wave']; ax[0].plot((np.array(w['t'])-2e-6)*1e6,w['J10'],color=S[i],label=lab)
    ax[0].axhline(6.0,color=CRIT,lw=1.5,ls='--'); ax[0].text(178,6.08,'Límite 6,0 V (DIO5661, PAM8302A)',color=CRIT,fontsize=9,ha='right')
    ax[0].set_xlim(-5,180); ax[0].set_ylim(0,8.0); ax[0].set_xlabel('tiempo tras el contacto (µs)'); ax[0].set_ylabel('V(J10 VBUS) (V)')
    ax[0].set_title('Hot-plug: tensión en J10 (fuente rígida)'); ax[0].legend(fontsize=7.5,loc='lower right')
    for i,(cab,lab) in enumerate((('AWG20_0.3','AWG20 0,3 m'),('AWG20_1.0','AWG20 1 m'),('AWG28_0.3','AWG28 0,3 m'),('AWG28_1.0','AWG28 1 m'))):
        w=W[f'puertoA_{cab}m']['wave']; I=np.array(w['I'])
        ax[1].plot((np.array(w['t'])-2e-6)*1e6,I,color=S[i],label=f'{lab}  (pico {I.max():.0f} A)')
    ax[1].set_xlim(-2,60); ax[1].set_xlabel('tiempo tras el contacto (µs)'); ax[1].set_ylabel('corriente VBUS (A)')
    ax[1].set_title('Corriente de entrada desde un puerto USB-A de 5,0 V'); ax[1].legend(fontsize=8)
    plt.tight_layout(); plt.savefig(FIG/'fig4_hotplug.png',dpi=150); plt.close()
def fig_termico():
    TT=np.load(TMP/'termico_mapa_carcasa_40C.npy'); R=json.load(open(RES/'termico.json')); m=R['malla']; h=m['h']
    fig,ax=plt.subplots(figsize=(12,5.6))
    cmap=mpl.colors.LinearSegmentedColormap.from_list('naranja',['#fde3d6','#f5a47e','#eb6834','#b8441a','#7a2a0e'])
    im=ax.imshow(TT.T,extent=[m['xc0']-h/2,m['xc1']+h/2,m['yc1']+h/2,m['yc0']-h/2],cmap=cmap,vmin=40,vmax=np.nanmax(TT))
    cb=plt.colorbar(im,ax=ax,fraction=0.025,pad=0.01); cb.set_label('T de placa (°C)')
    TR=R['carcasa_40C_nom']
    for ref,t in (('U6','U6 LMR51430'),('U8','U8 DIO5661'),('U1','U1 BT817')):
        f=FD[ref]; ax.annotate(f"{t}\nTj≈{TR[ref]['Tj']:.0f} °C",(f['x'],f['y']),xytext=(f['x']+6,f['y']-12),fontsize=8.5,arrowprops=dict(arrowstyle='-',color=T1,lw=0.8))
    f=FD['U4']; ax.annotate('U4 PAM8302A',(f['x'],f['y']),xytext=(f['x']+4,f['y']-10),fontsize=8.5,arrowprops=dict(arrowstyle='-',color=T1,lw=0.8))
    ax.set_title('Temperatura de placa estimada en carcasa (h = 8 W/m²K, Ta = 40 °C), pérdidas nominales')
    ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)'); ax.grid(False)
    plt.tight_layout(); plt.savefig(FIG/'fig5_termico.png',dpi=150); plt.close()
if __name__=='__main__':
    fig_layout(); fig_caida5v(); fig_montecarlo(); fig_termico()
    if (TMP/'hotplug_ondas.json').exists(): fig_hotplug()
    print('figuras en',FIG)
