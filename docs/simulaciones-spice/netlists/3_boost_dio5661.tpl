* 3) DIO5661ST6 (U8) - boost WLED en modo corriente, modelo conductual generico (NO oficial de Dioo)
* Variante: {name}
* BOM: L2 = 22uH FNR4030S220MT, D3 = SS210, C21 = 2.2uF 50V 1206 X7R, C20 = 10uF 25V 0805, R22 = 3.3 Ohm 1 %
* Supuestos: fsw = 1.1 MHz, VFB = 0.2 V, ILIM = 1.3 A, OVP = 37 V con histeresis 2 V
.param fsw=1.1meg Tsw={{1/fsw}} Kc=1 Se=0.5meg Ilim=1.3 vfb=0.2 gm=50u Rc=80k Cc=1n
Vin vin 0 5
C20 vin c20n 7u
Rc20 c20n 0 5m
L2 vin lxi 22u ic=0
Rdcr lxi lxs 0.25
Vsense lxs lx 0
Sm lx 0 g 0 SWM
.model SWM sw vt=0.5 vh=0.05 ron=0.4 roff=10meg
D3 lx vo SS210
.model SS210 d is=2e-6 n=1.3 rs=0.06 cjo=150p bv=100
C21 vo c21n {cout}
Rc21 c21n 0 10m
{load}
R22 fb 0 3.3
* EN = BACKLIGHT a 3.3 V (100 %); referencia con arranque suave de 0.5 ms (supuesto)
Vsaw saw 0 PULSE(0 1 0 {{Tsw-2n}} 1n 0.5n {{Tsw}})
Bref ref 0 V = {{vfb}}*min(1, max(0, (time-20u)/0.5m))
Gea 0 comp cur = {{gm}}*(V(ref)-V(fb))
Rcz comp czn {{Rc}}
Ccz czn 0 {{Cc}}
Dclh comp vclh DCL
Vclh vclh 0 2.4
Dcll vcll comp DCL
Vcll vcll 0 0.2
.model DCL d is=1e-12 n=0.1
* OVP con histeresis (memoria en nodo ov)
Bovx ovx 0 V = V(vo) > 37 ? 1 : (V(vo) < 35 ? 0 : (V(ov) > 0.5 ? 1 : 0))
Rov ovx ov 1k
Cov ov 0 1p
Bset set 0 V = (V(saw) < 0.02 && V(ov) < 0.5 && V(comp) > 0.55) ? 1 : 0
Breset rst 0 V = (V(saw) > 0.07 && (i(Vsense) > min({{Ilim}}, {{Kc}}*(V(comp)-0.5)) - {{Se}}*V(saw)*{{Tsw}} || V(saw) > 0.92)) ? 1 : 0
Bq qx 0 V = V(set) > 0.5 ? 1 : (V(rst) > 0.5 ? 0 : (V(q) > 0.5 ? 1 : 0))
Rq qx q 1k
Cq q 0 1p
Bg g 0 V = V(q) > 0.5 ? 1 : 0
.options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-5 itl4=100
.tran 5n {tstop} 0 5n uic
.control
run
linearize v(vo) v(fb) i(Vsense) v(lx) v(comp)
wrdata {out} v(vo) v(fb) i(Vsense) v(lx) v(comp)
quit
.endc
.end
