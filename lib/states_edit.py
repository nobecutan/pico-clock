import utime
from machine import Pin
from micropython import const
import micropython

from clockdata import ClockData
from drivers.display import Display
from gui.widgets.textbox import Textbox
from rotary import Event
from DS1302 import DS1302

import states


motor = Pin(0, Pin.OUT)

def _do_buzz(time_ms:int) -> None:
    motor.on()
    utime.sleep_ms(time_ms)
    motor.off()

def buzz(time_ms:int = 125) -> None:
    micropython.schedule(_do_buzz, time_ms)

class _EditTimeState(states._TimeState):
    def __init__(self, display: Display, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        super().__init__(display, clock_data, timeout_ms, timeout_state_name)
        self._h10 = -1
        self._h1 = -1
        self._m10 = -1
        self._m1 = -1
        self._prev_h10 = -1
        self._prev_h1 = -1
        self._prev_m10 = -1
        self._prev_m1 = -1

        self._header_height = self._time_y - 1
        self._footer_y = self._date_y + self._wri_default.char_height + 1
        self._footer_height = self._display.height - self._footer_y

    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        cd = self._clock_data
        self._h10 = cd.hour // 10
        self._h1 = cd.hour % 10
        self._m10 = cd.minute // 10
        self._m1 = cd.minute % 10

        self._prev_display_data.day = -1 # Force view update at least once


    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        # Clear header and footer for edit
        self._display.fill_rect(0, 0, self._display.width, self._header_height, 0)
        self._display.fill_rect(0, self._footer_y, self._display.width, self._footer_height, 0)

        cd = self._clock_data
        date = "{:04d}-{:02d}-{:02d}".format(cd.year, cd.month, cd.day)
        wr = self._wri_default
        wr.set_textpos(self._display, self._date_y, self._date_x_end - wr.stringlen(date))
        wr.printstring(date)
        if self._prev_display_data.year != cd.year:
            self._prev_display_data.year = cd.year
            has_changes = True
        if self._prev_display_data.month != cd.month:
            self._prev_display_data.month = cd.month
            has_changes = True
        if self._prev_display_data.day != cd.day:
            self._prev_display_data.day = cd.day
            has_changes = True

        return has_changes










class SetHour10(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        tb = Textbox(self._wri_time, self._time_y, self._hour_start_x,
                     self._wri_time.stringlen(str(self._h10)), 1)
        tb.append(str(self._h10))
        if self._prev_h10 != self._h10:
            self._prev_h10 = self._h10
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_ROT_DEC:
            self._h10 -= 1
            if self._h10 < 0:
                self._h10 = 0
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            self._h10 += 1
            if self._h10 > 2:
                self._h10 = 2
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._clock_data.hour = self._h10 * 10 + self._h1
            if self._clock_data.hour > 23:
                self._clock_data.hour = 23
            self._reset_timer_callback()
            buzz()
            return "SetHour1"

        return self.__class__.__name__


class SetHour1(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        tb = Textbox(self._wri_time, self._time_y, self._hour_start_x +
                     self._wri_time.stringlen(str(self._h10)),
                     self._wri_time.stringlen(str(self._h1)), 1)
        tb.append(str(self._h1))
        if self._prev_h1 != self._h1:
            self._prev_h1 = self._h1
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_ROT_DEC:
            self._h1 -= 1
            if self._h1 < 0:
                self._h1 = 0
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            self._h1 += 1
            h_max = 3 if self._h10 == 2 else 9
            if self._h1 > h_max:
                self._h1 = h_max
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._clock_data.hour = self._h10 * 10 + self._h1

            self._reset_timer_callback()
            buzz()
            return "SetMinute10"

        return self.__class__.__name__


class SetMinute10(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        tb = Textbox(self._wri_time, self._time_y, self._minutes_start_x,
                     self._wri_time.stringlen(str(self._m10)), 1)
        tb.append(str(self._m10))
        if self._prev_m10 != self._m10:
            self._prev_m10 = self._m10
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_ROT_DEC:
            self._m10 -= 1
            if self._m10 < 0:
                self._m10 = 0
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            self._m10 += 1
            if self._m10 > 5:
                self._m10 = 5
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._clock_data.minute = self._m10 * 10 + self._m1

            self._reset_timer_callback()
            buzz()
            return "SetMinute1"

        return self.__class__.__name__






class SetMinute1(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)

        self._m10 = clock_data.minute // 10
        self._m1 = clock_data.minute % 10


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        tb = Textbox(self._wri_time, self._time_y, self._minutes_start_x +
                     self._wri_time.stringlen(str(self._m10)),
                     self._wri_time.stringlen(str(self._m1)), 1)
        tb.append(str(self._m1))
        if self._prev_m1 != self._m1:
            self._prev_m1 = self._m1
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_ROT_DEC:
            self._m1 -= 1
            if self._m1 < 0:
                self._m1 = 0
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            self._m1 += 1
            if self._m1 > 9:
                self._m1 = 9
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._clock_data.minute = self._m10 * 10 + self._m1

            self._reset_timer_callback()
            buzz()
            return "SetYear"

        return self.__class__.__name__








class SetYear(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        cd = self._clock_data
        date = "{:04d}-{:02d}-{:02d}".format(cd.year, cd.month, cd.day)
        part = "{:04d}".format(cd.year)
        wr = self._wri_default
        start_x = self._date_x_end - wr.stringlen(date)

        tb = Textbox(wr, self._date_y, start_x, wr.stringlen(part), 1)
        tb.append(part)
        if self._prev_display_data.year != cd.year:
            self._prev_display_data.year = cd.year
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        cd = self._clock_data
        if event.event_type == Event.EVENT_ROT_DEC:
            cd.year -= 1
            if cd.year < 2020:
                cd.year = 2020
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            cd.year += 1
            if cd.year > 2096:
                cd.year = 2096
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._reset_timer_callback()
            buzz()
            return "SetMonth"

        return self.__class__.__name__






class SetMonth(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        cd = self._clock_data
        sub_date = "{:02d}-{:02d}".format(cd.month, cd.day)
        part = "{:02d}".format(cd.month)
        wr = self._wri_default
        start_x = self._date_x_end - wr.stringlen(sub_date)

        tb = Textbox(wr, self._date_y, start_x, wr.stringlen(part), 1)
        tb.append(part)
        if self._prev_display_data.month != cd.month:
            self._prev_display_data.month = cd.month
            has_changes = True
        return has_changes


    def processEvent(self, event: Event) -> str:
        cd = self._clock_data
        if event.event_type == Event.EVENT_ROT_DEC:
            cd.month -= 1
            if cd.month < 1:
                cd.month = 1
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            cd.month += 1
            if cd.month > 12:
                cd.month = 12
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            self._reset_timer_callback()
            buzz()
            return "SetDay"

        return self.__class__.__name__






class SetDay(_EditTimeState):
    def __init__(self, display: Display, clock_data: ClockData, rtc: DS1302) -> None:
        if clock_data.is_init:
            super().__init__(display, clock_data, states.DEFAULT_TIMEOUT, "Normal")
        else:
            super().__init__(display, clock_data)

        self._rtc = rtc

    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        self._d_max = self._max_day()


    def prepareView(self) -> bool:
        has_changes = super().prepareView()
        cd = self._clock_data
        sub_date = "{:02d}".format(cd.day)
        part = sub_date
        wr = self._wri_default
        start_x = self._date_x_end - wr.stringlen(sub_date)

        tb = Textbox(wr, self._date_y, start_x, wr.stringlen(part), 1)
        tb.append(part)
        if self._prev_display_data.day != cd.day:
            self._prev_display_data.day = cd.day
            has_changes = True
        return has_changes


    def _is_leap_year(self) -> bool:
        cd = self._clock_data
        if cd.year % 400:
            return True
        if cd.year % 100:
            return False
        return cd.year % 4 == 0


    def _max_day(self) -> int:
        cd = self._clock_data
        if cd.month in (1,3,5,7,8,10,12):
            return 31
        if cd.month in (4,6,9,11):
            return 30
        return 29 if self._is_leap_year() else 28


    def processEvent(self, event: Event) -> str:
        cd = self._clock_data
        if event.event_type == Event.EVENT_ROT_DEC:
            cd.day -= 1
            if cd.day < 1:
                cd.day = 1
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_ROT_INC:
            cd.day += 1
            if cd.day > self._d_max:
                cd.day = self._d_max
            else:
                buzz()
            self._reset_timer_callback()
        elif event.event_type == Event.EVENT_BTN_CLICK:
            cd.calc_weekday()
            cd.is_init = True

            self._reset_timer_callback()
            self._rtc.DateTime((cd.year, cd.month, cd.day, cd.weekday, cd.hour, cd.minute, 0))
            buzz()
            return "Normal"

        return self.__class__.__name__
