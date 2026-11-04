## (a) Huellas con «FT Origin» = Center

Coordenadas en mm, sistema de KiCad. El CPL de kicad-cli escribe X igual y **Y con el signo cambiado** (Y hacia arriba); Fabrication Toolkit hace lo mismo y, como esta placa no tiene origen auxiliar (aux_axis_origin) definido, ambos usan el mismo origen absoluto.

| Ref | Huella | Rot | Ancla (CPL kicad-cli) X / Y_CPL | Centro de pads (FT) X / Y_CPL | ΔX / ΔY_CPL | |Δ| | Centro solo pads eléctricos X / Y_CPL | Centro F.Fab (cuerpo) X / Y_CPL |
|---|---|---:|---|---|---|---:|---|---|
| J2 | PinSocket_1x22_P2.54mm_Vertical | 0 | 144.600 / -24.140 | **144.600 / -50.810** | 0.000 / -26.670 | 26.670 | 144.600 / -50.810 | 144.600 / -50.810 |
| J3 | PinSocket_1x22_P2.54mm_Vertical | 180 | 167.460 / -77.480 | **167.460 / -50.810** | 0.000 / 26.670 | 26.670 | 167.460 / -50.810 | 167.460 / -50.810 |
| J5 | JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical | 90 | 65.639 / -111.456 | **65.639 / -110.456** | 0.000 / 1.000 | 1.000 | 65.639 / -110.456 | 65.984 / -110.661 |
| J10 | USB_C_Receptacle_HRO_TYPE-C-31-M-12 | 0 | 208.480 / -126.250 | **208.480 / -124.790** | 0.000 / 1.460 | 1.460 | 208.480 / -124.790 | 208.480 / -126.250 |
| SW1 | SW_PUSH_6mm | 180 | 40.500 / -30.000 | **37.250 / -27.750** | -3.250 / 2.250 | 3.953 | 37.250 / -27.750 | 37.250 / -27.750 |
| SW2 | SW_PUSH_6mm | 180 | 40.500 / -42.000 | **37.250 / -39.750** | -3.250 / 2.250 | 3.953 | 37.250 / -39.750 | 37.250 / -39.750 |
| SW3 | SW_PUSH_6mm | 180 | 50.500 / -52.000 | **47.250 / -49.750** | -3.250 / 2.250 | 3.953 | 47.250 / -49.750 | 47.250 / -49.750 |
| SW4 | SW_PUSH_6mm | 180 | 30.500 / -52.000 | **27.250 / -49.750** | -3.250 / 2.250 | 3.953 | 27.250 / -49.750 | 27.250 / -49.750 |
| SW5 | SW_PUSH_6mm | 180 | 40.500 / -62.000 | **37.250 / -59.750** | -3.250 / 2.250 | 3.953 | 37.250 / -59.750 | 37.250 / -59.750 |
| SW6 | SW_PUSH_6mm | 0 | 120.850 / -120.500 | **124.100 / -122.750** | 3.250 / -2.250 | 3.953 | 124.100 / -122.750 | 124.100 / -122.750 |
| SW7 | SW_PUSH_6mm | 0 | 130.900 / -120.500 | **134.150 / -122.750** | 3.250 / -2.250 | 3.953 | 134.150 / -122.750 | 134.150 / -122.750 |
| SW8 | SW_PUSH_6mm | 0 | 140.600 / -120.500 | **143.850 / -122.750** | 3.250 / -2.250 | 3.953 | 143.850 / -122.750 | 143.850 / -122.750 |
| SW9 | SW_PUSH_6mm | 0 | 150.550 / -120.500 | **153.800 / -122.750** | 3.250 / -2.250 | 3.953 | 153.800 / -122.750 | 153.800 / -122.750 |
| SW10 | SW_PUSH_6mm | 180 | 224.900 / -62.000 | **221.650 / -59.750** | -3.250 / 2.250 | 3.953 | 221.650 / -59.750 | 221.650 / -59.750 |
| SW11 | SW_PUSH_6mm | 180 | 234.900 / -52.000 | **231.650 / -49.750** | -3.250 / 2.250 | 3.953 | 231.650 / -49.750 | 231.650 / -49.750 |
| SW12 | SW_PUSH_6mm | 180 | 214.900 / -52.000 | **211.650 / -49.750** | -3.250 / 2.250 | 3.953 | 211.650 / -49.750 | 211.650 / -49.750 |
| SW13 | SW_PUSH_6mm | 180 | 224.900 / -42.000 | **221.650 / -39.750** | -3.250 / 2.250 | 3.953 | 221.650 / -39.750 | 221.650 / -39.750 |
| SW14 | SW_PUSH_6mm | 180 | 130.550 / -33.750 | **127.300 / -31.500** | -3.250 / 2.250 | 3.953 | 127.300 / -31.500 | 127.300 / -31.500 |
| SW15 | SW_PUSH_6mm | 180 | 224.900 / -30.000 | **221.650 / -27.750** | -3.250 / 2.250 | 3.953 | 221.650 / -27.750 | 221.650 / -27.750 |
| SW16 | SW_PUSH_6mm | 0 | 171.350 / -54.950 | **174.600 / -57.200** | 3.250 / -2.250 | 3.953 | 174.600 / -57.200 | 174.600 / -57.200 |

