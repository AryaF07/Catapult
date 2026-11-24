from machine import Pin, I2C
from time import sleep_ms
import vl53l0x

i2c = I2C(1, sda=Pin(2), scl=Pin(3), freq=400000)
tof = vl53l0x.VL53L0X(i2c)

while True:
    distance_mm = tof.ping()
    print(distance_mm, "mm")
    
