from micropython import const

import gui.fonts.arial_50 as huge_font
import gui.fonts.freesans20 as small_font
from clockdata import ClockData
from drivers.display import Display
from gui.core.writer import Writer
from gui.widgets.textbox import Textbox
from rotary import Event
from DS1302 import DS1302

DEFAULT_TIMEOUT = 15000


class _State():

    def __init__(self, display: Display, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        self._clock_data = clock_data
        self._timeout_ms = timeout_ms
        self._timeout_state_name = timeout_state_name
        self._prev_display_data = ClockData()
        self._display = display
        self._wri_default = Writer(self._display, small_font, False)
        self._wri_time = Writer(self._display, huge_font, False)
        self._reset_timer_callback = lambda: None

    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._reset_timer_callback = reset_timer_callback


    def processEvent(self, event: Event) -> str:
        # Do nothing
        return self.__class__.__name__

    def prepareView(self) -> bool:
        self._display.clear()
        cd = self._clock_data
        wr = self._wri_default
        wr.set_textpos(self._display, 5, 13)
        wr.printstring("T1")
        wr.set_textpos(self._display, 5, 39)
        wr.printstring("T2")
        wr.set_textpos(self._display, 5, 70)
        wr.printstring("T3")
        self._display.hline(5, 26, 190, 1)
        self._display.vline(36, 9, 13, 1)
        self._display.vline(66, 9, 13, 1)
        self._display.vline(96, 9, 13, 1)

        has_changes = False
        if cd.battery is not None:
            wr.set_textpos(self._display, 5, 195 -
                           wr.stringlen(str(cd.battery)))
            wr.printstring(str(cd.battery))
            if self._prev_display_data.battery != cd.battery:
                has_changes = True
                self._prev_display_data.battery = cd.battery

        if cd.temperature is not None:
            wr.set_textpos(self._display, 175, 5)
            wr.printstring(cd.temperature)
            if self._prev_display_data.temperature != cd.temperature:
                has_changes = True
                self._prev_display_data.temperature = cd.temperature
            if cd.pressure is not None:
                wr.set_textpos(self._display, 175, 195 -
                               wr.stringlen(cd.pressure))
                wr.printstring(cd.pressure)
                if self._prev_display_data.pressure != cd.pressure:
                    has_changes = True
                    self._prev_display_data.pressure = cd.pressure
            self._display.hline(5, 173, 190, 1)

        return has_changes


class _TimeState(_State):
    def __init__(self, display: Display, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        super().__init__(display, clock_data, timeout_ms, timeout_state_name)
        self._hour_start_x = const(25)
        self._minutes_start_x = const(108)
        self._time_y = const(55)
        self._date_y = const(110)
        self._date_x_end = const(182)

    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        cd = self._clock_data
        t_writer = self._wri_time
        t_writer.set_textpos(self._display, 50, 91)
        t_writer.printstring(":")
        t_writer.set_textpos(self._display, self._time_y, self._hour_start_x)
        t_writer.printstring("{:02d}".format(cd.hour))
        t_writer.set_textpos(self._display, self._time_y,
                             self._minutes_start_x)
        t_writer.printstring("{:02d}".format(cd.minute))

        if self._prev_display_data.hour != cd.hour:
            has_changes = True
            self._prev_display_data.hour = cd.hour

        if self._prev_display_data.minute != cd.minute:
            has_changes = True
            self._prev_display_data.minute = cd.minute

        return has_changes






class Init(_State):
    def __init__(self, display: Display, clock_data: ClockData, rtc:DS1302) -> None:
        super().__init__(display, clock_data)

        self._rtc = rtc
        self._is_drawn = False


    def prepareView(self) -> bool:
        self._display.fill(0)
        self._display.text("Initialisierung", 20, 92)
        was_drawn = self._is_drawn
        self._is_drawn = True
        return not was_drawn


    def init(self) -> str:
        self._clock_data.is_init = self._clock_data.from_rtc(self._rtc.DateTime())
        if self._clock_data.is_init:
            return "Normal"
        return "SetHour10"







class Normal(_TimeState):
    def __init__(self, display: Display, clock_data: ClockData, rtc:DS1302) -> None:
        super().__init__(display, clock_data)

        self._rtc = rtc


    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        self._prev_display_data.day = -1 # Force display update at least once
        self._clock_data.from_rtc(self._rtc.DateTime())


    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        cd = self._clock_data
        date = cd.get_date_str()
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


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "SetHour10"
        if event.event_type == Event.EVENT_BTN_CLICK:
            return "Timer1Select"

        return self.__class__.__name__





