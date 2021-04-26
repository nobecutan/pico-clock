import machine
import micropython
import states
import states_edit
import utime
from clockdata import ClockData
from color_setup import ssd
from DS1302 import DS1302
from machine import Pin, I2C
from rotary import Event
from rotary_irq_rp2 import RotaryIRQ
from utime import sleep_ms
from bmp280 import BMP280

from clock import Clock

r = RotaryIRQ(pin_num_clk=22,
              pin_num_dt=26,
              pin_num_sw=27)

bme_bus = I2C(1, sda=Pin(6), scl=Pin(7))
bme = BMP280(bme_bus)

cd = ClockData()
sm = Clock(ssd, cd, bme)
rtc = DS1302(Pin(10), Pin(11), Pin(13))

sm.register_state(states.Init(ssd, cd, rtc))
sm.register_state(states.Normal(ssd, cd, rtc))

sm.register_state(states_edit.SetHour10(ssd, cd))
sm.register_state(states_edit.SetHour1(ssd, cd))
sm.register_state(states_edit.SetMinute10(ssd, cd))
sm.register_state(states_edit.SetMinute1(ssd, cd))
sm.register_state(states_edit.SetYear(ssd, cd))
sm.register_state(states_edit.SetMonth(ssd, cd))
sm.register_state(states_edit.SetDay(ssd, cd, rtc))


r.add_listener(sm.processEvent)


sm.init()
