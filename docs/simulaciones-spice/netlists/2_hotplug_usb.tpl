* 2) Pico de tension al enchufar USB-C (hot-plug) en el rail +5V
* Variante: {name}
* Fuente: cargador con salida rigida a {vs} V (worst case USB 2.0 = 5.25 V), Rout = 20 mOhm
* Cable: {len} m, L = {lper} uH/m (bucle VBUS+GND), R = {rper} Ohm/m (bucle). Conector 2 x 15 mOhm
Vsrc vs 0 {vs}
Rsrc vs a 0.02
Csrc vs 0 470u
Sw a b ctl 0 SWP
.model SWP sw vt=0.5 vh=0.01 ron=1m roff=100meg
Vctl ctl 0 PWL(0 0 1u 0 1.001u 1)
Lcab b c {lcab}u
Rcab c d {rcab}
Rcon d vb 0.03
* Placa: pista J10 -> condensadores
Lpcb vb p5 10n
* Condensadores en +5V (ceramicos 0805 25V X5R derrateados a 5 V)
C15 p5 n15 7u
R15e n15 0 5m
C7 p5 n7 7u
R7e n7 0 5m
C20 p5 n20 7u
R20e n20 0 5m
C11 p5 n11 0.8u
R11e n11 0 10m
C8 p5 0 100n
C37 p5 0 100n
{tvs}
{fix}
.tran 1n 40u 0 1n uic
.control
run
wrdata {out} v(p5) i(Lcab)
quit
.endc
.end
