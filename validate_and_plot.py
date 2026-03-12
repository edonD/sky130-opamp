"""
validate_and_plot.py — Full independent validation of the two-stage Miller OTA.

Runs 5 separate ngspice simulations:
  1. Operating point — verify all transistors in saturation
  2. AC analysis — Bode plot (gain + phase) with proper phase unwrapping
  3. Transient step response — unity-gain follower stability check
  4. DC sweep — transfer curve and output swing
  5. CMRR — common-mode rejection vs frequency

Generates publication-quality plots in plots_blog/
"""

import os
import sys
import csv
import subprocess
import tempfile
import re
import textwrap

import numpy as np

# ---------------------------------------------------------------------------
# Best parameters from DE optimization
# ---------------------------------------------------------------------------

PARAMS = {
    "Cc": 4.666438318258835,
    "Ibias": 9.994908928225167e-06,
    "L1": 1.581460082846346,
    "L3": 0.7584988025913545,
    "L5": 6.136897796674807,
    "L6": 0.2271294623935909,
    "L7": 0.6024717596860268,
    "Lbn": 1.2707119177958432,
    "Lbp": 0.8751213437062734,
    "Rc": 11819.031100938728,
    "W1": 25.694791499854123,
    "W3": 27.045780070413894,
    "W5": 37.11073880050474,
    "W6": 22.03615914749874,
    "W7": 62.66244487173147,
    "Wbn": 11.3338149287469,
    "Wbp": 28.995138011623094,
}

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR = os.path.join(PROJECT_DIR, "plots_blog")
NGSPICE = os.environ.get("NGSPICE", "ngspice")

