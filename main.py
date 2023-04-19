from machine import I2C, Pin, deepsleep
from micropython import schedule
from ds3231 import DS3231
from utime import localtime, sleep, ticks_diff, ticks_ms
from drivers.ssd1306 import SSD1306_I2C
from bmp280 import BMP280

from gui.core.writer import Writer

import gui.fonts.arial35 as font35
import gui.fonts.arial10 as font10
import gui.fonts.font6 as hdr_font
import gui.fonts.charging_14 as chrg_font


i2c = I2C(1, sda=Pin(2),scl=Pin(3))
# print(i2c.scan())

disp = SSD1306_I2C(128, 64, i2c)
disp.contrast(1) # minimum
hdr_writer = Writer(disp, hdr_font)
time_writer = Writer(disp, font35)
chrg_writer = Writer(disp,chrg_font)
t_writer = Writer(disp, font10)

rtc = DS3231(i2c)
bmp280 = BMP280(i2c)
# print(rtc.get_time())
# print(localtime())
# print(set_rtc(rtc.get_time()))
# print(localtime())

int_sqw = Pin(4)
rtc.int_sqw_setup(rtc.INT_SQW_OUT_INT)



global hh,mm,ss
hh=mm=ss=0

def update_time(pin:Pin):
    # ts = ticks_ms()
    global hh,mm,ss
    rtc.alarm1_if_reset()
    update_display = False
    ss += 1
    if ss >= 60:
        update_display = True
        ss = 0
        mm += 1
        if mm >= 60:
            mm = 0
            hh += 1
            if hh >= 24:
                hh = 0
                yy, MM, dd = rtc.get_time()[0:3]
                s = "{:02d}.{:02d}.{:02d}".format(dd, MM, yy%100)
                t_writer.set_textpos(disp, 54, 127-t_writer.stringlen(s))
                t_writer.printstring(s)

    # if not update_display: return

    if ss % 20 == 0: # update temp
        hdr_writer.set_textpos(disp, 3, 1)
        s = "{:0.1f}".format(bmp280.temperature)
        hdr_writer.printstring(s)
        chrg_writer.set_textpos(disp, 3, hdr_writer.stringlen(s)+1)
        chrg_writer.printstring("3")


    s = "{:02d}{}{:02d}".format(hh, ":" if ss % 2 == 0 else " ", mm)
    time_writer.set_textpos(disp,18,(128-time_writer.stringlen(s))//2)
    time_writer.printstring(s)
    disp.hline(0, 51, 44, 1)
    disp.vline(44, 52, 13, 1)
    # print(ticks_diff(ticks_ms(), ts))
    schedule(lambda t: disp.show(), None)

int_sqw.irq(update_time, Pin.IRQ_FALLING)

# rtc.alarm1_set(rtc.AL1_SECONDS_MATCH)
rtc.alarm1_set(rtc.AL1_ONCE_PER_SECOND)
rtc.alarm1_enable()

yy, MM, dd, hh, mm, ss = rtc.get_time()[0:6]
s = "{:02d}{}{:02d}".format(hh, ":" if ss % 2 == 0 else " ", mm)
time_writer.set_textpos(disp, 18, (128-time_writer.stringlen(s))//2)
time_writer.printstring(s)

hdr_writer.set_textpos(disp, 3, 1)
s = "{:0.1f}".format(bmp280.temperature)
hdr_writer.printstring(s)
chrg_writer.set_textpos(disp, 3, hdr_writer.stringlen(s)+1)
chrg_writer.printstring("3")
chrg_writer.set_textpos(disp, 3, 108)
chrg_writer.printstring("4")

t_writer.set_textpos(disp, 54, 1)
t_writer.printstring("T1 T2 T3")
disp.hline(0, 51, 44, 1)
disp.vline(13, 53, 12, 1)
disp.vline(29, 53, 12, 1)
disp.vline(44, 52, 13, 1)


s = "{:02d}.{:02d}.{:02d}".format(dd, MM, yy%100)
t_writer.set_textpos(disp, 54, 127-t_writer.stringlen(s))
t_writer.printstring(s)

schedule(lambda t: disp.show(), None)
#deepsleep()