Huellas con FT Origin=Center en la placa: 20. Diferencias con la lista esperada: ninguna.

### Origen que usaría Fabrication Toolkit en el resto de huellas montadas

FT usa por defecto «Anchor» en SMD y «Center» en todo lo demás (THT o sin atributo); un campo vacío no cambia ese defecto.

| Ref | attr | FT Origin (campo) | Origen FT efectivo | |Δ| ancla→centro pads (mm) |
|---|---|---|---|---:|

## (b) Pin 1, polaridad y rotación

«Pin 1 en placa» = dónde queda el pad 1 respecto al centro de la pieza vista desde arriba, con la placa orientada como en KiCad (Y hacia abajo de la pantalla). Es lo que hay que ver en el visor de JLC: el marcador de pin 1 / polaridad del modelo debe caer en ese lado.

| Ref | Huella | Rot KiCad (CPL kicad-cli) | Pad 1 → red | Pin 1 en placa | Offset tabla FT | Rot FT (auto‑translate) |
|---|---|---:|---|---|---:|---:|
| U1 | VQFN-64-1EP_9x9mm_P0.5mm_EP5.4x5.4mm_ThermalVias | 180 (180) | B7 | abajo-derecha | +0 | 180 |
| U2 | SOT-23-6 | -90 (-90) | /Power_Supply_USB/USB_C_D+ | arriba-derecha | +180 (^SOT-23) | 90 |
| U5 | SOIC-28W_7.5x17.9mm_P1.27mm | -90 (-90) | Net-(U5-GPB0) | arriba-derecha | +270 (^SOIC-) | 180 |
| U6 | SOT-23-6 | 90 (90) | GND | abajo-izquierda | +180 (^SOT-23) | 270 |
| U7 | SOIC-8_5.3x5.3mm_P1.27mm | 0 (0) | SPIM_SS_N | arriba-izquierda | +270 (^SOIC-) | 270 |
| U8 | SOT-23-6 | 180 (180) | /Screen_Ctrl/BL_LX | abajo-derecha | +180 (^SOT-23) | 0 |
| D1 | D_SMB_Handsoldering | 90 (90) | +5V | abajo | +0 | 90 |
| D2 | LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder | 0 (0) | Net-(D2-K) | izquierda | +0 | 0 |
| D3 | D_SMA_Handsoldering | 180 (180) | /Screen_Ctrl/VLED+ | derecha | +0 | 180 |
| Y1 | Crystal_SMD_5032-4Pin_5.0x3.2mm | 90 (90) | Net-(U1-X1{slash}CLK) | abajo-derecha | +0 | 90 |
| C40 | CP_Elec_6.3x5.8 | 0 (0) | +5V | izquierda | +180 (^CP_Elec_) | 180 |
| J5 | JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical | 90 (90) | Net-(J5-Pin_1) | abajo | +0 | 90 |
| J2 | PinSocket_1x22_P2.54mm_Vertical | 0 (0) | +3.3V | arriba | +0 | 0 |
| J3 | PinSocket_1x22_P2.54mm_Vertical | 180 (180) | GND | abajo | +0 | 180 |

### Redes por pad