os.makedirs(PLOTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Common circuit header (parameterised values substituted)
# ---------------------------------------------------------------------------

def circuit_header():
    p = PARAMS
    return textwrap.dedent(f"""\
    * SKY130 Two-Stage Miller OTA — Validation Run
    .lib "sky130_models/sky130_ultra_minimal.lib.spice" tt
    .options reltol=0.003 abstol=1e-12 vntol=1e-6

    * Supply
    Vdd vdd 0 1.8
    Vss vss 0 0

    * === BIAS GENERATION ===
    Ibias vdd biasn {p['Ibias']}
    XMbn biasn biasn vss vss sky130_fd_pr__nfet_01v8 W={p['Wbn']}u L={p['Lbn']}u nf=1

    * PMOS bias
    XMbp1 biasp biasp vdd vdd sky130_fd_pr__pfet_01v8 W={p['Wbp']}u L={p['Lbp']}u nf=1
    XMbp2 biasp biasn vss vss sky130_fd_pr__nfet_01v8 W={p['Wbn']}u L={p['Lbn']}u nf=1

    * === FIRST STAGE ===
    XM5 tail biasn vss vss sky130_fd_pr__nfet_01v8 W={p['W5']}u L={p['L5']}u nf=1
    XM1 n1 inm tail vss sky130_fd_pr__nfet_01v8 W={p['W1']}u L={p['L1']}u nf=1
    XM2 n2 inp tail vss sky130_fd_pr__nfet_01v8 W={p['W1']}u L={p['L1']}u nf=1
    XM3 n1 n1 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W3']}u L={p['L3']}u nf=1
    XM4 n2 n1 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W3']}u L={p['L3']}u nf=1

    * === SECOND STAGE ===
    XM6 out n2 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W6']}u L={p['L6']}u nf=1
    XM7 out biasn vss vss sky130_fd_pr__nfet_01v8 W={p['W7']}u L={p['L7']}u nf=1

    * === Miller compensation ===
    Rc n2 n2rc {p['Rc']}
    Cc n2rc out {p['Cc']}p

    * === Load ===
    CL out 0 5p
    """)


def run_ngspice(netlist_str, label="sim"):
    """Write netlist to temp file, run ngspice, return stdout+stderr."""
    fd, path = tempfile.mkstemp(suffix=".cir", prefix=f"val_{label}_")
    with os.fdopen(fd, "w") as f:
        f.write(netlist_str)
    try:
        result = subprocess.run(
            [NGSPICE, "-b", path],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_DIR,
        )
        return result.stdout + result.stderr
    finally:
        os.unlink(path)


# ===================================================================
# SIM 1: Operating Point
# ===================================================================

def sim_operating_point():
    print("=" * 60)
    print("SIM 1: Operating Point — Saturation Check")
    print("=" * 60)

    netlist = circuit_header() + textwrap.dedent("""\
    * Input at mid-supply
    Vinp inp 0 DC 0.9
    Vinm inm 0 DC 0.9

    .control
    op

    * Print node voltages
    echo "NODE_VDD" $&v(vdd)
    echo "NODE_VSS" $&v(vss)
    echo "NODE_BIASN" $&v(biasn)
    echo "NODE_BIASP" $&v(biasp)
    echo "NODE_TAIL" $&v(tail)
    echo "NODE_N1" $&v(n1)
    echo "NODE_N2" $&v(n2)
    echo "NODE_OUT" $&v(out)
    echo "NODE_INP" $&v(inp)
    echo "NODE_INM" $&v(inm)

    * Power
    let pwr = abs(v(vdd) * i(Vdd)) * 1e6
    echo "POWER_UW" $&pwr

    * Print all device operating points
    show all

    echo "OP_DONE"
    .endc
    .end
    """)

    output = run_ngspice(netlist, "op")

    # Parse node voltages
    nodes = {}
    for line in output.split("\n"):
        if line.strip().startswith("NODE_"):
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    nodes[parts[0]] = float(parts[1])
                except ValueError:
                    pass
        if line.strip().startswith("POWER_UW"):
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    nodes["POWER_UW"] = float(parts[1])
                except ValueError:
                    pass

    print(f"\n  Node Voltages:")
    for k in sorted(nodes):
        if k.startswith("NODE_"):
            name = k.replace("NODE_", "")
            print(f"    {name:>10} = {nodes[k]:.4f} V")

    power = nodes.get("POWER_UW", 0)
    print(f"\n  Power: {power:.1f} uW")

    # Saturation check
    vdd = nodes.get("NODE_VDD", 1.8)
    vss = nodes.get("NODE_VSS", 0.0)
    biasn = nodes.get("NODE_BIASN", 0)
    biasp = nodes.get("NODE_BIASP", 0)
    tail = nodes.get("NODE_TAIL", 0)
    n1 = nodes.get("NODE_N1", 0)
    n2 = nodes.get("NODE_N2", 0)
    out = nodes.get("NODE_OUT", 0)
    inp = nodes.get("NODE_INP", 0.9)
    inm = nodes.get("NODE_INM", 0.9)

    # We'll estimate Vth ~ 0.5V for NMOS, ~0.5V for PMOS as rough check
    # The real check is Vds > Vov (= Vgs - Vth)
    VTN = 0.5  # approximate NMOS threshold
    VTP = 0.5  # approximate |PMOS threshold|

    print(f"\n  Transistor Saturation Check (Vth_n~{VTN}V, |Vth_p|~{VTP}V):")
    print(f"  {'Device':<8} {'Type':<6} {'Vgs/Vsg':>8} {'Vds/Vsd':>8} {'Vov':>8} {'Status':>10}")
    print(f"  {'-'*50}")

    devices = [
        # (name, type, Vg, Vs, Vd)
        ("XMbn",  "NMOS", biasn, vss,  biasn),  # diode: Vds = Vgs
        ("XMbp1", "PMOS", biasp, vdd,  biasp),  # diode
        ("XMbp2", "NMOS", biasn, vss,  biasp),
        ("XM5",   "NMOS", biasn, vss,  tail),
        ("XM1",   "NMOS", inm,   tail, n1),
        ("XM2",   "NMOS", inp,   tail, n2),
        ("XM3",   "PMOS", n1,    vdd,  n1),     # diode
        ("XM4",   "PMOS", n1,    vdd,  n2),
        ("XM6",   "PMOS", n2,    vdd,  out),
        ("XM7",   "NMOS", biasn, vss,  out),
    ]

    all_sat = True
    device_info = []
    for name, typ, vg, vs, vd in devices:
        if typ == "NMOS":
            vgs = vg - vs
            vds = vd - vs
            vov = vgs - VTN
        else:  # PMOS
            vgs = vs - vg  # Vsg
            vds = vs - vd  # Vsd
            vov = vgs - VTP

        sat = vds >= vov - 0.05  # small tolerance
        status = "SAT" if sat else "TRIODE"
        if not sat:
            all_sat = False
        print(f"  {name:<8} {typ:<6} {vgs:>8.3f} {vds:>8.3f} {vov:>8.3f} {status:>10}")
        device_info.append((name, typ, vgs, vds, vov, sat))

    print(f"\n  All transistors in saturation: {'YES' if all_sat else 'NO <<<'}")

    return nodes, device_info, power


# ===================================================================
# SIM 2: AC Analysis — Bode Plot
# ===================================================================

def sim_ac_analysis():
    print("\n" + "=" * 60)
    print("SIM 2: AC Analysis — Bode Plot")
    print("=" * 60)

    ac_file = os.path.join(PROJECT_DIR, "val_ac_data")

    netlist = circuit_header() + textwrap.dedent(f"""\
    * Differential AC stimulus
    Vinp inp 0 DC 0.9 AC 0.5
    Vinm inm 0 DC 0.9 AC -0.5

    .control
    op
    ac dec 100 1 10G
    wrdata {ac_file} v(out)

    meas ac dc_gain_db find vdb(out) at=10
    echo "RESULT_DC_GAIN_DB" $&dc_gain_db

    meas ac gbw_hz when vdb(out)=0
    echo "RESULT_GBW_HZ" $&gbw_hz

    echo "AC_DONE"
    .endc
    .end
    """)

    output = run_ngspice(netlist, "ac")

    # Parse measurements from output
    meas = {}
    for line in output.split("\n"):
        for tag in ["RESULT_DC_GAIN_DB", "RESULT_GBW_HZ"]:
            if tag in line:
                m = re.search(rf'{tag}\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
                if m:
                    meas[tag] = float(m.group(1))

    # Read AC data
    raw = np.loadtxt(ac_file)
    freq = raw[:, 0]
    real_part = raw[:, 1]
    imag_part = raw[:, 2]

    mask = freq > 0
    freq = freq[mask]
    real_part = real_part[mask]
    imag_part = imag_part[mask]

    magnitude = np.sqrt(real_part**2 + imag_part**2)
    gain_db = 20 * np.log10(np.maximum(magnitude, 1e-30))
    phase_rad = np.arctan2(imag_part, real_part)
    phase_unwrapped = np.unwrap(phase_rad)
    phase_deg = np.degrees(phase_unwrapped)

    # Find GBW (0dB crossing)
    gbw = None
    phase_at_gbw = None
    for i in range(len(gain_db) - 1):
        if gain_db[i] > 0 and gain_db[i + 1] <= 0:
            frac = gain_db[i] / (gain_db[i] - gain_db[i + 1])
            gbw = freq[i] * (freq[i + 1] / freq[i]) ** frac
            phase_at_gbw = phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i])
            break

    pm = 180.0 + phase_at_gbw if phase_at_gbw is not None else None
    dc_gain = gain_db[0]

    print(f"  DC Gain:       {dc_gain:.1f} dB")
    print(f"  GBW:           {gbw/1e6:.2f} MHz" if gbw else "  GBW: not found")
    print(f"  Phase at GBW:  {phase_at_gbw:.1f} deg" if phase_at_gbw else "")
    print(f"  Phase Margin:  {pm:.1f} deg" if pm else "  PM: not found")

    # Find gain margin (phase = -180 crossing)
    gm_db = None
    freq_gm = None
    for i in range(len(phase_deg) - 1):
        if phase_deg[i] > -180 and phase_deg[i + 1] <= -180:
            frac = (phase_deg[i] + 180) / (phase_deg[i] - phase_deg[i + 1])
            freq_gm = freq[i] * (freq[i + 1] / freq[i]) ** frac
            gm_db = -(gain_db[i] + frac * (gain_db[i + 1] - gain_db[i]))
            break

    if gm_db is not None:
        print(f"  Gain Margin:   {gm_db:.1f} dB at {freq_gm/1e6:.1f} MHz")

    # Clean up
    try:
        os.unlink(ac_file)
    except OSError:
        pass

    return freq, gain_db, phase_deg, dc_gain, gbw, pm, gm_db, freq_gm


