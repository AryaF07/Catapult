"""Monte Carlo simulation of the catapult's scan-and-target pipeline.

Runs on a normal PC (no hardware). It compares the original hackathon
code (sim/baseline.py) with the optimised code (targeting.py) on the same
randomly generated scenes, and estimates cycle time from the delays in
the code plus a simple sensor/servo timing model.

    python sim/simulate.py            # prints tables, writes sim/results.md

All numbers are SIMULATED under the assumptions listed in ASSUMPTIONS.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import targeting as opt   # noqa: E402
import baseline as base   # noqa: E402

SEED = 2026
TRIALS = 10000

ASSUMPTIONS = {
    "sensor_sigma_pct": 3.0,      # 1-sigma ranging noise, % of distance
    "outlier_rate": 0.05,         # chance a sample is a random spike
    "harsh_outlier_rate": 0.15,   # stress test
    "no_target_mm": 8190,         # VL53L0X out-of-range value
    "timing_budget_ms": 33,       # driver default measurement time
    "i2c_start_stop_ms": 3,       # ~15 extra register writes per ping()
    "servo_ms_per_us": 0.21,      # ~0.17 s / 60 deg servo spec
    "empty_scene_rate": 0.10,     # share of scenes with nothing in range
}

ANGLES_DESC = opt.scan_angles()          # 3000 -> 1800, 13 steps
HALF_STEP = opt.SCAN_STEP_US / 2


# --- Scene & sensor model -------------------------------------------------
def random_scene(rng, side_by_side=False):
    """List of objects (lo_us, hi_us, distance_mm)."""
    if side_by_side:
        # Two touching objects at clearly different depths.
        w1 = rng.choice([100, 200, 300])
        w2 = rng.choice([100, 200, 300])
        lo = rng.randrange(opt.SCAN_END_US, opt.SCAN_START_US - w1 - w2 + 1, 50)
        near = rng.uniform(150, 900)
        far = near + rng.uniform(200, 500)
        a, b = (near, far) if rng.random() < 0.5 else (far, near)
        return [(lo, lo + w1, a), (lo + w1, lo + w1 + w2, b)]
    if rng.random() < ASSUMPTIONS["empty_scene_rate"]:
        return []
    objs = []
    for _ in range(rng.randint(1, 3)):
        width = rng.choice([100, 150, 200, 300, 400])
        lo = rng.uniform(opt.SCAN_END_US, opt.SCAN_START_US - width)
        objs.append((lo, lo + width, rng.uniform(150, 1300)))
    return objs


def true_distance(scene, pulse_us, rng):
    """Nearest object the beam hits at this angle (None = nothing)."""
    hits = []
    for lo, hi, d in scene:
        if lo <= pulse_us <= hi:
            hits.append(d)
        elif lo - HALF_STEP <= pulse_us <= hi + HALF_STEP and rng.random() < 0.5:
            hits.append(d)          # beam only partly on the object's edge
    return min(hits) if hits else None


def sample(d, rng, outlier_rate):
    if rng.random() < outlier_rate:
        return int(rng.uniform(0, ASSUMPTIONS["no_target_mm"]))
    if d is None:
        return ASSUMPTIONS["no_target_mm"]
    return max(0, int(rng.gauss(d, d * ASSUMPTIONS["sensor_sigma_pct"] / 100)))


def scan(scene, rng, n, filter_fn, outlier_rate):
    readings = []
    for pulse_us in ANGLES_DESC:
        samples = [sample(true_distance(scene, pulse_us, rng), rng, outlier_rate)
                   for _ in range(n)]
        r = filter_fn(pulse_us, samples)
        if r:
            readings.append(r)
    return readings


def nearest_object(scene):
    """Ground-truth target: the nearest object that the scan can see."""
    visible = [o for o in scene
               if any(o[0] <= a <= o[1] for a in ANGLES_DESC)]
    return min(visible, key=lambda o: o[2]) if visible else None


# --- Evaluation -----------------------------------------------------------
PIPELINES = {
    "baseline": (base.filter_reading, base.find_clusters, base.choose_target),
    "optimised": (opt.filter_reading, opt.find_clusters, opt.choose_target),
}


def evaluate(pipeline, n, outlier_rate=None, side_by_side=False,
             trials=TRIALS, seed=SEED):
    if outlier_rate is None:
        outlier_rate = ASSUMPTIONS["outlier_rate"]
    filt, cluster, choose = PIPELINES[pipeline]
    rng = random.Random(seed)          # same scenes for every config
    hits = total = 0
    aim_err, dist_err = [], []
    empty = false_alarm = 0
    for _ in range(trials):
        scene = random_scene(rng, side_by_side)
        truth = nearest_object(scene)
        target = choose(cluster(scan(scene, rng, n, filt, outlier_rate)))
        if truth is None:
            empty += 1
            false_alarm += target is not None
            continue
        total += 1
        if target is None:
            continue
        lo, hi, d = truth
        aim_err.append(abs(target[0] - (lo + hi) / 2) * opt.DEG_PER_US)
        if lo - HALF_STEP <= target[0] <= hi + HALF_STEP:
            hits += 1
            dist_err.append(abs(target[1] - d) / d * 100)
    return {
        "accuracy": 100 * hits / total,
        "aim_err_deg": sum(aim_err) / len(aim_err),
        "dist_err_pct": sum(dist_err) / len(dist_err),
        "false_alarm": 100 * false_alarm / empty if empty else 0.0,
    }


# --- Timing model (derived from the delays in the code) -------------------
FIRE_BASELINE_MS = 500 + 1500 + 500 + 500 + 500 + 1000 + 500 + 500
FIRE_OPTIMISED_MS = 1500 + 500 + 500 + 500 + 1000 + 500 + 500


def scan_ms_baseline(n=20):
    per_reading = (ASSUMPTIONS["timing_budget_ms"]
                   + ASSUMPTIONS["i2c_start_stop_ms"] + 20)
    return len(ANGLES_DESC) * (300 + n * per_reading)


def scan_ms_optimised(n, discard=1, base_ms=40, per_us=0.5):
    settle = base_ms + per_us * opt.SCAN_STEP_US
    first_settle = base_ms + per_us * 0   # sweep starts at nearer end
    reads = (n + discard) * ASSUMPTIONS["timing_budget_ms"]
    return first_settle + (len(ANGLES_DESC) - 1) * settle + len(ANGLES_DESC) * reads


def aim_ms_optimised(rng_trials=10000, seed=SEED):
    """Average turret settle from end of sweep to a random target angle."""
    rng = random.Random(seed)
    tot = 0
    for _ in range(rng_trials):
        delta = abs(rng.choice(ANGLES_DESC) - rng.choice([ANGLES_DESC[0], ANGLES_DESC[-1]]))
        tot += 40 + 0.5 * delta if delta else 0
    return tot / rng_trials


def min_servo_margin():
    """Settle time / physical move time for one scan step."""
    need = ASSUMPTIONS["servo_ms_per_us"] * opt.SCAN_STEP_US
    return (40 + 0.5 * opt.SCAN_STEP_US) / need


# --- Report ---------------------------------------------------------------
def main():
    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("# Simulation results")
    out()
    out("Generated by `python sim/simulate.py` (seed %d, %d scenes per row). "
        "All figures are simulated, not measured on hardware." % (SEED, TRIALS))
    out()
    out("Assumptions: " + ", ".join("%s=%s" % kv for kv in ASSUMPTIONS.items()))
    out()

    out("## 1. Samples per step (optimised pipeline, 5% outliers)")
    out()
    out("| Samples | Scan time (s) | Target accuracy | Aim error (deg) | Distance error | False targets |")
    out("|---|---|---|---|---|---|")
    sweep = {}
    for n in (1, 3, 5, 7, 9, 15, 20):
        r = evaluate("optimised", n)
        sweep[n] = r
        out("| %d | %.2f | %.1f%% | %.2f | %.2f%% | %.1f%% |" % (
            n, scan_ms_optimised(n) / 1000, r["accuracy"], r["aim_err_deg"],
            r["dist_err_pct"], r["false_alarm"]))
    out()

    out("## 2. Baseline vs optimised")
    out()
    b = evaluate("baseline", 20)
    o = evaluate("optimised", 7)
    bh = evaluate("baseline", 20, ASSUMPTIONS["harsh_outlier_rate"])
    oh = evaluate("optimised", 7, ASSUMPTIONS["harsh_outlier_rate"])
    bs = evaluate("baseline", 20, side_by_side=True)
    os_ = evaluate("optimised", 7, side_by_side=True)
    out("| Scenario | Baseline (20 samples) | Optimised (7 samples) |")
    out("|---|---|---|")
    out("| Random scenes, 5%% outliers | %.1f%% | %.1f%% |" % (b["accuracy"], o["accuracy"]))
    out("| Random scenes, 15%% outliers | %.1f%% | %.1f%% |" % (bh["accuracy"], oh["accuracy"]))
    out("| Two objects side by side | %.1f%% | %.1f%% |" % (bs["accuracy"], os_["accuracy"]))
    out("| Mean aim error (random) | %.2f deg | %.2f deg |" % (b["aim_err_deg"], o["aim_err_deg"]))
    out("| Mean aim error (side by side) | %.2f deg | %.2f deg |" % (bs["aim_err_deg"], os_["aim_err_deg"]))
    out("| Distance error (random) | %.2f%% | %.2f%% |" % (b["dist_err_pct"], o["dist_err_pct"]))
    out("| False targets on empty scenes | %.1f%% | %.1f%% |" % (b["false_alarm"], o["false_alarm"]))
    out()

    out("## 3. Timing (from code delays + sensor timing model)")
    out()
    sb, so = scan_ms_baseline(), scan_ms_optimised(7)
    aim = aim_ms_optimised()
    cb = sb + FIRE_BASELINE_MS
    co = so + aim + FIRE_OPTIMISED_MS
    out("| Stage | Baseline | Optimised | Change |")
    out("|---|---|---|---|")
    out("| Sensor readings per scan | %d | %d (+%d discarded) | -%.0f%% |" % (
        13 * 20, 13 * 7, 13, 100 * (1 - 13 * 8 / 260)))
    out("| Per-reading time | %d ms | %d ms | -%.0f%% |" % (
        ASSUMPTIONS["timing_budget_ms"] + ASSUMPTIONS["i2c_start_stop_ms"] + 20,
        ASSUMPTIONS["timing_budget_ms"],
        100 * (1 - 33 / 56)))
    out("| Turret settle per step | 300 ms | 90 ms | -70% |")
    out("| Scan | %.2f s | %.2f s | %.1fx faster |" % (sb / 1000, so / 1000, sb / so))
    out("| Aim + fire + reset | %.2f s | %.2f s | |" % (
        FIRE_BASELINE_MS / 1000, (aim + FIRE_OPTIMISED_MS) / 1000))
    out("| Full cycle | %.2f s | %.2f s | %.0f%% shorter |" % (
        cb / 1000, co / 1000, 100 * (1 - co / cb)))
    out("| Targets per minute | %.1f | %.1f | %.1fx |" % (
        60000 / cb, 60000 / co, cb / co))
    out()
    out("Servo settle margin per step: %.1fx the modelled move time." % min_servo_margin())

    with open(os.path.join(HERE, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