- **U1** (BT817Q, BT817Q-R): 1=B7, 16=SPIM_MOSI, 17=+3.3V, 32=CTP_SDA, 33=GND, 48=GND, 49=G0, 64=B6, 65=GND
- **U2** (USBLC6-2SC6, USBLC6-2SC6): 1=/Power_Supply_USB/USB_C_D+, 2=GND, 3=/Power_Supply_USB/USB_C_D-, 4=/Power_Supply_USB/USB_C_D-, 5=+5V, 6=/Power_Supply_USB/USB_C_D+
- **U5** (MCP23017x-x-SO, MCP23017-E/SO): 1=Net-(U5-GPB0), 2=Net-(U5-GPB1), 3=Net-(U5-GPB2), 4=Net-(U5-GPB3), 5=Net-(U5-GPB4), 6=Net-(U5-GPB5), 7=Net-(U5-GPB6), 8=unconnected-(U5-GPB7-Pad8), 9=+3.3V, 10=GND, 11=unconnected-(U5-NC-Pad11), 12=ESP_SCL, 13=ESP_SDA, 14=unconnected-(U5-NC-Pad14), 15=GND, 16=GND, 17=GND, 18=MCP_RESET, 19=unconnected-(U5-INTB-Pad19), 20=BTN_INT, 21=Net-(U5-GPA0), 22=Net-(U5-GPA1), 23=Net-(U5-GPA2), 24=Net-(U5-GPA3), 25=Net-(U5-GPA4), 26=Net-(U5-GPA5), 27=Net-(U5-GPA6), 28=unconnected-(U5-GPA7-Pad28)
- **U6** (LMR51430, LMR51430YDDCR): 1=GND, 2=/Power_Supply_USB/BUCK_SW, 3=+5V, 4=Net-(U6-FB), 5=+5V, 6=/Power_Supply_USB/BUCK_CB
- **U7** (W25Q128JVS, W25Q128JVSIQ): 1=SPIM_SS_N, 2=SPIM_MISO, 3=SPIM_IO2, 4=GND, 5=SPIM_MOSI, 6=SPIM_SCLK, 7=SPIM_IO3, 8=+3.3V
- **U8** (DIO5661ST6, DIO5661ST6): 1=/Screen_Ctrl/BL_LX, 2=GND, 3=/Screen_Ctrl/VLED-, 4=BACKLIGHT, 5=unconnected-(U8-Pad5), 6=+5V
- **D1** (P6SMB6.8CA, P6SMB6.8CA/TR13): 1=+5V, 2=GND
- **D2** (GREEN, KT-0805G): 1=Net-(D2-K), 2=+3.3V
- **D3** (SS210, SS210): 1=/Screen_Ctrl/VLED+, 2=/Screen_Ctrl/BL_LX
- **Y1** (12MHz 20 pF, X503212MSB4SI): 1=Net-(U1-X1{slash}CLK), 2=GND, 3=Net-(U1-X2), 4=GND
- **C40** (100 uF, MA16V100M6X6): 1=+5V, 2=GND
- **J5** (Audio_+_-, B2B-PH-K-S(LF)(SN)): 1=Net-(J5-Pin_1), 2=Net-(J5-Pin_2)
- **J2** (ESP32_S3_DEVKIT_LEFT), de arriba abajo en la placa: 1=+3.3V, 2=+3.3V, 3=Net-(J2-Pin_3), 4=/PD_N, 5=/INT_N, 6=JOY_L_X, 7=JOY_L_Y, 8=ESP_SCL, 9=ESP_SDA, 10=BTN_INT, 11=MCP_RESET, 12=JOY_L_BTN, 13=/GPIO3, 14=/GPIO46, 15=/GPIO1{slash}IO3, 16=/CS_N, 17=/MOSI, 18=/SCK, 19=/MISO, 20=/GPIO0{slash}IO2, 21=unconnected-(J2-Pin_21-Pad21), 22=GND
- **J3** (ESP32_S3_DEVKIT_RIGHT), de arriba abajo en la placa: 22=GND, 21=/U0TXD, 20=/U0RXD, 19=JOY_R_Y, 18=JOY_R_X, 17=/MTMS, 16=/MTDI, 15=/MTDO, 14=/MTCK, 13=/GPIO38, 12=/GPIO37, 11=/GPIO36, 10=/GPIO35, 9=/GPIO0, 8=/GPIO45, 7=/GPIO48, 6=JOY_R_BTN, 5=VOL_MODE, 4=USB_D+, 3=USB_D-, 2=GND, 1=GND

