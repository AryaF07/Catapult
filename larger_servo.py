from machine import Pin, PWM
from time import sleep_ms


class Servo:
    def __init__(self, pin):
        self.servo = PWM(Pin(pin))
        self.servo.freq(50)

        self.STOP_US = 1500
        self.CW_US = 1000
        self.CCW_US = 2000
        self.FULL_TURN_MS = 2000
        self.HALF_TURN_MS = self.FULL_TURN_MS // 2

    def set_us(self, us):
        self.servo.duty_ns(int(us * 1000))

    def stop_servo(self):
        self.set_us(self.STOP_US)

    def turn_180(self, direction="CW"):
        
        if direction == "CW":
            self.set_us(self.CW_US)
            sleep_ms(self.HALF_TURN_MS)
            self.stop_servo()
            sleep_ms(500)
        elif direction == "CCW":
            self.set_us(self.CCW_US)
            sleep_ms(self.HALF_TURN_MS)
            self.stop_servo()

    # def turn_360_and_back(self):
    #     self.set_us(self.CW_US)
    #     sleep_ms(self.FULL_TURN_MS)
    #     self.stop_servo()
    #     sleep_ms(500)

    #     self.set_us(self.CCW_US)
    #     sleep_ms(self.FULL_TURN_MS)
    #     self.stop_servo()