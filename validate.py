#!/usr/bin/env python3
"""
Comprehensive validation of best parameters.
Runs ngspice, extracts ac_data, computes proper unwrapped PM,
checks operating points, and generates plots.
"""

import csv
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_best_params():
    params = {}
    with open(os.path.join(PROJECT_DIR, "best_parameters.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            params[row["name"]] = float(row["value"])
    return params


def load_specs():
    with open(os.path.join(PROJECT_DIR, "specs.json")) as f:
        return json.load(f)


def load_design():
    with open(os.path.join(PROJECT_DIR, "design.cir")) as f:
        return f.read()


def format_netlist(template, param_values):
    def _replace(match):
        key = match.group(1)
        if key in param_values:
            return str(param_values[key])
        return match.group(0)
    return re.sub(r'\{(\w+)\}', _replace, template)


def create_validation_netlist(params):
    """Create a comprehensive validation netlist."""
    template = load_design()

    # Strip the .control section and replace with comprehensive validation
    lines = template.split("\n")
    new_lines = []
    skip = False
    for line in lines:
        if line.strip().lower().startswith(".control"):
            skip = True
            continue
        if line.strip().lower().startswith(".endc"):
            skip = False
            continue
        if line.strip().lower() == ".end":
            continue
        if not skip:
            new_lines.append(line)

    circuit = "\n".join(new_lines)

    # Format with parameters
    circuit = re.sub(r'\{(\w+)\}', lambda m: str(params.get(m.group(1), m.group(0))), circuit)

    # Add comprehensive measurement control
    circuit += """

.control
* === Operating Point ===
op
let pwr = abs(v(vdd) * i(Vdd)) * 1e6
echo "RESULT_POWER_UW" $&pwr
echo "OP_VDD" $&v(vdd)
echo "OP_BIASN" $&v(biasn)
echo "OP_BIASP" $&v(biasp)
echo "OP_TAIL" $&v(tail)
echo "OP_N1" $&v(n1)
echo "OP_N2" $&v(n2)
echo "OP_OUT" $&v(out)

* === AC Analysis — high resolution ===
ac dec 50 1 1G
wrdata val_ac_data v(out)

meas ac dc_gain_db find vdb(out) at=10
echo "RESULT_DC_GAIN_DB" $&dc_gain_db

let saved_dcgain = dc_gain_db
set dcg_val = "$&saved_dcgain"

meas ac gbw_hz when vdb(out)=0
echo "RESULT_GBW_HZ" $&gbw_hz

meas ac phase_at_gbw find vp(out) when vdb(out)=0
let pm_raw = 180 + phase_at_gbw
echo "RESULT_PM_RAW" $&pm_raw

* === CMRR ===
alter Vinp ac = 1
alter Vinm ac = 1
ac dec 50 1 100Meg
meas ac cm_gain_db find vdb(out) at=10
let cmrr = $dcg_val - cm_gain_db
echo "RESULT_CMRR_DB" $&cmrr

* Restore differential
alter Vinp ac = 0.5
alter Vinm ac = -0.5

* === Output swing — fine resolution ===
dc Vinp 0.0 1.8 0.05
wrdata val_dc_data v(out)
meas dc vout_max max v(out)
meas dc vout_min min v(out)
let swing = vout_max - vout_min
echo "RESULT_OUTPUT_SWING_V" $&swing

echo "RESULT_DONE"
.endc

.end
"""
    return circuit


def run_validation(netlist):
    """Run ngspice and capture output."""
    tmp = os.path.join(PROJECT_DIR, "_validate.cir")
    with open(tmp, "w") as f:
        f.write(netlist)

    try:
        result = subprocess.run(
            ["ngspice", "-b", tmp],
            capture_output=True, text=True, timeout=300,
            cwd=PROJECT_DIR
        )
        return result.stdout + result.stderr
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def parse_results(output):
    """Parse all RESULT_ and OP_ values."""
    results = {}
    for line in output.split("\n"):
        for prefix in ["RESULT_", "OP_"]:
            if prefix in line and "DONE" not in line:
                match = re.search(rf'({prefix}\w+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
                if match:
                    results[match.group(1)] = float(match.group(2))
    return results


def compute_pm_from_ac_data():
    """Compute PM with np.unwrap from val_ac_data."""
    data_file = os.path.join(PROJECT_DIR, "val_ac_data")
    if not os.path.exists(data_file):
        print("  ERROR: val_ac_data not found")
        return None, None, None, None

    raw = np.loadtxt(data_file)
    if raw.ndim != 2 or raw.shape[1] < 3:
        print(f"  ERROR: unexpected shape {raw.shape}")
        return None, None, None, None

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

    dc_gain = gain_db[0]

    # Find UGF
    ugf = None
    pm = None
    for i in range(len(gain_db) - 1):
        if gain_db[i] > 0 and gain_db[i + 1] <= 0:
            frac = gain_db[i] / (gain_db[i] - gain_db[i + 1])
            ugf = freq[i] * (freq[i + 1] / freq[i]) ** frac
            phase_at_ugf = phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i])
            pm = 180.0 + phase_at_ugf
            break

    return dc_gain, ugf, pm, (freq, gain_db, phase_deg)


def generate_plots(freq, gain_db, phase_deg, dc_data, results, specs, details):
    """Generate all required plots."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available, skipping plots")
        return

    os.makedirs("plots", exist_ok=True)

    # Dark theme
    plt.rcParams.update({
        'figure.facecolor': '#1a1a2e', 'axes.facecolor': '#16213e',
        'axes.edgecolor': '#e94560', 'axes.labelcolor': '#eee',
        'text.color': '#eee', 'xtick.color': '#aaa', 'ytick.color': '#aaa',
        'grid.color': '#333', 'grid.alpha': 0.5, 'lines.linewidth': 2,
    })

    # 1. Bode plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax1.semilogx(freq, gain_db, color='#e94560')
    ax1.axhline(y=0, color='#aaa', linestyle='--', alpha=0.5)
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title('Bode Plot')
    ax1.grid(True)

    dc_gain_val = results.get("RESULT_DC_GAIN_DB", gain_db[0])
    gbw_val = results.get("RESULT_GBW_HZ", 0)
    pm_val = details.get("pm_unwrapped", 0)
    ax1.annotate(f'DC Gain = {dc_gain_val:.1f} dB', xy=(0.02, 0.95),
                 xycoords='axes fraction', fontsize=10, color='#e94560')
    ax1.annotate(f'GBW = {gbw_val:.2e} Hz', xy=(0.02, 0.85),
                 xycoords='axes fraction', fontsize=10, color='#e94560')

    ax2.semilogx(freq, phase_deg, color='#0f3460')
    ax2.set_ylabel('Phase (deg)')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.grid(True)
    ax2.annotate(f'PM = {pm_val:.1f}°', xy=(0.02, 0.95),
                 xycoords='axes fraction', fontsize=10, color='#0f3460')

    plt.tight_layout()
    plt.savefig('plots/bode.png', dpi=150)
    plt.close()

    # 2. DC transfer curve
    if dc_data is not None:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dc_data[:, 0], dc_data[:, 1], color='#e94560')
        ax.set_xlabel('Input Voltage (V)')
        ax.set_ylabel('Output Voltage (V)')
        ax.set_title('DC Transfer Curve')
        ax.grid(True)
        swing = results.get("RESULT_OUTPUT_SWING_V", 0)
        ax.annotate(f'Swing = {swing:.2f} V', xy=(0.02, 0.95),
                     xycoords='axes fraction', fontsize=10, color='#e94560')
        plt.tight_layout()
        plt.savefig('plots/dc_transfer.png', dpi=150)
        plt.close()

    print("  Plots saved to plots/")


def main():
    print("=" * 60)
    print("  COMPREHENSIVE VALIDATION")
    print("=" * 60)

    params = load_best_params()
    specs = load_specs()

    print("\nBest parameters:")
    for name, val in sorted(params.items()):
        print(f"  {name:<20} = {val:.4e}")

    # Create and run validation netlist
    print("\nRunning validation simulation...")
    netlist = create_validation_netlist(params)
    output = run_validation(netlist)
    results = parse_results(output)

    if "RESULT_POWER_UW" not in results:
        print("  ERROR: Simulation failed!")
        print(output[-500:])
        return False

    # Operating point
    print("\nOperating Point:")
    for key in ["OP_BIASN", "OP_BIASP", "OP_TAIL", "OP_N1", "OP_N2", "OP_OUT"]:
        if key in results:
            print(f"  {key[3:]:<12} = {results[key]:.4f} V")

    # Compute proper PM
    dc_gain_ac, ugf, pm_unwrapped, bode_data = compute_pm_from_ac_data()

    print(f"\nAC Analysis:")
    print(f"  DC gain (meas):    {results.get('RESULT_DC_GAIN_DB', 'N/A'):.2f} dB")
    if dc_gain_ac is not None:
        print(f"  DC gain (wrdata):  {dc_gain_ac:.2f} dB")
    print(f"  GBW:               {results.get('RESULT_GBW_HZ', 0):.2e} Hz")
    if ugf is not None:
        print(f"  UGF (wrdata):      {ugf:.2e} Hz")
    print(f"  PM (raw vp):       {results.get('RESULT_PM_RAW', 'N/A')}")
    if pm_unwrapped is not None:
        print(f"  PM (unwrapped):    {pm_unwrapped:.1f} deg")

    # Use unwrapped PM
    if pm_unwrapped is not None:
        results["RESULT_PHASE_MARGIN_DEG"] = pm_unwrapped
    else:
        results["RESULT_PHASE_MARGIN_DEG"] = results.get("RESULT_PM_RAW", 0)

    details = {"pm_unwrapped": pm_unwrapped or 0}

    # Check specs
    print(f"\n{'='*60}")
    print(f"  SPEC COMPLIANCE")
    print(f"{'='*60}")

    all_met = True
    spec_results = {}
    for spec_name, spec_def in specs["measurements"].items():
        target_str = spec_def["target"].strip()
        key = f"RESULT_{spec_name.upper()}"
        val = results.get(key)

        if val is None:
            met = False
            val_str = "N/A"
        elif target_str.startswith(">"):
            target = float(target_str[1:])
            met = val >= target
            val_str = f"{val:.4g}"
        elif target_str.startswith("<"):
            target = float(target_str[1:])
            met = val <= target
            val_str = f"{val:.4g}"
        else:
            met = False
            val_str = f"{val:.4g}"

        status = "PASS" if met else "FAIL"
        print(f"  {spec_name:<25} {target_str:>10} {val_str:>12} [{status}]")
        if not met:
            all_met = False
        spec_results[spec_name] = {"value": val, "target": target_str, "met": met}

    specs_met = sum(1 for s in spec_results.values() if s["met"])
    print(f"\n  Result: {specs_met}/{len(spec_results)} specs met")

    # Generate plots
    if bode_data is not None:
        freq, gain_db, phase_deg = bode_data
        dc_data_file = os.path.join(PROJECT_DIR, "val_dc_data")
        dc_data = None
        if os.path.exists(dc_data_file):
            try:
                dc_raw = np.loadtxt(dc_data_file)
                if dc_raw.ndim == 2 and dc_raw.shape[1] >= 2:
                    dc_data = dc_raw[dc_raw[:, 0] > 0]  # filter valid
            except Exception:
                pass
        generate_plots(freq, gain_db, phase_deg, dc_data, results, specs, details)

    # Save results
    with open("measurements.json", "w") as f:
        json.dump({
            "measurements": {k: v for k, v in results.items() if k.startswith("RESULT_")},
            "operating_point": {k: v for k, v in results.items() if k.startswith("OP_")},
            "spec_results": {k: {"value": v["value"], "target": v["target"], "met": bool(v["met"])}
                             for k, v in spec_results.items()},
            "all_specs_met": bool(all_met),
        }, f, indent=2)

    print(f"\n{'='*60}")
    if all_met:
        print("  ALL SPECS MET!")
    else:
        print("  SOME SPECS NOT MET - further optimization needed")
    print(f"{'='*60}")

    return all_met


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
