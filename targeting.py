"""Hardware-independent targeting logic.

Pure Python with no `machine` imports, so the same code runs on the
Raspberry Pi Pico (MicroPython) and on a PC (CPython) for simulation
and unit testing.

A reading is a tuple (pulse_us, distance_mm), where pulse_us is the
turret servo pulse width at which the reading was taken.
"""

# --- Scan geometry -------------------------------------------------------
SCAN_START_US = 3000          # +45 degrees
SCAN_END_US = 1800            # -45 degrees
SCAN_STEP_US = 100            # ~7.5 degrees per step
DEG_PER_US = 90 / (SCAN_START_US - SCAN_END_US)

# --- Filtering -----------------------------------------------------------
MIN_VALID_MM = 25             # below this the VL53L0X is unreliable
MAX_VALID_MM = 1400           # beyond this treat as "no object"

# --- Clustering ----------------------------------------------------------
MAX_ANGLE_GAP_US = SCAN_STEP_US   # neighbouring scan steps only
MAX_DISTANCE_JUMP_MM = 150        # depth jump that separates two objects


def scan_angles(start=SCAN_START_US, end=SCAN_END_US, step=SCAN_STEP_US):
    """Pulse widths visited by one sweep (inclusive of both ends)."""
    if start >= end:
        return list(range(start, end - 1, -step))
    return list(range(start, end + 1, step))


def median(values):
    """Median of a non-empty list (upper median for even lengths)."""
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def filter_reading(pulse_us, samples):
    """Median-filter one angle's samples; return a reading or None."""
    if not samples:
        return None
    distance = median(samples)
    if MIN_VALID_MM < distance < MAX_VALID_MM:
        return (pulse_us, distance)
    return None


def find_clusters(readings,
                  max_angle_gap=MAX_ANGLE_GAP_US,
                  max_distance_jump=MAX_DISTANCE_JUMP_MM):
    """Group readings into objects.

    Readings are sorted by angle first, so the result does not depend on
    sweep direction. A new cluster starts when there is a gap in angle
    (an empty/filtered step) OR a jump in depth (two objects side by side
    at different distances, which the original angle-only rule merged).
    """
    clusters = []
    current = []
    for reading in sorted(readings):
        if current:
            prev_angle, prev_dist = current[-1]
            angle_gap = abs(reading[0] - prev_angle)
            depth_jump = abs(reading[1] - prev_dist)
            if angle_gap > max_angle_gap or depth_jump > max_distance_jump:
                clusters.append(current)
                current = []
        current.append(reading)
    if current:
        clusters.append(current)
    return clusters


def cluster_centre(cluster):
    """(centre pulse_us, median distance_mm) of a cluster."""
    angles = [r[0] for r in cluster]
    centre = (min(angles) + max(angles)) / 2
    return (centre, median([r[1] for r in cluster]))


def choose_target(clusters):
    """Return (pulse_us, distance_mm) of the nearest cluster, or None."""
    best = None
    for cluster in clusters:
        candidate = cluster_centre(cluster)
        if best is None or candidate[1] < best[1]:
            best = candidate
    return best


def us_to_degrees(pulse_us):
    """Convert a turret pulse width to degrees from centre (+ = left)."""
    centre = (SCAN_START_US + SCAN_END_US) / 2
    return (pulse_us - centre) * DEG_PER_US
