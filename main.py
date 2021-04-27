import machine
import micropython
import states
import states_edit
import utime
from clockdata import ClockData
from color_setup import ssd
from DS1302 import DS1302
from machine import Pin, I2C, Timer
from rotary import Event
from rotary_irq_rp2 import RotaryIRQ
from utime import sleep_ms
from bmp280 import BMP280

from clock import Clock

r = RotaryIRQ(pin_num_clk=22,
              pin_num_dt=26,
              pin_num_sw=27)

motor_pin = Pin(0, Pin.OUT)
buzzer_pin = Pin(15, Pin.OUT)

bme_bus = I2C(1, sda=Pin(6), scl=Pin(7))
try:
    bme = BMP280(bme_bus)
except:
    print("No BMP280 (temp. sensor) found.")
    pass

cd = ClockData()
rtc = DS1302(Pin(10), Pin(11), Pin(13))
clock = Clock(ssd, cd, bme, rtc)
countdown_timer = Timer()

clock.register_state(states.Init(ssd, cd, rtc))
clock.register_state(states.Normal(ssd, cd, rtc))
clock.register_state(states.Timer1Select(ssd, cd))
clock.register_state(states.Timer2Select(ssd, cd))
clock.register_state(states.Timer3Select(ssd, cd))
clock.register_state(states.TimerBackSelect(ssd, cd))
clock.register_state(states.TimerStart(ssd, cd, countdown_timer, clock.processEvent))
clock.register_state(states.TimerAlarm(ssd, cd, countdown_timer, clock.processEvent, buzzer_pin, motor_pin))

clock.register_state(states_edit.SetHour10(ssd, cd))
clock.register_state(states_edit.SetHour1(ssd, cd))
clock.register_state(states_edit.SetMinute10(ssd, cd))
clock.register_state(states_edit.SetMinute1(ssd, cd))
clock.register_state(states_edit.SetYear(ssd, cd))
clock.register_state(states_edit.SetMonth(ssd, cd))
clock.register_state(states_edit.SetDay(ssd, cd, rtc))
clock.register_state(states_edit.TimerSetMinute10(ssd, cd))
clock.register_state(states_edit.TimerSetMinute1(ssd, cd))
clock.register_state(states_edit.TimerSetSecond10(ssd, cd))
clock.register_state(states_edit.TimerSetSecond1(ssd, cd, rtc))


r.add_listener(clock.processEvent)

#
clock.init()
