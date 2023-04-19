import machine
import micropython
import states
import states_edit
import utime
from clockdata import ClockData
from clock_view_128x64 import ClockView128x64 as ClockView
# from color_setup import display
from drivers.ssd1306 import SSD1306_I2C
from ds3231 import DS3231
from at24c32n import AT24C32N
from machine import Pin, I2C, Timer
from rotary import Event
from rotary_irq_rp2 import RotaryIRQ
from utime import sleep_ms
from bmp280 import BMP280

from clock import Clock

r = RotaryIRQ(pin_num_clk=16,
              pin_num_dt=17,
              pin_num_sw=18)

motor_pin = Pin(19, Pin.OUT)
buzzer_pin = Pin(14, Pin.OUT)

i2c = I2C(1, sda=Pin(2), scl=Pin(3))
try:
    bmp280 = BMP280(i2c)
except:
    print("No BMP280 (temp. sensor) found.")
    bmp280 = None

display = SSD1306_I2C(128, 64, i2c)
clock_view = ClockView(display)
cd = ClockData()
rtc = DS3231(i2c)
eeprom = AT24C32N(i2c)
clock = Clock(display, clock_view, cd, bmp280, rtc)
countdown_timer = Timer()

clock.register_state(states.Init(clock_view, cd, rtc))
clock.register_state(states.Normal(display, cd, rtc))
# clock.register_state(states.Timer1Select(display, cd))
# clock.register_state(states.Timer2Select(display, cd))
# clock.register_state(states.Timer3Select(display, cd))
# clock.register_state(states.TimerBackSelect(display, cd))
# clock.register_state(states.TimerStart(display, cd, countdown_timer, clock.processEvent))
# clock.register_state(states.TimerAlarm(display, cd, countdown_timer, clock.processEvent, buzzer_pin, motor_pin))

# clock.register_state(states_edit.SetHour10(display, cd))
# clock.register_state(states_edit.SetHour1(display, cd))
# clock.register_state(states_edit.SetMinute10(display, cd))
# clock.register_state(states_edit.SetMinute1(display, cd))
# clock.register_state(states_edit.SetYear(display, cd))
# clock.register_state(states_edit.SetMonth(display, cd))
# clock.register_state(states_edit.SetDay(display, cd, rtc))
# clock.register_state(states_edit.TimerSetMinute10(display, cd))
# clock.register_state(states_edit.TimerSetMinute1(display, cd))
# clock.register_state(states_edit.TimerSetSecond10(display, cd))
# clock.register_state(states_edit.TimerSetSecond1(display, cd, rtc))


r.add_listener(clock.processEvent)

#
clock.init()
