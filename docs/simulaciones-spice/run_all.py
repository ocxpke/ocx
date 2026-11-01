#!/usr/bin/env python3
"""Lanza todas las simulaciones ngspice de OCX y genera las graficas PNG y resultados.json.

Uso:  python3 run_all.py [directorio_de_trabajo]
Necesita ngspice (probado con ngspice-42), numpy y matplotlib.
Los ficheros de datos brutos (cientos de MB) van al directorio de trabajo, no al repo.
"""
import json
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.join(HERE, "netlists")
PNG = os.path.join(HERE, "graficas")
WORK = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="ocx_spice_")
os.makedirs(WORK, exist_ok=True)
os.makedirs(PNG, exist_ok=True)

# Paleta categorica de referencia (orden fijo) + tinta y limites
S = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
INK, INK2, GRID, LIMIT = "#0b0b0b", "#52514e", "#e4e3df", "#c62828"
plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.6, "font.size": 10, "legend.frameon": False,
    "axes.titleweight": "bold", "axes.titlesize": 11,
})
R = {}


def ngspice(cir_text, name):
    path = os.path.join(WORK, name + ".cir")
    with open(path, "w") as f:
        f.write(cir_text)
    subprocess.run(["ngspice", "-b", path], cwd=WORK, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load(path, ncols):
    d = np.loadtxt(path)
    t = d[:, 0]
    return t, [d[:, 2 * i + 1] for i in range(ncols)]


def limit(ax, y, text, color=LIMIT, va="bottom"):
    ax.axhline(y, color=color, lw=1.0, ls="--")
    ax.annotate(text, xy=(1, y), xycoords=("axes fraction", "data"), ha="right", va=va,
                color=color, fontsize=8.5, xytext=(-2, 2 if va == "bottom" else -2),
                textcoords="offset points")


# ------------------------------------------------------------------ 1) buck
def sim_buck():
    src = open(os.path.join(NET, "1_buck_lmr51430.cir")).read()
    out = os.path.join(WORK, "buck.dat")
    ngspice(src, "buck")
    t, (v, il, comp, vin) = load(out, 4)
    w = lambda a, b: (t >= a) & (t < b)
    vnom = 0.6 * (1 + 100 / 22)
    i10, i90 = np.argmax(v > 0.1 * vnom), np.argmax(v > 0.9 * vnom)
    m50, m500, mup, mdn = w(5.5e-3, 6e-3), w(7.0e-3, 7.5e-3), w(6e-3, 7.5e-3), w(7.5e-3, 8.5e-3)
    r = dict(vnom=vnom, vout_50=v[m50].mean(), vout_500=v[m500].mean(),
             t_arranque_10_90_ms=(t[i90] - t[i10]) * 1e3, t_90_ms=t[i90] * 1e3,
             sobreimpulso_arranque_mV=(v[t < 5e-3].max() - vnom) * 1e3,
             il_max_arranque_A=il[t < 5e-3].max(),
             rizado_50mA_mVpp=np.ptp(v[m50]) * 1e3, rizado_500mA_mVpp=np.ptp(v[m500]) * 1e3,
             il_pico_50mA=il[m50].max(), il_pico_500mA=il[m500].max(),
             caida_escalon_mV=(v[mup].min() - v[m50].mean()) * 1e3,
             subida_liberacion_mV=(v[mdn].max() - v[m500].mean()) * 1e3)
    mrec = w(6e-3, 7.5e-3)
    band = np.abs(v[mrec] - v[m500].mean()) > 0.01
    r["recuperacion_1pct_us"] = (t[mrec][band][-1] - 6e-3) * 1e6 if band.any() else 0
    R["buck"] = r

    fig, axs = plt.subplots(2, 2, figsize=(11, 7))
    ax = axs[0, 0]
    m = t < 3e-3
    ax.plot(t[m] * 1e3, v[m], color=S[0], label="V(3V3)")
    ax.plot(t[m] * 1e3, vin[m], color=S[1], label="VIN (+5V)")
    ax.set(title="Arranque (arranque suave interno, carga 50 mA)", xlabel="t (ms)", ylabel="V")
    ax.legend(loc="center right")
    ax = axs[0, 1]
    m = w(5.95e-3, 6.15e-3)
    ax.plot(t[m] * 1e6 - 6000, v[m], color=S[0], lw=1.2)
    limit(ax, vnom * 0.97, "-3 %", va="bottom")
    ax.set_ylim(vnom * 0.965, vnom * 1.005)
    ax.set(title="Escalon 50 -> 500 mA (1 A/us)", xlabel="t - 6 ms (us)", ylabel="V(3V3) (V)")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(t[m] * 1e6 - 6000, il[m], color=S[2], lw=0.6, alpha=0.6)
    ax2.set_ylabel("I(L3) (A)", color=S[2]); ax2.tick_params(colors=S[2])
    ax = axs[1, 0]
    m = w(5.98e-3, 6.0e-3)
    ax.plot(t[m] * 1e6 - 5980, (v[m] - v[m].mean()) * 1e3, color=S[0])
    ax.set(title="Rizado a 50 mA (modo PFM, salto de pulsos)", xlabel="t (us)", ylabel="V(3V3) - media (mV)")
    ax = axs[1, 1]
    m = w(7.48e-3, 7.485e-3)
    ax.plot(t[m] * 1e6 - 7480, (v[m] - v[m].mean()) * 1e3, color=S[0])
    ax.set(title="Rizado a 500 mA (PWM 1,1 MHz)", xlabel="t (us)", ylabel="V(3V3) - media (mV)")
    fig.tight_layout()
    fig.savefig(os.path.join(PNG, "1_buck_lmr51430.png"), dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ 2) hot-plug
def sim_hotplug():
    tpl = open(os.path.join(NET, "2_hotplug_usb.tpl")).read()
    tvs = {
        "sin": "",
        "P6SMB6.8CA tip.": "Dtvs 0 p5 TVS\n.model TVS d is=1e-12 n=1 bv=6.8 ibv=10m rs=0.065 cjo=2n",
        "P6SMB6.8CA min.": "Dtvs 0 p5 TVS\n.model TVS d is=1e-12 n=1 bv=6.45 ibv=10m rs=0.065 cjo=2n",
    }
    fixes = {
        "": "",
        "+47uF/0.47R": "Cdamp p5 nd 47u\nRdamp nd 0 0.47",
        "+100uF ESR 0.3": "Cdamp p5 nd 100u\nRdamp nd 0 0.3",
    }
    res = []
    curves = {}
    for vs in (5.0, 5.25):
        for length in (0.3, 1.0):
            for rper, rname in ((0.067, "AWG20"), (0.43, "AWG28")):
                for tk, tv in tvs.items():
                    for fk, fv in fixes.items():
                        if fk and tk == "P6SMB6.8CA min.":
                            continue
                        name = f"hp_{vs}_{length}_{rname}_{len(res)}"
                        out = os.path.join(WORK, name + ".dat")
                        txt = tpl.format(name=name, vs=vs, len=length, lper=1.0, rper=rper,
                                         lcab=1.0 * length, rcab=round(rper * length, 4),
                                         tvs=tv, fix=fv, out=out)
                        ngspice(txt, name)
                        t, (v, i) = load(out, 2)
                        row = dict(vs=vs, cable_m=length, cable=rname, tvs=tk, cambio=fk or "ninguno",
                                   vpico=float(v.max()), ipico=float(i.max()))
                        res.append(row)
                        curves[(vs, length, rname, tk, fk)] = (t, v)
    R["hotplug"] = res
    sweep = []
    for esr in (0.05, 0.15, 0.3, 0.6, 1.0, 2.0):
        for length in (0.3, 1.0):
            name = f"hpesr_{esr}_{length}"
            out = os.path.join(WORK, name + ".dat")
            txt = tpl.format(name=name, vs=5.25, len=length, lper=1.0, rper=0.067, lcab=length,
                             rcab=round(0.067 * length, 4), tvs=tvs["P6SMB6.8CA tip."],
                             fix=f"Cdamp p5 nd 100u\nRdamp nd 0 {esr}", out=out)
            ngspice(txt, name)
            t, (v, i) = load(out, 2)
            sweep.append(dict(esr=esr, cable_m=length, vpico=float(v.max())))
    R["hotplug_barrido_esr_100uF"] = sweep

    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for ax, (length, rn, title) in zip(axs, ((0.3, "AWG20", "Cable 0,3 m (AWG20)"),
                                             (1.0, "AWG20", "Cable 1 m (AWG20)"),
                                             (1.0, "AWG28", "Cable 1 m (AWG28, fino)"))):
        for k, (tk, fk, lab) in enumerate((("sin", "", "sin TVS"),
                                           ("P6SMB6.8CA tip.", "", "con D1 (P6SMB6.8CA)"),
                                           ("P6SMB6.8CA tip.", "+47uF/0.47R", "D1 + 47 uF con 0,47 ohm serie"),
                                           ("P6SMB6.8CA tip.", "+100uF ESR 0.3", "D1 + 100 uF (ESR 0,3 ohm)"))):
            t, v = curves[(5.25, length, rn, tk, fk)]
            ax.plot(t * 1e6, v, color=S[k], label=lab, lw=1.4)
        limit(ax, 6.0, "6,0 V abs. max PAM8302A / DIO5661")
        ax.set(title=title, xlabel="t (us)", xlim=(0, 25))
    axs[0].set_ylabel("V(+5V) en placa (V), fuente 5,25 V")
    axs[0].legend(loc="lower right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG, "2_hotplug_usb.png"), dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ 3) boost
def sim_boost():
    tpl = open(os.path.join(NET, "3_boost_dio5661.tpl")).read()
    cases = {
        "60mA": dict(cout="1.2u", tstop="2.5m",
                     load="Dled vo fb LED\n.model LED d is=5.6e-27 n=14 rs=2.3"),
        "sin_carga": dict(cout="0.8u", tstop="2.5m", load="Rleak vo fb 100meg"),
    }
    data = {}
    for k, c in cases.items():
        out = os.path.join(WORK, f"boost_{k}.dat")
        ngspice(tpl.format(name=k, out=out, **c), "boost_" + k)
        t, (vo, fb, il, lx, comp) = load(out, 5)
        data[k] = (t, vo, fb, il, lx, comp)
    t, vo, fb, il, lx, comp = data["60mA"]
    m = t > 2.0e-3
    iled = fb / 3.3
    R["boost_60mA"] = dict(iled_mA=iled[m].mean() * 1e3, iled_rizado_mApp=np.ptp(iled[m]) * 1e3,
                           vo=vo[m].mean(), vo_rizado_mVpp=np.ptp(vo[m]) * 1e3,
                           il_pico=il[m].max(), il_min=il[m].min(), il_max_total=il.max(),
                           vo_max=vo.max(), p_r22_mW=(fb[m] ** 2).mean() / 3.3 * 1e3)
    t2, vo2, fb2, il2, lx2, comp2 = data["sin_carga"]
    m2 = t2 > 1.0e-3
    R["boost_sin_carga"] = dict(vo_max=vo2.max(), vo_min_regimen=vo2[m2].min(), vlx_max=lx2.max(),
                                il_max=il2.max(), vo_media=vo2[m2].mean())

    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
    ax = axs[0]
    ax.plot(t * 1e3, iled * 1e3, color=S[0], lw=1.0)
    ax.axhline(0.2 / 3.3 * 1e3, color=INK2, lw=1, ls=":")
    ax.set(title="I(LED) = V(FB)/R22, R22 = 3,3 ohm", xlabel="t (ms)", ylabel="mA")
    ax = axs[1]
    m = (t > 2.4e-3) & (t < 2.41e-3)
    ax.plot((t[m] - 2.4e-3) * 1e6, il[m], color=S[2], label="I(L2)")
    ax.set(title="Regimen a 60 mA: corriente en L2", xlabel="t (us)", ylabel="A")
    ax3 = ax.twinx(); ax3.grid(False)
    ax3.plot((t[m] - 2.4e-3) * 1e6, vo[m], color=S[0], lw=1.0)
    ax3.set_ylabel("VLED+ (V)", color=S[0]); ax3.tick_params(colors=S[0])
    ax = axs[2]
    ax.plot(t2 * 1e3, vo2, color=S[1], label="VLED+ sin carga (LED abierto)")
    ax.plot(t * 1e3, vo, color=S[0], label="VLED+ con LED (60 mA)")
    limit(ax, 50, "50 V nominal C21", color=INK2)
    limit(ax, 40, "~40 V abs. max LX (supuesto)", va="top")
    ax.set(title="Comportamiento sin carga (OVP)", xlabel="t (ms)", ylabel="V", ylim=(0, 55))
    ax.legend(loc="lower right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG, "3_boost_dio5661.png"), dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ 4) audio
def sim_audio():
    base = open(os.path.join(NET, "4_filtro_audio.cir")).read()
    variants = {"BOM: C10 = 10 nF, C29 = 4,7 nF": "",
                "cambio minimo: C10 = 4,7 nF": ".param r4=3.3k c10=4.7n r3=1k c29=4.7n",
                "recomendado: C10 = 4,7 nF, C29 = 2,2 nF": ".param r4=3.3k c10=4.7n r3=1k c29=2.2n"}
    curves = {}
    res = {}
    for k, (lab, extra) in enumerate(variants.items()):
        out = os.path.join(WORK, f"audio_{k}.dat")
        txt = base.replace("%OUT%", out)
        if extra:
            txt = txt.replace(".param r4=3.3k c10=10n r3=1k c29=4.7n", extra)
        ngspice(txt, f"audio_{k}")
        d = np.loadtxt(out)
        f, db = d[:, 0], d[:, 1]
        g_spk = db + 20 * np.log10(30)  # ganancia hasta la salida del PAM8302A (2*150k/10k)
        pk = db.max()
        fl = f[np.argmax(db > pk - 3)]
        fh = f[np.where(db > pk - 3)[0][-1]]
        at = lambda fx: float(np.interp(np.log10(fx), np.log10(f), db))
        res[lab] = dict(pico_dB=pk, f_baja_3dB=fl, f_alta_3dB=fh, rel_dB_10k=at(1e4) - pk,
                        rel_dB_20k=at(2e4) - pk, rel_dB_281k=at(281.25e3) - pk, rel_dB_1M=at(1e6) - pk)
        curves[lab] = (f, db)
    R["audio"] = res
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for k, (lab, (f, db)) in enumerate(curves.items()):
        ax.semilogx(f, db, color=S[k], label=lab)
    ax.axvspan(20, 20e3, color=GRID, alpha=0.6, lw=0)
    ax.text(150, -75, "banda de audio 20 Hz - 20 kHz", color=INK2, fontsize=8.5)
    ax.axvline(281.25e3, color=INK2, ls=":", lw=1)
    ax.text(300e3, -10, "portadora PWM\n~281 kHz (supuesto)", color=INK2, fontsize=8.5)
    ax.set(title="AUDIO_L -> IN+ del PAM8302A (R4/C10/R3/C29/C12, carga 10 kohm)",
           xlabel="f (Hz)", ylabel="|H| (dB)", ylim=(-90, 5))
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(PNG, "4_filtro_audio.png"), dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------ 5) I2C
def sim_i2c():
    tpl = open(os.path.join(NET, "5_i2c.tpl")).read()
    res = []
    curves = {}
    for rp in ("1k", "4.7k"):
        for cb in ("50p", "100p", "200p", "400p"):
            out = os.path.join(WORK, f"i2c_{rp}_{cb}.dat")
            ngspice(tpl.format(rp=rp, cb=cb, out=out), f"i2c_{rp}_{cb}")
            t, (v,) = load(out, 1)
            m = (t > 2e-6) & (t < 12e-6)
            t30 = t[m][np.argmax(v[m] > 0.3 * 3.3)]
            t70 = t[m][np.argmax(v[m] > 0.7 * 3.3)]
            m2 = t > 12e-6
            f70 = t[m2][np.argmax(v[m2] < 0.7 * 3.3)]
            f30 = t[m2][np.argmax(v[m2] < 0.3 * 3.3)]
            vol = v[(t > 1e-6) & (t < 1.9e-6)].mean()
            res.append(dict(rp=rp, cb=cb, tr_ns=(t70 - t30) * 1e9, tf_ns=(f30 - f70) * 1e9,
                            vol=vol, isink_mA=(3.3 - vol) / float(rp.replace("k", "e3")) * 1e3))
            curves[(rp, cb)] = (t, v)
    R["i2c"] = res
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, rp, bus in zip(axs, ("1k", "4.7k"), ("bus tactil CTP (R1/R2)", "bus ESP32-MCP23017 (R6/R7)")):
        for k, cb in enumerate(("50p", "100p", "200p", "400p")):
            t, v = curves[(rp, cb)]
            m = (t > 1.5e-6) & (t < 6e-6)
            ax.plot((t[m] - 2e-6) * 1e9, v[m], color=S[k], label=f"Cbus = {cb}F")
        for y, lab in ((0.3 * 3.3, "VIL = 0,3 VDD"), (0.7 * 3.3, "VIH = 0,7 VDD")):
            ax.axhline(y, color=INK2, ls=":", lw=1)
            ax.text(3900, y + 0.05, lab, color=INK2, fontsize=8.5, ha="right")
        for x, lab in ((120, "Fm+ 120 ns"), (300, "Fm 300 ns"), (1000, "Sm 1000 ns")):
            ax.axvline(x, color=LIMIT, ls="--", lw=0.9)
            ax.text(x + 20, 0.2, lab, color=LIMIT, fontsize=8, rotation=90, va="bottom")
        ax.set(title=f"Rp = {rp.replace('.', ',')}ohm - {bus}", xlabel="t desde liberacion (ns)", xlim=(-200, 4000))
    axs[0].set_ylabel("SDA/SCL (V)")
    axs[0].legend(loc="center right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(PNG, "5_i2c_subida.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    for fn in (sim_buck, sim_hotplug, sim_boost, sim_audio, sim_i2c):
        print("->", fn.__name__, flush=True)
        fn()
    with open(os.path.join(HERE, "resultados.json"), "w") as f:
        json.dump(R, f, indent=1, default=float)
    print(json.dumps(R, indent=1, default=float))
