# Optimisation notes

The hackathon version worked, but it was slow (~24 s per shot) and its
target selection broke in a common case. This pass refactors and tunes the
code, and adds a PC simulator so the changes can be measured without
hardware.

> **All figures below are simulated** (`python sim/simulate.py`, 10,000
> random scenes per configuration, fixed seed) or derived from the delays
> in the code. They have not been measured on the physical catapult.
> Assumptions are listed at the top of [sim/results.md](sim/results.md).

## Headline results

| Metric | Before | After |
|---|---|---|
| Target selection accuracy (random scenes) | 89.0% | 97.5% |
| Accuracy, two objects side by side | 87.6% | 100% |
| Mean aim error | 5.0° | 2.5° |
| Distance estimate error | 13.9% | 1.6% |
| Scan time | 18.5 s | 4.6 s (4.1× faster) |
| Full scan-aim-fire cycle | 24.0 s | 9.9 s (59% shorter) |
| Targets engaged per minute | 2.5 | 6.1 |
| Sensor readings per scan | 260 | 104 (-60%) |

## What changed and why

### 1. Clustering splits on depth as well as angle (accuracy fix)
The original `find_clusters` only started a new cluster when there was a
gap in angle. Two objects next to each other (e.g. a box in front of a
wall section) became one cluster, so the catapult aimed at the midpoint
between them and used a blended distance. The new version also splits
when the distance jumps by more than 150 mm, and sorts readings by angle
first so it works whichever direction the turret swept.
*Effect: side-by-side accuracy 87.6% → 100%, aim error 7.5° → 0.9°.*

### 2. Continuous sensor mode instead of start/stop per reading
`tof.ping()` puts the VL53L0X into ranging mode, waits for one result and
stops it again, and the loop then slept another 20 ms. Now the sensor is
started once and `tof.read()` just collects the next back-to-back result.
One reading is discarded after every turret move so a measurement taken
while moving is never used.
*Effect: ~56 ms → ~33 ms per reading (-41%).*

### 3. Samples per step 20 → 7, chosen by simulation
The simulator swept 1-20 samples per step. Accuracy plateaus at ~97.5%
from 3 samples upward; 1 sample produces 10.6% false targets on empty
scenes, 3 still produces some under heavy noise. 7 keeps 0% false targets
and ~1.6% distance error even with 15% outlier spikes, at a third of the
sensor time.

### 4. Turret settle time proportional to the move
A flat 300 ms wait after every 7.5° step was replaced with
`40 ms + 0.5 ms per µs moved` (90 ms per step). That is still ~4× the time
a typical hobby servo (~0.17 s/60°) needs for the move, and larger moves
(aiming at the target) automatically get more time.
*Effect: settle time per step -70%.*

### 5. Sweep starts from the nearer end
The turret used to be sent back to a fixed home position after every
shot, then swing to +45° to start the next scan. Now it stays where it is
and the next sweep starts from whichever end is closer.

### 6. Refactor and robustness
- Targeting logic moved to `targeting.py` with no hardware imports, so the
  exact code that runs on the Pico is unit-tested and simulated on a PC.
- 13 unit tests (`python -m unittest discover tests`).
- Sensor timeouts are caught and skipped instead of crashing the loop.
- Each cycle prints scan time, scan-to-fire time and target angle/distance
  so real hardware runs can be compared against the simulation.
- Descriptive servo names (`turret_servo`, `latch_servo`, `arm_servo`).

The firing sequence itself (arm and latch timings) was deliberately left
unchanged because it depends on the mechanism and can't be validated
without hardware.
