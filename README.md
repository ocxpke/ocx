# OCX handheld: main board

Main PCB of OCX, a PSP-style handheld console designed for my bachelor's thesis (TFG).

## What's on the board
- **MCU:** ESP32-S3-DevKitC-1 on two 1×22 sockets. Its antenna sits over a cutout in the board edge.
- **Display:** BT817Q (EVE4) graphics controller with a W25Q128JV flash and a 12 MHz crystal. It drives a 5" 800×480 RGB panel (NHD-5.0-800480AF-ASXP-CTP) through a 40-pin FPC, and its capacitive touch through a 6-pin FPC.
- **Backlight:** DIO5661 constant-current boost, ~60 mA at ~21 V.
- **Power:** USB-C, 5 V only, with USBLC6-2 ESD protection. An LMR51430 buck makes the 3.3 V rail.
- **Input:** MCP23017 I²C expander for 14 buttons, plus two analog joysticks on FPCs.
- **Audio:** PAM8302A class-D amplifier with a JST PH speaker connector.

## Board
| | |
|---|---|
| EDA | KiCad 10.0 (the files don't open in KiCad 9 or older) |
| Layers | 4: F.Cu signals / In1 GND / In2 3.3 V / B.Cu signals |
| Size | 228 × 115.4 mm, 1.6 mm thick |
| Fab | JLCPCB, JLC04161H-2116 stackup, ENIG |

## Opening the project
Install KiCad 10.0 and open `hardware/ocxPrototype.kicad_pro`.
All footprints and 3D models come from the standard KiCad libraries. The only custom symbol (BT817Q) is in `hardware/EVE_custom.kicad_sym`, registered in the project's `sym-lib-table`.

## License

Copyright © 2026 Jose Ramirez Giron

**Hardware** (everything in `hardware/`: schematics, PCB layout and symbol library) is licensed under the
[CERN Open Hardware Licence Version 2 – Strongly Reciprocal (CERN-OHL-S-2.0)](https://ohwr.org/cern_ohl_s_v2.txt).
See [`LICENSE`](LICENSE) for the full text.

You may use, study, modify, manufacture and sell this design or products based on it, as long as you:
- keep the copyright and licence notices,
- make the source of any modified version available under the same licence, and
- state clearly what you changed and when.

**Documentation and images** (`docs/`) are licensed under
[Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

"OCX" is the name of this project. Please don't use it for modified versions or present them as the original.

Datasheets of third-party components belong to their manufacturers and are not covered by these licences.
