# Pin 1 y polaridad para comparar con la vista 3D de JLCPCB

Generado por `scripts/pin1_table.py`. Vista superior (como la muestra JLC), Y hacia abajo como en KiCad: «arriba» = hacia el borde superior de la placa (lado de la muesca de la antena).
Rotacion = la que va en el CPL (`ocx-cpl-jlcpcb.csv`). Dibujo de cada huella en [`pin1-polaridad.png`](pin1-polaridad.png): pad de referencia en rojo, nets en los pads clave.

| Ref | Valor | LCSC | Huella | Rot. CPL | Centro CPL (mm) | Pad ref. | Pad ref. respecto al centro | Nets (pad ref. / otros) | Que comprobar en el 3D | Riesgo si esta girado |
|---|---|---|---|---|---|---|---|---|---|---|
| U1 | BT817Q | C20613585 | VQFN-64-1EP_9x9mm_P0.5mm_EP5.4x5.4mm_ThermalVias | 180 | 120.3000mm, -63.3000mm | 1 | abajo-derecha (dx=+4.44, dy=+3.75) | **1:B7** / 64 pads | Punto de pin 1 del VQFN-64 sobre el pad marcado. EP centrado. | Un giro de 90/180 deja el BT817 inservible. |
| U2 | USBLC6-2SC6 | C7519 | SOT-23-6 | 270 | 207.9800mm, -113.0500mm | 1 | arriba-derecha (dx=+0.95, dy=-1.14) | **1:USB_C_D+** / 2:GND, 3:USB_C_D-, 4:USB_C_D-, 5:+5V, 6:USB_C_D+ | Punto de pin 1 del SOT-23-6. Pin 2 = GND, pin 5 = VBUS. | Girado 180 grados intercambia GND (2) y +5V (5): cortocircuito a traves de los diodos. |
| U5 | MCP23017x-x-SO | C47023 | SOIC-28W_7.5x17.9mm_P1.27mm | 270 | 154.6950mm, -94.7500mm | 1 | arriba-derecha (dx=+8.25, dy=-4.65) | **1:Net-(U5-GPB0)** / 27 pads | Muesca/punto del SOIC-28 en el extremo del pad 1. |  |
| U6 | LMR51430 | C5210749 | SOT-23-6 | 90 | 192.5800mm, -107.0500mm | 1 | abajo-izquierda (dx=-0.95, dy=+1.14) | **1:GND** / 2:BUCK_SW, 3:+5V, 4:Net-(U6-FB), 5:+5V, 6:BUCK_CB | Punto de pin 1 del SOT-23-6 (DDC). 1 = GND, 2 = SW, 3 = VIN, 4 = FB, 5 = EN, 6 = CB. | Girado 180 grados: VIN<->CB y GND<->FB; el regulador no arranca o se destruye. |
| U7 | W25Q128JVS | C97521 | SOIC-8_5.3x5.3mm_P1.27mm | 0 | 135.5000mm, -56.5000mm | 1 | arriba-izquierda (dx=-3.59, dy=-1.91) | **1:SPIM_SS_N** / 7 pads | Punto/bisel del SOIC-8 208 mil en el pad 1 (/CS). |  |
| U8 | DIO5661ST6 | C324576 | SOT-23-6 | 180 | 86.3420mm, -83.1520mm | 1 | abajo-derecha (dx=+1.14, dy=+0.95) | **1:BL_LX** / 2:GND, 3:VLED-, 4:BACKLIGHT, 5:unconnected-(U8-Pad5), 6:+5V | Punto de pin 1 del SOT-23-6. 1 = LX, 2 = GND, 6 = VIN (+5V). | Girado 180 grados pone +5V en el LX y GND en el pad 5. |
| D1 | P6SMB6.8CA | C78395 | D_SMB_Handsoldering | 90 | 203.4000mm, -113.0000mm | 1 | abajo (dx=+0.00, dy=+2.70) | **1:+5V** / 2:GND | TVS bidireccional (CA): sin polaridad. Basta con que asiente en los dos pads. |  |
| D2 | GREEN | C2297 | LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder | 0 | 229.9000mm, -113.3000mm | 1 | izquierda (dx=-1.03, dy=+0.00) | **1:Net-(D2-K)** / 2:+3.3V | LED: pad 1 = CATODO (K). La marca verde/T del encapsulado debe ir al pad 1. |  |
| D3 | SS210 | C14996 | D_SMA_Handsoldering | 180 | 93.8375mm, -85.8000mm | 1 | derecha (dx=+2.50, dy=+0.00) | **1:VLED+** / 2:BL_LX | Schottky SMA: pad 1 = CATODO (K). La banda debe quedar sobre el pad 1. | Al reves conduce en directa la salida a la entrada. |
| Y1 | 12MHz 20 pF | C112588 | Crystal_SMD_5032-4Pin_5.0x3.2mm | 90 | 121.5700mm, -52.1800mm | 1 | abajo-derecha (dx=+1.00, dy=+1.65) | **1:Net-(U1-X1{slash}CLK)** / 2:GND, 3:Net-(U1-X2), 4:GND | Cristal 5032 4 pines: 1 y 3 = cristal, 2 y 4 = GND. Bisel/punto en el pad 1. | Un giro de 180 es inocuo (1<->3, 2<->4); uno de 90 pone el cristal a GND. |
| J1 | J_LCD | C225713 | Omron_XF2M-4015-1A_1x40-1MP_P0.5mm_Horizontal | 0 | 108.7400mm, -103.2000mm | 1 | arriba-izquierda (dx=-9.75, dy=-2.05) | **1:VLED-** / 40 pads | FPC 40 p (XF2M-4015-1A): pad 1 coincide con el pin 1 del LCD; boca hacia el cable. |  |
| J4 | CTP | C408826 | TE_84953-6_1x06-1MP_P1.0mm_Horizontal | 0 | 134.0000mm, -101.1500mm | 1 | arriba-izquierda (dx=-2.50, dy=-1.80) | **1:+3.3V** / 2:GND, 3:CTP_SCL, 4:CTP_SDA, 5:CTP_INT_N, 6:CTP_RST_N, MP:NC | FPC 6 p (84953-6): pad 1 coincide con el pin 1 del panel tactil; boca hacia el cable. |  |
| J10 | USB_C_Receptacle_USB2.0_16P | C165948 | USB_C_Receptacle_HRO_TYPE-C-31-M-12 | 0 | 208.4800mm, -126.2500mm | A1 | arriba-izquierda (dx=-3.25, dy=-4.05) | **A1:GND** / 16 pads | USB-C: boca del conector hacia el borde de la placa; patillas de carcasa en sus ranuras. |  |
| L2 | 22uH | C167883 | L_Sunlord_SWPA4030S | 0 | 85.5375mm, -87.4000mm | 1 | izquierda (dx=-1.50, dy=+0.00) | **1:+5V** / 2:BL_LX | Inductancia sin polaridad electrica; el punto (inicio de devanado) va al pad 1. |  |
| L3 | 2.2uH | C3151182 | L_Coilcraft_XxL4020 | 270 | 192.6800mm, -113.4500mm | 1 | arriba (dx=+0.00, dy=-1.19) | **1:BUCK_SW** / 2:+3.3V | Inductancia sin polaridad electrica; el punto (inicio de devanado) va al pad 1. |  |

Notas:
- JLC aplica su propia rotacion de libreria; si en su visor el punto de pin 1 del modelo 3D no cae en el pad indicado, corregir la rotacion en la web de JLC (o en el CPL) en multiplos de 90 grados, nunca la huella en KiCad.
- En diodos KiCad numera el catodo como pad 1 (D2, D3). D1 es bidireccional.
- J10: ademas del pin A1, comprobar que la boca del USB-C sobresale/enrasa con el borde inferior.
