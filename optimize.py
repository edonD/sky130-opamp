#!/usr/bin/env python3
"""
Op-amp optimizer using Optuna with proper phase margin computation.
Each simulation writes AC data to a unique temp file for unwrapped PM.
"""

import os
import sys
import re
import json
import csv
import time
import subprocess
import tempfile
import argparse

import numpy as np
import optuna
from optuna.samplers import TPESampler

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
NGSPICE = os.environ.get("NGSPICE", "ngspice")


def load_specs():
    with open(os.path.join(PROJECT_DIR, "specs.json")) as f:
        return json.load(f)


def load_design():
    with open(os.path.join(PROJECT_DIR, "design.cir")) as f:
        return f.read()


def load_parameters():
    params = []
    with open(os.path.join(PROJECT_DIR, "parameters.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            params.append({
                "name": row["name"].strip(),
                "min": float(row["min"]),
                "max": float(row["max"]),
                "scale": row.get("scale", "lin").strip(),
            })
    return params


def format_netlist(template, param_values):
    def _replace(match):
        key = match.group(1)
        if key in param_values:
            return str(param_values[key])
        return match.group(0)
    return re.sub(r'\{(\w+)\}', _replace, template)


def compute_pm_from_file(ac_file):
    """Compute phase margin with np.unwrap from wrdata file."""
    if not os.path.exists(ac_file):
        return None, None
    try:
        raw = np.loadtxt(ac_file)
        if raw.ndim != 2 or raw.shape[1] < 3:
            return None, None
        freq = raw[:, 0]
        real_part = raw[:, 1]
        imag_part = raw[:, 2]
        mask = freq > 0
        freq, real_part, imag_part = freq[mask], real_part[mask], imag_part[mask]
        if len(freq) < 5:
            return None, None
        magnitude = np.sqrt(real_part**2 + imag_part**2)
        gain_db = 20 * np.log10(np.maximum(magnitude, 1e-30))
        phase_rad = np.arctan2(imag_part, real_part)
        phase_unwrapped = np.unwrap(phase_rad)
        phase_deg = np.degrees(phase_unwrapped)

        # Find UGF
        for i in range(len(gain_db) - 1):
            if gain_db[i] > 0 and gain_db[i + 1] <= 0:
                frac = gain_db[i] / (gain_db[i] - gain_db[i + 1])
                ugf = freq[i] * (freq[i + 1] / freq[i]) ** frac
                phase_at_ugf = phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i])
                pm = 180.0 + phase_at_ugf
                return pm, ugf
        return None, None
    except Exception:
        return None, None