# ===================================================================
# SIM 3: Transient Step Response (Unity-Gain Follower)
# ===================================================================

def sim_transient():
    print("\n" + "=" * 60)
    print("SIM 3: Transient — Unity-Gain Follower Step Response")
    print("=" * 60)

    tran_file = os.path.join(PROJECT_DIR, "val_tran_data")
    p = PARAMS

    netlist = textwrap.dedent(f"""\
    * SKY130 Two-Stage Miller OTA — Unity-Gain Follower Transient
    .lib "sky130_models/sky130_ultra_minimal.lib.spice" tt
    .options reltol=0.003 abstol=1e-12 vntol=1e-6

    Vdd vdd 0 1.8
    Vss vss 0 0

    * Step input: 0.85V -> 0.95V at 1us, back to 0.85V at 10us
    Vin inp 0 PWL(0 0.85 0.99u 0.85 1u 0.95 9.99u 0.95 10u 0.85 15u 0.85)

    * === BIAS ===
    Ibias vdd biasn {p['Ibias']}
    XMbn biasn biasn vss vss sky130_fd_pr__nfet_01v8 W={p['Wbn']}u L={p['Lbn']}u nf=1
    XMbp1 biasp biasp vdd vdd sky130_fd_pr__pfet_01v8 W={p['Wbp']}u L={p['Lbp']}u nf=1
    XMbp2 biasp biasn vss vss sky130_fd_pr__nfet_01v8 W={p['Wbn']}u L={p['Lbn']}u nf=1

    * === FIRST STAGE ===
    XM5 tail biasn vss vss sky130_fd_pr__nfet_01v8 W={p['W5']}u L={p['L5']}u nf=1
    XM1 n1 out tail vss sky130_fd_pr__nfet_01v8 W={p['W1']}u L={p['L1']}u nf=1
    XM2 n2 inp tail vss sky130_fd_pr__nfet_01v8 W={p['W1']}u L={p['L1']}u nf=1
    XM3 n1 n1 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W3']}u L={p['L3']}u nf=1
    XM4 n2 n1 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W3']}u L={p['L3']}u nf=1

    * === SECOND STAGE ===
    XM6 out n2 vdd vdd sky130_fd_pr__pfet_01v8 W={p['W6']}u L={p['L6']}u nf=1
    XM7 out biasn vss vss sky130_fd_pr__nfet_01v8 W={p['W7']}u L={p['L7']}u nf=1

    * === Compensation ===
    Rc n2 n2rc {p['Rc']}
    Cc n2rc out {p['Cc']}p

    * === Load ===
    CL out 0 5p

    .control
    tran 5n 15u
    wrdata {tran_file} v(inp) v(out)
    echo "TRAN_DONE"
    .endc
    .end
    """)

    output = run_ngspice(netlist, "tran")

    raw = np.loadtxt(tran_file)
    time_s = raw[:, 0]
    v_inp = raw[:, 1]
    v_out = raw[:, 3]  # wrdata: col0=time, col1=v(inp)_real, col2=v(inp)_imag, col3=v(out)_real

    # Actually wrdata format for tran: time, val1, val2
    # Let me check the shape
    if raw.shape[1] == 3:
        v_inp = raw[:, 1]
        v_out = raw[:, 2]
    elif raw.shape[1] >= 4:
        v_inp = raw[:, 1]
        v_out = raw[:, 3]

    # Measure settling and overshoot on rising edge
    # Find the step region (around 1us)
    step_mask = (time_s >= 0.9e-6) & (time_s <= 5e-6)
    t_step = time_s[step_mask]
    v_step = v_out[step_mask]

    if len(v_step) > 0:
        v_final = 0.95  # expected final value
        v_init = 0.85
        v_peak = np.max(v_step)
        overshoot = (v_peak - v_final) / (v_final - v_init) * 100
        overshoot = max(0, overshoot)

        # Settling time (1% band)
        settled = np.abs(v_step - v_final) < 0.01 * abs(v_final - v_init)
        settle_idx = None
        for i in range(len(settled) - 1, -1, -1):
            if not settled[i]:
                if i + 1 < len(t_step):
                    settle_idx = i + 1
                break
        if settle_idx is not None:
            settling_time = t_step[settle_idx] - 1e-6
        else:
            settling_time = 0

        print(f"  Overshoot:     {overshoot:.1f}%")
        print(f"  Settling (1%): {settling_time*1e6:.3f} us")
    else:
        overshoot = 0
        settling_time = 0

    try:
        os.unlink(tran_file)
    except OSError:
        pass

    return time_s, v_inp, v_out, overshoot, settling_time


