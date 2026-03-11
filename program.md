# Autonomous Circuit Design — Op-Amp

You are an autonomous analog circuit designer. Your goal: design an operational amplifier that meets every specification in `specs.json` using the SKY130 foundry PDK.

You have Differential Evolution (DE) as your optimizer. You define topology and parameter ranges — DE finds optimal values. You NEVER set component values manually.

## Files

| File | Editable? | Purpose |
|------|-----------|---------|
| `design.cir` | YES | Parametric SPICE netlist |
| `parameters.csv` | YES | Parameter names, min, max for DE |
| `evaluate.py` | YES | Runs DE, measures, scores, plots |
| `specs.json` | **NO** | Target specifications |
| `program.md` | **NO** | These instructions |
| `de/engine.py` | **NO** | DE optimizer engine |
| `results.tsv` | YES | Experiment log — append after every run |

## Technology

- **PDK:** SkyWater SKY130 (130nm). Models: `.lib "sky130_models/sky130.lib.spice" tt`
- **Devices:** `sky130_fd_pr__nfet_01v8`, `sky130_fd_pr__pfet_01v8` (and LVT/HVT variants)
- **Instantiation:** `XM1 drain gate source bulk sky130_fd_pr__nfet_01v8 W=10u L=0.5u nf=1`
- **Supply:** 1.8V single supply. Nodes: `vdd` = 1.8V, `vss` = 0V
- **Units:** Always specify W and L with `u` suffix (micrometers). Capacitors with `p` or `f`.
- **ngspice settings:** `.spiceinit` must contain `set ngbehavior=hsa` and `set skywaterpdk`

## Design Freedom

You are free to explore any op-amp topology or architecture. There are no restrictions on what you can try — single-stage OTA, two-stage Miller, folded cascode, telescopic, recycling folded cascode, gain-boosted, class-AB output, current-mirror OTA, three-stage nested Miller, whatever you think will work. Experiment boldly.

The only constraints are physical reality:

1. **All values parametric.** Every W, L, resistor, capacitor, and bias current uses `{name}` in design.cir with a matching row in parameters.csv.
2. **Ranges must be physically real.** W: 0.5u–500u. L: 0.15u–10u. Bias currents: 1µA–5mA. Caps: 10fF–100pF. Resistors: 50Ω–500kΩ. Ranges must span at least 10× (one decade).
3. **No hardcoding to game the optimizer.** A range of [5.0, 5.001] is cheating. Every parameter must have real design freedom.
4. **No editing specs.json or model files.** You optimize the circuit to meet the specs, not the other way around.

## The Loop

### 1. Read current state
- `results.tsv` — what you've tried and how it scored
- `design.cir` + `parameters.csv` — current topology
- `specs.json` — what you're targeting

### 2. Design or modify the topology
Change whatever you think will improve performance. You can make small tweaks or try a completely different architecture. Your call.

### 3. Implement
- Edit `design.cir` with the new/modified circuit
- Update `parameters.csv` with ranges for all parameters
- Update `evaluate.py` if measurements need changes
- Verify every `{placeholder}` in design.cir has a parameters.csv entry

### 4. Commit topology
```bash
git add -A
git commit -m "topology: <what changed>"
git push
```
Commit ALL files so any commit can be cloned and understood standalone.

### 5. Run DE
```bash
python evaluate.py 2>&1 | tee run.log          # full run
python evaluate.py --quick 2>&1 | tee run.log   # quick sanity check
```

### 6. Validate — THIS IS MANDATORY

DE found numbers. Now prove they're real. **Do not skip any of these checks.**

#### a) Operating point check
Run `.op` and inspect every transistor. Compute `Vds` and `Vgs - Vth` for each device. Every transistor must be in saturation (`Vds > Vgs - Vth` for NMOS, `Vsd > Vsg - |Vth|` for PMOS). If any device is in triode, the gain measurement is garbage — go back to step 2.

#### b) Sanity check against physics
- Phase margin > 120° on a 2+ stage amp → phase measurement wrapped
- DC gain > 150 dB → probably a model artifact
- CMRR > 200 dB → model idealization, not real
- If a number seems too good, it is. Investigate before trusting it.

#### c) Transient cross-validation
Wire the op-amp as a unity-gain follower. Apply a small step (50–100mV around mid-supply). Simulate transient response. **If the output oscillates or rings excessively, the circuit is unstable** — regardless of what PM the AC analysis claims. This is ground truth.

#### d) Inspect plots
Does the Bode gain curve have clean -20dB/dec rolloff at crossover? Does the phase decrease monotonically? Does the DC transfer curve look like a proper amplifier? If the plots look wrong, the extracted numbers are wrong too.

**Only after all four checks pass do you log the result.**

### 7. Generate plots and log results

#### a) Functional plots — `plots/`
Generate these plots every iteration (overwrite previous):
- **`bode.png`** — Gain (dB) and phase (deg) vs frequency. Annotate DC gain, GBW, and phase margin on the plot.
- **`dc_transfer.png`** — Output voltage vs differential input voltage. Show output swing limits.
- **`step_response.png`** — Unity-gain follower step response. Annotate settling time and overshoot.
- **`cmrr.png`** — CMRR vs frequency.

Use a dark theme. Label axes with units. Annotate key measurements directly on each plot.

#### b) Progress plot — `plots/progress.png`
Regenerate from `results.tsv` after every run:
- X axis: iteration number
- Y axis: best score so far
- Mark topology changes with vertical dashed lines
- Mark the point where all specs were first met

#### c) Log to results.tsv
Append one line:
```
<commit_hash>	<score>	<topology>	<specs_met>/<total>	<notes>
```

#### d) Commit and push everything
```bash
git add -A
git commit -m "results: <score> — <summary>"
git push
```
Every commit must include ALL files — source, parameters, plots, logs, measurements.

### 8. Decide next step
- Specs not met → analyze what's failing, change topology or ranges
- DE didn't converge → widen ranges or try different architecture
- Specs met → keep improving margins, then check stopping condition

## Stopping Condition

Track a counter: `steps_without_improvement`. After each run:
- If the best score improved → reset counter to 0
- If it did not improve → increment counter

**Stop when BOTH conditions are true:**
1. All specifications in `specs.json` are met (verified by transient cross-check)
2. `steps_without_improvement >= 50`

Until both conditions are met, keep iterating.

## Known Pitfalls

**Phase wrapping.** ngspice `vp()` wraps phase to ±180°. A true phase of -210° appears as +150°, giving a fake PM of 330°. This has already caused a false "pass" on this project. **Always compute phase from complex `v(out)` using `wrdata`, then unwrap in Python with `np.unwrap`.** Never trust raw `vp()` for phase margin.

**Transient startup.** Never use `uic` for verification — it starts all nodes at 0V which is not the operating point. Always run `.op` first, then transient. Use `.options reltol=0.003 abstol=1e-12 vntol=1e-6 method=gear` if convergence is difficult.

**Low-voltage headroom.** At 1.8V supply, stacking more than 2 transistors in series is very tight. Folded cascode or recycling architectures help. Cascode biasing must be carefully designed to keep all devices in saturation.

**Unrealistic compensation.** For GBW in the MHz range, Miller compensation caps should typically be 0.5–50pF. If DE pushes Cc below 100fF, something is wrong.