def run_sim(template, param_values):
    """Run simulation and return measurements with proper PM."""
    # Create unique temp files
    tmp_dir = tempfile.mkdtemp(prefix="opamp_")
    cir_file = os.path.join(tmp_dir, "sim.cir")
    ac_file = os.path.join(tmp_dir, "ac_data")

    # Add ac_file path to parameters
    all_params = dict(param_values)
    all_params["ac_file"] = ac_file

    netlist = format_netlist(template, all_params)

    with open(cir_file, "w") as f:
        f.write(netlist)

    try:
        result = subprocess.run(
            [NGSPICE, "-b", cir_file],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_DIR
        )
        output = result.stdout + result.stderr
    except (subprocess.TimeoutExpired, Exception):
        return None
    finally:
        pass  # cleanup later

    if "RESULT_DONE" not in output:
        # Cleanup
        try:
            os.unlink(cir_file)
            if os.path.exists(ac_file):
                os.unlink(ac_file)
            os.rmdir(tmp_dir)
        except OSError:
            pass
        return None

    # Parse measurements
    measurements = {}
    for line in output.split("\n"):
        if "RESULT_" in line and "RESULT_DONE" not in line:
            match = re.search(r'(RESULT_\w+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
            if match:
                measurements[match.group(1)] = float(match.group(2))

    # Compute proper PM from ac_data
    pm, ugf = compute_pm_from_file(ac_file)
    if pm is not None:
        measurements["RESULT_PHASE_MARGIN_DEG"] = pm
        measurements["RESULT_GBW_HZ_UNWRAP"] = ugf

    # Cleanup
    try:
        os.unlink(cir_file)
        if os.path.exists(ac_file):
            os.unlink(ac_file)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    return measurements


def compute_cost(measurements, specs):
    """Score: higher is better."""
    if not measurements:
        return -1000

    score = 0
    for spec_name, spec_def in specs["measurements"].items():
        target_str = spec_def["target"].strip()
        weight = spec_def["weight"]
        key = f"RESULT_{spec_name.upper()}"
        val = measurements.get(key)

        if val is None:
            score -= weight * 10
            continue

        if target_str.startswith(">"):
            target = float(target_str[1:])
            if val >= target:
                score += weight * (1.0 + min((val - target) / max(abs(target), 1), 1.0))
            else:
                gap = (target - val) / max(abs(target), 1e-9)
                score -= weight * gap * 5
        elif target_str.startswith("<"):
            target = float(target_str[1:])
            if val <= target:
                score += weight * (1.0 + min((target - val) / max(abs(target), 1), 1.0))
            else:
                gap = (val - target) / max(abs(target), 1e-9)
                score -= weight * gap * 5

    return score


def objective(trial, template, params, specs):
    """Optuna objective."""
    param_values = {}
    for p in params:
        name = p["name"]
        lo, hi = p["min"], p["max"]
        if p["scale"] == "log":
            param_values[name] = trial.suggest_float(name, lo, hi, log=True)
        else:
            param_values[name] = trial.suggest_float(name, lo, hi)

    measurements = run_sim(template, param_values)
    if measurements is None:
        return -1000

    cost = compute_cost(measurements, specs)
    trial.set_user_attr("measurements", measurements)
    trial.set_user_attr("params", param_values)
    return cost


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=200, help="Number of trials")
    parser.add_argument("--jobs", type=int, default=8, help="Parallel jobs")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    if args.quick:
        args.trials = 60

    template = load_design()
    params = load_parameters()
    specs = load_specs()

    print(f"Optuna TPE: {args.trials} trials, {args.jobs} parallel jobs")
    print(f"Parameters: {len(params)}")
    print(f"Phase margin computed from unwrapped AC data (unique temp files)")

    sampler = TPESampler(n_startup_trials=max(20, len(params) * 2), seed=42)
    study = optuna.create_study(direction="maximize", sampler=sampler)

    # Seed with known-good solution from best_parameters.csv if it exists
    best_csv = os.path.join(PROJECT_DIR, "best_parameters.csv")
    if os.path.exists(best_csv):
        try:
            seed_params = {}
            with open(best_csv) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    seed_params[row["name"]] = float(row["value"])
            if seed_params:
                study.enqueue_trial(seed_params)
                print(f"Seeded with known-good solution from best_parameters.csv")
        except Exception as e:
            print(f"Could not seed: {e}")

    t0 = time.time()
    study.optimize(
        lambda trial: objective(trial, template, params, specs),
        n_trials=args.trials,
        n_jobs=args.jobs,
        show_progress_bar=True,
    )
    elapsed = time.time() - t0

    print(f"\nOptimization complete in {elapsed:.0f}s")
    print(f"Best score: {study.best_value:.2f}")

    best_trial = study.best_trial
    best_params = best_trial.user_attrs.get("params", best_trial.params)
    best_measurements = best_trial.user_attrs.get("measurements", {})

    # Re-run for final validation (writes ac_data to project dir for plots)
    print("\nFinal validation re-run...")
    final = run_sim(template, best_params)
    if final:
        best_measurements = final

    # Report
    all_met = True
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    for spec_name, spec_def in specs["measurements"].items():
        target_str = spec_def["target"].strip()
        key = f"RESULT_{spec_name.upper()}"
        val = best_measurements.get(key)
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
        if not met:
            all_met = False
        print(f"  {spec_name:<25} {target_str:>10} {val_str:>12} [{status}]")

    specs_met = sum(1 for sn, sd in specs["measurements"].items()
                    if check_spec(best_measurements, sn, sd))
    print(f"\n  Specs met: {specs_met}/{len(specs['measurements'])}")

    print(f"\n  Best Parameters:")
    for name, val in sorted(best_params.items()):
        print(f"    {name:<20} = {val:.4e}")

    # Save
    with open("best_parameters.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "value"])
        for name, val in sorted(best_params.items()):
            w.writerow([name, val])

    with open("measurements.json", "w") as f:
        json.dump({
            "measurements": best_measurements,
            "score": study.best_value,
            "all_met": all_met,
            "specs_met": specs_met,
            "trials": len(study.trials),
            "elapsed": elapsed,
        }, f, indent=2, default=str)

    print(f"\n{'='*60}")
    return all_met, best_params, best_measurements


def check_spec(measurements, spec_name, spec_def):
    target_str = spec_def["target"].strip()
    key = f"RESULT_{spec_name.upper()}"
    val = measurements.get(key)
    if val is None:
        return False
    if target_str.startswith(">"):
        return val >= float(target_str[1:])
    elif target_str.startswith("<"):
        return val <= float(target_str[1:])
    return False


if __name__ == "__main__":
    all_met, bp, meas = main()
    sys.exit(0 if all_met else 1)