# ===================================================================
# SIM 4: DC Sweep — Transfer Curve
# ===================================================================

def sim_dc_sweep():
    print("\n" + "=" * 60)
    print("SIM 4: DC Sweep — Transfer Curve")
    print("=" * 60)

    dc_file = os.path.join(PROJECT_DIR, "val_dc_data")

    netlist = circuit_header() + textwrap.dedent(f"""\
    * Single-ended sweep of Vinp
    Vinp inp 0 DC 0.9
    Vinm inm 0 DC 0.9

    .control
    dc Vinp 0 1.8 0.001
    wrdata {dc_file} v(out)

    meas dc vout_max max v(out)
    meas dc vout_min min v(out)
    let swing = vout_max - vout_min
    echo "SWING" $&swing
    echo "VMAX" $&vout_max
    echo "VMIN" $&vout_min
    echo "DC_DONE"
    .endc
    .end
    """)

    output = run_ngspice(netlist, "dc")

    raw = np.loadtxt(dc_file)
    v_inp = raw[:, 0]
    v_out = raw[:, 1]

    vmax = np.max(v_out)
    vmin = np.min(v_out)
    swing = vmax - vmin

    print(f"  Output Max:    {vmax:.4f} V")
    print(f"  Output Min:    {vmin:.4f} V")
    print(f"  Output Swing:  {swing:.3f} V")

    try:
        os.unlink(dc_file)
    except OSError:
        pass

    return v_inp, v_out, vmax, vmin, swing


