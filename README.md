# Sensor-Guided Autonomous Catapult

Built at **Hack-A-Bot 2026** (24-hour team hackathon). A Raspberry Pi Pico 2 running MicroPython scans its surroundings with a time-of-flight distance sensor, picks the nearest object, turns to face it and launches a projectile — with no human input.

## How it works

1. **Scan** – a positional servo sweeps the turret through 13 positions across a ~90° arc (PWM 3000 → 1800 µs in 100 µs steps), starting from whichever end is nearer.
2. **Measure** – at each position the VL53L0X ToF sensor (I2C @ 400 kHz, continuous mode) takes 7 readings; the **median** is kept to reject noise and outliers.
3. **Filter** – readings outside the 25–1400 mm valid range are discarded.
4. **Cluster** – adjacent valid angles are grouped into objects, splitting on gaps in angle or jumps in depth.
5. **Select** – each cluster's centre angle and median distance are computed, and the **closest** object is chosen as the target.
6. **Aim & fire** – the turret rotates to the target angle and a servo-driven sequence (continuous-rotation winding servo + release/latch servo) launches the projectile, then resets to a known home position and repeats.

## Hardware

| Component | Role | Pico pin |
|---|---|---|
| Raspberry Pi Pico 2 | Controller (MicroPython) | – |
| VL53L0X time-of-flight sensor | Distance measurement | I2C1: SDA GP2, SCL GP3 |
| Positional servo | Horizontal turret aim | GP4 |
| Mini servo | Release / latch | GP6 |
| Continuous-rotation servo | Launch arm drive | GP1 |

## Files

| File | Purpose |
|---|---|
| `main.py` | Control loop: scan → filter → cluster → target → aim → fire |
| `targeting.py` | Hardware-independent filtering, clustering and target selection |
| `sim/simulate.py` | PC Monte Carlo simulation comparing original vs optimised code |
| `sim/baseline.py` | Original hackathon targeting logic, kept for comparison |
| `tests/` | Unit tests for `targeting.py` |
| `mini_servo.py` | Positional servo driver with calibrated pulse widths |
| `larger_servo.py` | Continuous-rotation servo driver (timed 180° turns) |
| `vl53l0x.py` | VL53L0X ToF sensor driver (third-party MicroPython driver) |
| `scan.py` | Standalone sensor test – prints distance in mm |
| `blink.py` | Board sanity check (onboard LED) |
| `stepper.py` | Placeholder for planned stepper-based base rotation |

## Running

Flash MicroPython onto the Pico 2, upload all `.py` files (e.g. with the MicroPico VS Code extension), then run `main.py` (or save it to the board so it runs on boot).

## Optimisation & simulation

After the hackathon the code was optimised and a PC simulator was added (no hardware needed). Simulated results: target selection accuracy **89% → 97.5%**, scan time **18.5 s → 4.6 s**, full cycle **24 s → 9.9 s**. See [OPTIMISATION.md](OPTIMISATION.md) and [sim/results.md](sim/results.md).

```
python sim/simulate.py
python -m unittest discover tests
```

Upload `targeting.py` to the Pico alongside the other `.py` files (not `sim/` or `tests/`).

## Planned improvements

- Vertical scan to find a target's centre height
- Distance-based launch power / elevation
- Stepper motor base for finer angular resolution
