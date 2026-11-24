from machine import Pin, PWM
from time import sleep_ms


class MiniServo:
    def __init__(
        self,
        pin,
        freq=50,
        us_0=425,
        us_90=1350,
        us_155=2000,
        us_180=2300,
        us_225=2600
    ):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)

        self.US_0 = us_0
        self.US_90 = us_90
        self.US_155 = us_155
        self.US_180 = us_180
        self.US_225 = us_225

    def set_us(self, us):
        self.pwm.duty_ns(int(us * 1000))


    def move_90(self, direction="CW"):
        if direction == "CW":
            self.set_us(self.US_0)
        elif direction == "CCW":
            self.set_us(self.US_90)
           
            
           

    def move_45_and_back(self):
        sleep_ms(500)
        self.set_us(self.US_180)
        sleep_ms(500)
        self.set_us(self.US_225)
        sleep_ms(500)
        self.set_us(self.US_155)
        sleep_ms(500)
        self.set_us(self.US_180)
        


    def deinit(self):
        self.pwm.deinit()