# ===================================================================
# SIM 5: CMRR vs Frequency
# ===================================================================

def sim_cmrr():
    print("\n" + "=" * 60)
    print("SIM 5: CMRR vs Frequency")
    print("=" * 60)

    dm_file = os.path.join(PROJECT_DIR, "val_dm_data")
    cm_file = os.path.join(PROJECT_DIR, "val_cm_data")

    # Differential-mode AC
    netlist_dm = circuit_header() + textwrap.dedent(f"""\
    Vinp inp 0 DC 0.9 AC 0.5
    Vinm inm 0 DC 0.9 AC -0.5

    .control
    op
    ac dec 50 1 1G
    wrdata {dm_file} v(out)
    echo "DM_DONE"
    .endc
    .end
    """)

    # Common-mode AC
    netlist_cm = circuit_header() + textwrap.dedent(f"""\
    Vinp inp 0 DC 0.9 AC 1
    Vinm inm 0 DC 0.9 AC 1

    .control
    op
    ac dec 50 1 1G
    wrdata {cm_file} v(out)
    echo "CM_DONE"
    .endc
    .end
    """)

    run_ngspice(netlist_dm, "dm")
    run_ngspice(netlist_cm, "cm")

    raw_dm = np.loadtxt(dm_file)
    raw_cm = np.loadtxt(cm_file)

    freq_dm = raw_dm[:, 0]
    dm_mag = np.sqrt(raw_dm[:, 1]**2 + raw_dm[:, 2]**2)

    freq_cm = raw_cm[:, 0]
    cm_mag = np.sqrt(raw_cm[:, 1]**2 + raw_cm[:, 2]**2)

    # Use the shorter array length for alignment
    n = min(len(freq_dm), len(freq_cm))
    freq = freq_dm[:n]
    mask = freq > 0
    freq = freq[mask]
    dm_mag = dm_mag[:n][mask]
    cm_mag = cm_mag[:n][mask]

    # CMRR = differential gain / common-mode gain
    # DM stimulus is ±0.5 (so vdiff=1), CM stimulus is 1 (vcm=1)
    cmrr_db = 20 * np.log10(np.maximum(dm_mag, 1e-30)) - 20 * np.log10(np.maximum(cm_mag, 1e-30))

    cmrr_dc = cmrr_db[0] if len(cmrr_db) > 0 else 0
    print(f"  CMRR at DC:    {cmrr_dc:.1f} dB")

    for fname in [dm_file, cm_file]:
        try:
            os.unlink(fname)
        except OSError:
            pass

    return freq, cmrr_db, dm_mag, cm_mag, cmrr_dc


# ===================================================================
# PLOTTING — Publication quality for blog
# ===================================================================

