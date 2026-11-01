* 5) Tiempo de subida I2C (drenador abierto) - Rp = {rp}, Cbus = {cb}
Vdd vdd 0 3.3
Rp vdd sda {rp}
Cb sda 0 {cb}
* transistor de salida: Ron 30 Ohm, se suelta en t = 2 us y vuelve a tirar en t = 12 us
Sdrv sda 0 ctl 0 SWD
.model SWD sw vt=0.5 vh=0.01 ron=30 roff=100meg
Vctl ctl 0 PWL(0 1 2u 1 2.001u 0 12u 0 12.001u 1)
.tran 1n 20u 0 1n
.control
run
wrdata {out} v(sda)
quit
.endc
.end
