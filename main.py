"""Autonomous catapult control loop (MicroPython, Raspberry Pi Pico 2).

scan -> median filter -> cluster -> pick nearest -> aim -> fire -> repeat

See OPTIMISATION.md for what changed from the original hackathon version
and sim/ for the PC simulation used to choose these settings.
"""
from larger_servo import Servo
from mini_servo import MiniServo
from machine import Pin, I2C
from time import sleep_ms, ticks_ms, ticks_diff
import vl53l0x
import targeting

# --- Tunables (chosen with sim/simulate.py) ------------------------------
SAMPLES_PER_STEP = 7          # was 20; median of 7 still rejects outliers
DISCARD_PER_STEP = 1          # first reading after a move may be stale
SETTLE_BASE_MS = 40           # fixed settle time after every turret move
SETTLE_MS_PER_US = 0.5        # + time proportional to the move size
#   One 100 us scan step -> 90 ms (was a flat 300 ms).
#   Servo spec ~0.17 s/60 deg = ~0.21 ms per us, so this keeps >2x margin.

# --- Hardware ------------------------------------------------------------
latch_servo = MiniServo(pin=6)     # release / latch
turret_servo = MiniServo(pin=4)    # horizontal aim
arm_servo = Servo(pin=1)           # continuous-rotation launch arm

i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
tof = vl53l0x.VL53L0X(i2c)
tof.start()   # continuous back-to-back ranging; was start/stop per reading

turret_us = targeting.SCAN_START_US


def move_turret(pulse_us):
    """Move the turret and wait only as long as the move needs."""
    global turret_us
    pulse_us = int(pulse_us)
    delta = abs(pulse_us - turret_us)
    turret_servo.set_us(pulse_us)
    turret_us = pulse_us
    if delta:
        sleep_ms(int(SETTLE_BASE_MS + SETTLE_MS_PER_US * delta))


def read_samples(n):
    samples = []
    for _ in range(DISCARD_PER_STEP):
        tof.read()
    for _ in range(n):
        try:
            samples.append(tof.read())
        except Exception:      # sensor timeout: skip sample, keep scanning
            pass
    return samples


def horizontal_scan():
    """Sweep from whichever end is nearer, so there is no long return move."""
    angles = targeting.scan_angles()
    if abs(turret_us - angles[-1]) < abs(turret_us - angles[0]):
        angles.reverse()
    readings = []
    for pulse_us in angles:
        move_turret(pulse_us)
        reading = targeting.filter_reading(pulse_us, read_samples(SAMPLES_PER_STEP))
        if reading:
            readings.append(reading)
    return readings


def reset():
    latch_servo.move_90(direction="CCW")
    sleep_ms(500)
    # Turret is left where it is: the next scan starts from the nearer end.


def fire():
    arm_servo.turn_180(direction="CW")
    sleep_ms(500)
    latch_servo.move_90(direction="CW")
    sleep_ms(500)
    latch_servo.move_90(direction="CW")
    sleep_ms(500)
    arm_servo.turn_180(direction="CCW")
    sleep_ms(500)
    reset()


def main():
    reset()
    cycle = 0
    while True:
        t0 = ticks_ms()
        readings = horizontal_scan()
        t_scan = ticks_diff(ticks_ms(), t0)

        target = targeting.choose_target(targeting.find_clusters(readings))
        if target is None:
            print("cycle", cycle, "no target, scan", t_scan, "ms")
            continue

        pulse_us, distance_mm = target
        move_turret(pulse_us)
        t_aim = ticks_diff(ticks_ms(), t0)
        fire()
        t_cycle = ticks_diff(ticks_ms(), t0)

        print("cycle", cycle,
              "target %.1f deg %d mm" % (targeting.us_to_degrees(pulse_us), distance_mm),
              "scan", t_scan, "ms, scan-to-fire", t_aim, "ms, cycle", t_cycle, "ms")
        cycle += 1


main()