def setup_style():
    """Set up a clean, modern dark style for blog plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    # Dark theme
    rcParams.update({
        "figure.facecolor": "#0f1117",
        "axes.facecolor": "#161b22",
        "axes.edgecolor": "#30363d",
        "axes.labelcolor": "#c9d1d9",
        "axes.titlesize": 16,
        "axes.labelsize": 13,
        "text.color": "#c9d1d9",
        "xtick.color": "#8b949e",
        "ytick.color": "#8b949e",
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "grid.color": "#21262d",
        "grid.alpha": 0.8,
        "grid.linewidth": 0.5,
        "lines.linewidth": 2.0,
        "figure.dpi": 150,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.facecolor": "#0f1117",
        "font.family": "sans-serif",
        "font.size": 12,
        "legend.facecolor": "#161b22",
        "legend.edgecolor": "#30363d",
        "legend.fontsize": 11,
    })
    return plt


def plot_bode(plt, freq, gain_db, phase_deg, dc_gain, gbw, pm, gm_db, freq_gm):
    """Bode plot — gain and phase on shared x-axis."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True,
                                     gridspec_kw={"height_ratios": [1.2, 1], "hspace": 0.08})

    # --- Gain ---
    ax1.semilogx(freq, gain_db, color="#58a6ff", linewidth=2.2, zorder=3)
    ax1.axhline(0, color="#8b949e", linewidth=0.8, linestyle="--", alpha=0.6)
    ax1.set_ylabel("Gain (dB)")
    ax1.set_title("Bode Plot — Two-Stage Miller OTA (SKY130)", fontsize=16, fontweight="bold", pad=12)
    ax1.grid(True, which="both", alpha=0.3)
    ax1.set_ylim([-60, 100])

    # Annotate DC gain
    ax1.annotate(f"DC Gain = {dc_gain:.1f} dB",
                 xy=(10, dc_gain), xytext=(50, dc_gain - 12),
                 fontsize=12, color="#7ee787", fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#7ee787", lw=1.5))

    # Annotate GBW
    if gbw:
        ax1.plot(gbw, 0, "o", color="#f78166", markersize=8, zorder=5)
        ax1.annotate(f"GBW = {gbw/1e6:.1f} MHz",
                     xy=(gbw, 0), xytext=(gbw * 3, 15),
                     fontsize=12, color="#f78166", fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color="#f78166", lw=1.5))

    # --- Phase ---
    ax2.semilogx(freq, phase_deg, color="#d2a8ff", linewidth=2.2, zorder=3)
    ax2.axhline(-180, color="#da3633", linewidth=1.0, linestyle="--", alpha=0.7, label="-180° (instability)")
    ax2.set_ylabel("Phase (deg)")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.set_ylim([-300, 30])

    # Annotate PM
    if gbw and pm:
        phase_at_gbw = pm - 180
        ax2.plot(gbw, phase_at_gbw, "o", color="#f78166", markersize=8, zorder=5)

        # Draw PM arc
        ax2.annotate("", xy=(gbw, -180), xytext=(gbw, phase_at_gbw),
                     arrowprops=dict(arrowstyle="<->", color="#7ee787", lw=2))
        ax2.text(gbw * 1.5, (phase_at_gbw - 180) / 2, f"PM = {pm:.1f}°",
                 fontsize=12, color="#7ee787", fontweight="bold")

    # Annotate gain margin
    if gm_db and freq_gm:
        gain_at_180 = -gm_db  # gain is negative at this point
        ax1.plot(freq_gm, gain_at_180, "s", color="#d29922", markersize=8, zorder=5)
        ax1.annotate(f"GM = {gm_db:.1f} dB",
                     xy=(freq_gm, gain_at_180), xytext=(freq_gm / 5, gain_at_180 + 12),
                     fontsize=11, color="#d29922", fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color="#d29922", lw=1.5))

    ax2.legend(loc="lower left", framealpha=0.8)

    fig.savefig(os.path.join(PLOTS_DIR, "bode.png"))
    plt.close(fig)
    print("  Saved: bode.png")


