#!/usr/bin/env python3
"""
Bayesian optimization for op-amp design using Optuna.
Each simulation takes ~25s so we need an efficient optimizer.
Uses TPE sampler which is effective with few evaluations.
Runs simulations in parallel.
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
from concurrent.futures import ProcessPoolExecutor, as_completed

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


def run_sim(template, param_values, idx=0):
    """Run a single ngspice simulation. Returns measurements dict."""
    netlist = format_netlist(template, param_values)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.cir', delete=False,
                                      dir=tempfile.gettempdir())
    tmp.write(netlist)
    tmp.close()

    try:
        result = subprocess.run(
            [NGSPICE, "-b", tmp.name],
            capture_output=True, text=True, timeout=60,
            cwd=PROJECT_DIR
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if "RESULT_DONE" not in output:
        return None

    measurements = {}
    for line in output.split("\n"):
        if "RESULT_" in line and "RESULT_DONE" not in line:
            match = re.search(r'(RESULT_\w+)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
            if match:
                measurements[match.group(1)] = float(match.group(2))
    return measurements


def compute_phase_margin_from_ac_data(ac_data_path="ac_data"):
    """Compute PM with np.unwrap from wrdata output."""
    data_file = os.path.join(PROJECT_DIR, ac_data_path)
    if not os.path.exists(data_file):
        return None
    try:
        raw = np.loadtxt(data_file)
        if raw.ndim != 2 or raw.shape[1] < 3:
            return None
        freq = raw[:, 0]
        real_part = raw[:, 1]
        imag_part = raw[:, 2]
        mask = freq > 0
        freq, real_part, imag_part = freq[mask], real_part[mask], imag_part[mask]
        if len(freq) < 5:
            return None
        magnitude = np.sqrt(real_part**2 + imag_part**2)
        gain_db = 20 * np.log10(np.maximum(magnitude, 1e-30))
        phase_rad = np.arctan2(imag_part, real_part)
        phase_unwrapped = np.unwrap(phase_rad)
        phase_deg = np.degrees(phase_unwrapped)
        for i in range(len(gain_db) - 1):
            if gain_db[i] > 0 and gain_db[i + 1] <= 0:
                frac = gain_db[i] / (gain_db[i] - gain_db[i + 1])
                phase_at_ugf = phase_deg[i] + frac * (phase_deg[i + 1] - phase_deg[i])
                return 180.0 + phase_at_ugf
        return None
    except Exception:
        return None


def compute_cost(measurements, specs):
    """Score: higher is better, 100 = all specs met with margin."""
    if not measurements:
        return -1000

    score = 0
    spec_defs = specs["measurements"]

    for spec_name, spec_def in spec_defs.items():
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
                # Bonus for exceeding spec
                score += weight * (1.0 + min((val - target) / max(abs(target), 1), 1.0))
            else:
                # Penalty proportional to gap
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
    """Optuna objective function."""
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

    # Store measurements for later retrieval
    trial.set_user_attr("measurements", measurements)
    trial.set_user_attr("params", param_values)

    return cost


def score_and_report(measurements, specs):
    """Check all specs and report."""
    details = {}
    all_met = True
    for spec_name, spec_def in specs["measurements"].items():
        target_str = spec_def["target"].strip()
        key = f"RESULT_{spec_name.upper()}"
        val = measurements.get(key)

        if val is None:
            details[spec_name] = {"value": None, "target": target_str, "met": False}
            all_met = False
            continue

        if target_str.startswith(">"):
            target = float(target_str[1:])
            met = val >= target
        elif target_str.startswith("<"):
            target = float(target_str[1:])
            met = val <= target
        else:
            met = False

        details[spec_name] = {"value": val, "target": target_str, "met": met}
        if not met:
            all_met = False

    return all_met, details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=200, help="Number of trials")
    parser.add_argument("--jobs", type=int, default=8, help="Parallel jobs")
    parser.add_argument("--quick", action="store_true", help="Quick run (50 trials)")
    args = parser.parse_args()

    if args.quick:
        args.trials = 50

    template = load_design()
    params = load_parameters()
    specs = load_specs()

    print(f"Optuna TPE optimizer: {args.trials} trials, {args.jobs} parallel jobs")
    print(f"Parameters: {len(params)}")

    # Create study
    sampler = TPESampler(n_startup_trials=max(20, len(params) * 2), seed=42)
    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
        study_name="opamp_opt"
    )

    t0 = time.time()

    # Run optimization
    study.optimize(
        lambda trial: objective(trial, template, params, specs),
        n_trials=args.trials,
        n_jobs=args.jobs,
        show_progress_bar=True,
    )

    elapsed = time.time() - t0
    print(f"\nOptimization complete in {elapsed:.0f}s")
    print(f"Best score: {study.best_value:.2f}")

    # Get best parameters
    best_trial = study.best_trial
    best_params = best_trial.user_attrs.get("params", best_trial.params)
    best_measurements = best_trial.user_attrs.get("measurements", {})

    # Re-run best to get fresh measurements and ac_data
    print("\nRe-running best parameters for final validation...")
    final_measurements = run_sim(template, best_params)
    if final_measurements:
        best_measurements = final_measurements

    # Compute proper PM from ac_data
    pm = compute_phase_margin_from_ac_data()
    if pm is not None:
        best_measurements["RESULT_PHASE_MARGIN_DEG"] = pm
        print(f"  Unwrapped PM: {pm:.1f} deg")

    all_met, details = score_and_report(best_measurements, specs)

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    specs_met = sum(1 for d in details.values() if d["met"])
    print(f"  Specs met: {specs_met}/{len(details)}")
    for name, d in details.items():
        status = "PASS" if d["met"] else "FAIL"
        val = f"{d['value']:.4g}" if d['value'] is not None else "N/A"
        print(f"  {name:<25} {d['target']:>10} {val:>12} [{status}]")

    print(f"\n  Best Parameters:")
    for name, val in sorted(best_params.items()):
        print(f"    {name:<20} = {val:.4e}")

    # Save results
    with open("best_parameters.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "value"])
        for name, val in sorted(best_params.items()):
            w.writerow([name, val])

    with open("measurements.json", "w") as f:
        json.dump({
            "measurements": best_measurements,
            "score": study.best_value,
            "details": {k: {"value": v["value"], "target": v["target"], "met": bool(v["met"])} for k, v in details.items()},
            "parameters": best_params,
            "trials": len(study.trials),
            "elapsed": elapsed,
        }, f, indent=2)

    print(f"\nScore: {study.best_value:.2f} | Specs met: {specs_met}/{len(details)}")
    print(f"{'='*60}")

    return all_met, best_params, best_measurements, details


if __name__ == "__main__":
    all_met, best_params, measurements, details = main()
    sys.exit(0 if all_met else 1)