U1: 9 pads sin número; capas: [('F.Paste',)]. Pad 65 (EP): [('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 5.4, 5.4, ('F.Cu', 'F.Mask')), ('GND', 5.4, 5.4, ('B.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',)), ('GND', 0.63, 0.63, ('*.Cu',))]

## (c) DNP, BOM y CPL

- DNP en la PCB (attr dnp): J6, J7, TP1, TP10, TP11, TP12, TP2, TP3, TP4, TP5, TP6, TP7, TP8, TP9, U4
- DNP en el esquemático (BOM completa): J6, J7, TP1, TP10, TP11, TP12, TP2, TP3, TP4, TP5, TP6, TP7, TP8, TP9, U4
- DNP esperadas que aparecen en la BOM sin DNP: ninguna
- DNP esperadas que aparecen en el CPL (--exclude-dnp): ninguna
- DNP esperadas que NO están marcadas DNP en PCB: ninguna; en esquemático: ninguna
- DNP no esperadas: PCB ninguna, esquemático ninguna
- Refs en BOM y no en CPL: ninguna; en CPL y no en BOM: ninguna
- Huellas montadas en PCB que faltan en BOM: ninguna
- Nº de piezas montadas: BOM 104, CPL 104 (CPL con DNP: 119; diferencia = ['J6', 'J7', 'TP1', 'TP10', 'TP11', 'TP12', 'TP2', 'TP3', 'TP4', 'TP5', 'TP6', 'TP7', 'TP8', 'TP9', 'U4'])
- Filas de BOM montadas sin LCSC: ninguna; sin MPN: ninguna
- LCSC con formato distinto de C<número>: ninguno
- Mismo LCSC con distinto valor/huella/MPN: ninguno
- Mismo MPN con varios LCSC: ninguno
- LCSC/MPN distintos entre esquemático y PCB: ninguno
- Piezas THT en el CPL (19): J2, J3, J5, SW1, SW10, SW11, SW12, SW13, SW14, SW15, SW16, SW2, SW3, SW4, SW5, SW6, SW7, SW8, SW9
- Cara de las piezas del CPL: {'top': 104}
- Cabecera del CPL de kicad-cli: ['Ref', 'Val', 'Package', 'PosX', 'PosY', 'Rot', 'Side']

### Qué haría Fabrication Toolkit con las DNP

FT nunca pone una DNP en el CPL, pero **sí la mete en la BOM** salvo que se active «Exclude DNP components from BOM» (por defecto desactivado). El «LCSC Part #» que pondría:

| Ref | LCSC | MPN | «LCSC Part #» en BOM de FT |
|---|---|---|---|
| U4 | — | PAM8302AADCR | PAM8302AADCR |
| J6 | — | SFV5R-4STE1HLF | SFV5R-4STE1HLF |
| J7 | — | SFV5R-4STE1HLF | SFV5R-4STE1HLF |
| TP1 | — | — | (vacío) |
| TP2 | — | — | (vacío) |
| TP3 | — | — | (vacío) |
| TP4 | — | — | (vacío) |
| TP5 | — | — | (vacío) |
| TP6 | — | — | (vacío) |
| TP7 | — | — | (vacío) |
| TP8 | — | — | (vacío) |
| TP9 | — | — | (vacío) |
| TP10 | — | — | (vacío) |
| TP11 | — | — | (vacío) |
| TP12 | — | — | (vacío) |

## Geometría de fabricación (medida en la PCB)

- Pistas: 1002; anchos usados (mm: nº): {0.2: 671, 0.3: 124, 0.5: 163, 0.8: 44}
- Vías: 186; (diámetro, taladro): {(0.6, 0.3): 186}; anillo mínimo vía = 0.150 mm
- Tipos de vía: {'through': 186}
- Taladros en pads (tipo, Ø): {('np_thru_hole', 0.65): 2, ('np_thru_hole', 3.2): 6, ('thru_hole', '0.6x1.2'): 2, ('thru_hole', '0.6x1.7'): 2, ('thru_hole', 0.33): 25, ('thru_hole', 0.75): 2, ('thru_hole', 1.0): 45, ('thru_hole', 1.1): 64}
- Anillo PTH mínimo en pads: 0.150 mm (U1 pad 65); los 5 menores: [(0.15, 'U1', '65'), (0.15, 'U1', '65'), (0.15, 'U1', '65'), (0.15, 'U1', '65'), (0.15, 'U1', '65')]
- Ranuras (óvalos): [('J10', 'SH', 'thru_hole', 0.6, 1.7), ('J10', 'SH', 'thru_hole', 0.6, 1.2), ('J10', 'SH', 'thru_hole', 0.6, 1.7), ('J10', 'SH', 'thru_hole', 0.6, 1.2)]
- Edge.Cuts: 12 elementos; caja 16.00,14.50 → 244.00,129.90 = 228.00 × 115.40 mm
- Textos sueltos en serigrafía (texto, capa, alto, ancho, grosor, fuente): [('Jose Ramirez Giron', 'F.SilkS', 1.5, 1.5, None, 'Hemi Head 426'), ('ANTENA', 'F.SilkS', 1.5, 1.5, 0.3, 'Hemi Head 426'), ('OCX v1.0', 'F.SilkS', 5.0, 5.0, 0.5, 'Hemi Head 426')]
- Textos visibles de huellas en serigrafía: 116; menores (alto, grosor, ref, campo): [(1.0, 0.15, 'C1', 'Reference'), (1.0, 0.15, 'C10', 'Reference'), (1.0, 0.15, 'C12', 'Reference'), (1.0, 0.15, 'C13', 'Reference'), (1.0, 0.15, 'C14', 'Reference'), (1.0, 0.15, 'C15', 'Reference')]
- Stackup en la PCB: [('F.Mask', 0.01), ('F.Cu', 0.035), ('dielectric 1', 0.1), ('In1.Cu', 0.035), ('dielectric 2', 1.24), ('In2.Cu', 0.035), ('dielectric 3', 0.1), ('B.Cu', 0.035), ('B.Mask', 0.01)]; suma sin máscara = 1.5800 mm; acabado: None

## Ficheros generados

- `ocxPrototype-B_Cu.gbl` (20889 B)
- `ocxPrototype-B_Mask.gbs` (4543 B)
- `ocxPrototype-B_Paste.gbp` (493 B)
- `ocxPrototype-B_Silkscreen.gbo` (4553 B)
- `ocxPrototype-Edge_Cuts.gm1` (1233 B)
- `ocxPrototype-F_Cu.gtl` (67081 B)
- `ocxPrototype-F_Mask.gts` (18214 B)
- `ocxPrototype-F_Paste.gtp` (14588 B)
- `ocxPrototype-F_Silkscreen.gto` (246145 B)
- `ocxPrototype-In1_Cu.g1` (375508 B)
- `ocxPrototype-In2_Cu.g2` (376725 B)
- `ocxPrototype-NPTH-drl_map.gbr` (41354 B)
- `ocxPrototype-NPTH.drl` (501 B)
- `ocxPrototype-PTH-drl_map.gbr` (128552 B)
- `ocxPrototype-PTH.drl` (5312 B)
- `ocxPrototype-job.gbrjob` (3642 B)
- ocxPrototype-PTH.drl: unidades METRIC, herramientas [(0.3, 186), (0.33, 25), (0.6, 4), (0.75, 2), (1.0, 45), (1.1, 64)], ranuras G85: 4
- ocxPrototype-NPTH.drl: unidades METRIC, herramientas [(0.65, 2), (3.2, 6)], ranuras G85: 0

## Rellenos de zona del commit

Comparación del cobre exportado con --check-zones (rellena si hace falta) y sin él (rellenos tal cual están guardados en el commit). Se ignoran cabeceras/atributos.

- ocxPrototype-B_Cu.gbl: 0 líneas distintas, diferencia máxima de coordenada 0.0000 µm
- ocxPrototype-F_Cu.gtl: 0 líneas distintas, diferencia máxima de coordenada 0.0000 µm
- ocxPrototype-In1_Cu.g1: 23 líneas distintas, diferencia máxima de coordenada 0.0010 µm
- ocxPrototype-In2_Cu.g2: 1 líneas distintas, diferencia máxima de coordenada 0.0010 µm