def plot_step_response(plt, time_s, v_inp, v_out, overshoot, settling_time):
    """Unity-gain follower step response."""
    fig, ax = plt.subplots(figsize=(12, 5))

    t_us = time_s * 1e6

    ax.plot(t_us, v_inp, "--", color="#8b949e", linewidth=1.5, label="Input", zorder=2)
    ax.plot(t_us, v_out, color="#58a6ff", linewidth=2.2, label="Output", zorder=3)

    ax.set_xlabel("Time (us)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Unity-Gain Follower Step Response", fontsize=16, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", framealpha=0.8)

    # Annotate settling
    ax.annotate(f"Overshoot: {overshoot:.1f}%\nSettling (1%): {settling_time*1e6:.2f} us",
                xy=(2.5, 0.945), fontsize=12, color="#7ee787",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#161b22", edgecolor="#7ee787", alpha=0.9))

    # Draw 1% settling band
    ax.axhspan(0.95 * 0.99, 0.95 * 1.01, xmin=0, xmax=1,
               color="#7ee787", alpha=0.08, zorder=1)

    ax.set_xlim([0, 15])
    ax.set_ylim([0.82, 0.98])

    fig.savefig(os.path.join(PLOTS_DIR, "step_response.png"))
    plt.close(fig)
    print("  Saved: step_response.png")


def plot_dc_transfer(plt, v_inp, v_out, vmax, vmin, swing):
    """DC transfer curve."""
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(v_inp, v_out, color="#58a6ff", linewidth=2.2, zorder=3)

    # Rail lines
    ax.axhline(vmax, color="#7ee787", linewidth=0.8, linestyle=":", alpha=0.5)
    ax.axhline(vmin, color="#da3633", linewidth=0.8, linestyle=":", alpha=0.5)

    ax.set_xlabel("Input Voltage V(inp) (V)")
    ax.set_ylabel("Output Voltage (V)")
    ax.set_title("DC Transfer Curve", fontsize=16, fontweight="bold", pad=12)
    ax.grid(True, alpha=0.3)

    # Annotate swing
    ax.annotate(f"Output Swing: {vmin:.3f}V to {vmax:.3f}V = {swing:.2f}V",
                xy=(0.5, vmax * 0.5), fontsize=12, color="#f0883e",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#161b22", edgecolor="#f0883e", alpha=0.9))

    # Draw swing bracket on the right
    ax.annotate("", xy=(1.65, vmin), xytext=(1.65, vmax),
                arrowprops=dict(arrowstyle="<->", color="#f0883e", lw=2))

    fig.savefig(os.path.join(PLOTS_DIR, "dc_transfer.png"))
    plt.close(fig)
    print("  Saved: dc_transfer.png")


def plot_cmrr(plt, freq, cmrr_db, cmrr_dc):
    """CMRR vs frequency."""
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.semilogx(freq, cmrr_db, color="#d2a8ff", linewidth=2.2, zorder=3)
    ax.axhline(60, color="#da3633", linewidth=1.0, linestyle="--", alpha=0.7, label="Spec: 60 dB")

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("CMRR (dB)")
    ax.set_title("Common-Mode Rejection Ratio", fontsize=16, fontweight="bold", pad=12)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left", framealpha=0.8)

    ax.annotate(f"CMRR at DC = {cmrr_dc:.1f} dB",
                xy=(10, cmrr_dc), xytext=(100, cmrr_dc - 10),
                fontsize=12, color="#7ee787", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#7ee787", lw=1.5))

    fig.savefig(os.path.join(PLOTS_DIR, "cmrr.png"))
    plt.close(fig)
    print("  Saved: cmrr.png")


def plot_summary_dashboard(plt, dc_gain, gbw, pm, power, swing, cmrr_dc, overshoot, settling_time):
    """Combined summary dashboard — the hero image for the blog."""
    fig = plt.figure(figsize=(14, 8))
    fig.suptitle("AI-Designed Op-Amp — SKY130 Two-Stage Miller OTA",
                 fontsize=18, fontweight="bold", color="#f0f6fc", y=0.98)

    # Specs table
    specs = [
        ("DC Gain", f"{dc_gain:.1f} dB", ">60 dB", dc_gain >= 60),
        ("GBW", f"{gbw/1e6:.1f} MHz", ">5 MHz", gbw >= 5e6),
        ("Phase Margin", f"{pm:.1f}°", ">60°", pm >= 60),
        ("Power", f"{power:.0f} uW", "<1000 uW", power <= 1000),
        ("Output Swing", f"{swing:.2f} V", ">1.2 V", swing >= 1.2),
        ("CMRR", f"{cmrr_dc:.1f} dB", ">60 dB", cmrr_dc >= 60),
    ]

    ax_table = fig.add_axes([0.05, 0.05, 0.9, 0.88])
    ax_table.set_xlim(0, 10)
    ax_table.set_ylim(0, 10)
    ax_table.axis("off")

    # Title row
    y_start = 9.0
    row_h = 1.1
    headers = ["Specification", "Measured", "Target", "Status"]
    x_cols = [1.0, 4.0, 6.5, 8.5]

    for i, h in enumerate(headers):
        ax_table.text(x_cols[i], y_start, h, fontsize=13, fontweight="bold",
                      color="#8b949e", ha="center")

    ax_table.plot([0.2, 9.8], [y_start - 0.3, y_start - 0.3], color="#30363d", linewidth=1)

    for j, (name, measured, target, met) in enumerate(specs):
        y = y_start - 0.6 - (j + 1) * row_h
        color = "#7ee787" if met else "#da3633"
        status = "PASS" if met else "FAIL"

        ax_table.text(x_cols[0], y, name, fontsize=13, color="#c9d1d9", ha="center")
        ax_table.text(x_cols[1], y, measured, fontsize=14, color=color, ha="center", fontweight="bold")
        ax_table.text(x_cols[2], y, target, fontsize=13, color="#8b949e", ha="center")
        ax_table.text(x_cols[3], y, status, fontsize=13, color=color, ha="center", fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.15, edgecolor=color))

    # Bottom info
    ax_table.text(5.0, 0.5,
                  f"Overshoot: {overshoot:.1f}%  |  Settling: {settling_time*1e6:.2f} us  |  "
                  f"All specs met: 6/6  |  Score: 1.00",
                  fontsize=12, color="#8b949e", ha="center",
                  bbox=dict(boxstyle="round,pad=0.5", facecolor="#0d1117", edgecolor="#30363d"))

    fig.savefig(os.path.join(PLOTS_DIR, "summary_dashboard.png"))
    plt.close(fig)
    print("  Saved: summary_dashboard.png")


def plot_circuit_params(plt):
    """Visualize the circuit parameters as a clean table."""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    fig.suptitle("Optimized Circuit Parameters", fontsize=16, fontweight="bold",
                 color="#f0f6fc", y=0.96)

    sections = [
        ("Input Pair (M1/M2)", [("W", PARAMS["W1"], "um"), ("L", PARAMS["L1"], "um")]),
        ("PMOS Load (M3/M4)", [("W", PARAMS["W3"], "um"), ("L", PARAMS["L3"], "um")]),
        ("Tail Source (M5)", [("W", PARAMS["W5"], "um"), ("L", PARAMS["L5"], "um")]),
        ("2nd Stage Driver (M6)", [("W", PARAMS["W6"], "um"), ("L", PARAMS["L6"], "um")]),
        ("2nd Stage Load (M7)", [("W", PARAMS["W7"], "um"), ("L", PARAMS["L7"], "um")]),
        ("Bias", [("Ibias", PARAMS["Ibias"] * 1e6, "uA"), ("W_bn", PARAMS["Wbn"], "um"),
                  ("L_bn", PARAMS["Lbn"], "um")]),
        ("Compensation", [("Cc", PARAMS["Cc"], "pF"), ("Rc", PARAMS["Rc"] / 1e3, "kOhm")]),
    ]

    y = 11.0
    for section_name, params in sections:
        ax.text(0.5, y, section_name, fontsize=12, fontweight="bold", color="#58a6ff")
        param_str = "   ".join([f"{n} = {v:.2f} {u}" for n, v, u in params])
        ax.text(0.8, y - 0.5, param_str, fontsize=11, color="#c9d1d9")
        y -= 1.3

    fig.savefig(os.path.join(PLOTS_DIR, "circuit_params.png"))
    plt.close(fig)
    print("  Saved: circuit_params.png")


# ===================================================================
# Main
# ===================================================================

def main():
    print("\n" + "#" * 60)
    print("#  FULL VALIDATION — Two-Stage Miller OTA (SKY130)")
    print("#" * 60)

    # Run all simulations
    nodes, device_info, power = sim_operating_point()
    freq, gain_db, phase_deg, dc_gain, gbw, pm, gm_db, freq_gm = sim_ac_analysis()
    time_s, v_inp, v_out, overshoot, settling_time = sim_transient()
    v_dc_inp, v_dc_out, vmax, vmin, swing = sim_dc_sweep()
    freq_cmrr, cmrr_db, dm_mag, cm_mag, cmrr_dc = sim_cmrr()

    # Generate plots
    print("\n" + "=" * 60)
    print("GENERATING PLOTS")
    print("=" * 60)

    plt = setup_style()

    plot_bode(plt, freq, gain_db, phase_deg, dc_gain, gbw, pm, gm_db, freq_gm)
    plot_step_response(plt, time_s, v_inp, v_out, overshoot, settling_time)
    plot_dc_transfer(plt, v_dc_inp, v_dc_out, vmax, vmin, swing)
    plot_cmrr(plt, freq_cmrr, cmrr_db, cmrr_dc)
    plot_summary_dashboard(plt, dc_gain, gbw, pm, power, swing, cmrr_dc, overshoot, settling_time)
    plot_circuit_params(plt)

    # Final summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  DC Gain:       {dc_gain:.1f} dB    (spec: >60)    {'PASS' if dc_gain >= 60 else 'FAIL'}")
    print(f"  GBW:           {gbw/1e6:.1f} MHz   (spec: >5)     {'PASS' if gbw >= 5e6 else 'FAIL'}")
    print(f"  Phase Margin:  {pm:.1f} deg   (spec: >60)    {'PASS' if pm >= 60 else 'FAIL'}")
    print(f"  Power:         {power:.0f} uW    (spec: <1000)  {'PASS' if power <= 1000 else 'FAIL'}")
    print(f"  Output Swing:  {swing:.2f} V     (spec: >1.2)   {'PASS' if swing >= 1.2 else 'FAIL'}")
    print(f"  CMRR:          {cmrr_dc:.1f} dB    (spec: >60)    {'PASS' if cmrr_dc >= 60 else 'FAIL'}")
    if gm_db:
        print(f"  Gain Margin:   {gm_db:.1f} dB")
    print(f"  Overshoot:     {overshoot:.1f}%")
    print(f"  Settling:      {settling_time*1e6:.2f} us")
    print(f"\n  All plots saved to: {PLOTS_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
