from utime import sleep, ticks_diff, ticks_ms
from machine import Pin, Timer
from micropython import const, schedule
from clock_view import ClockView

from clockdata import ClockData
from rotary import Event
from DS1302 import DS1302

DEFAULT_TIMEOUT = 15000


class _State():

    def __init__(self, clock_view: ClockView, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        self._clock_view = clock_view
        self._clock_data = clock_data
        self._timeout_ms = timeout_ms
        self._timeout_state_name = timeout_state_name
        self._reset_timer_callback = lambda: None



    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._reset_timer_callback = reset_timer_callback


    def handleTimeout(self) -> None:
        pass


    def processEvent(self, event: Event) -> str:
        # Do nothing
        return self.__class__.__name__


    def prepareView(self) -> bool:
        return self._clock_view.draw_background(self._clock_data)




class _TimeState(_State):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        super().__init__(clock_view, clock_data, timeout_ms, timeout_state_name)


    def prepareView(self) -> bool:
        return self._clock_view.draw_time(self._clock_data)







class _CountdownState(_TimeState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, timeout_ms: int = 0, timeout_state_name: str = None) -> None:
        super().__init__(clock_view, clock_data, timeout_ms, timeout_state_name)
        self._timer_min = 0
        self._timer_sec = 0
        self._prev_timer_min = -1
        self._prev_timer_sec = -1
        self._is_timer_init = False


    def _get_timer_val(self) -> Tuple[int, int]:
        cd = self._clock_data
        if cd.active_timer_selected == 1:
            return (cd.t1_duration // 60, cd.t1_duration % 60)
        elif cd.active_timer_selected == 2:
            return (cd.t2_duration // 60, cd.t2_duration % 60)
        elif cd.active_timer_selected == 3:
            return (cd.t3_duration // 60, cd.t2_duration % 60)
        else:
            raise IndexError("active timer {:d} unsupported".format(cd.active_timer_selected))


    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._timer_min, self._timer_sec = self._get_timer_val()

        super().initState(reset_timer_callback)


    def prepareView(self) -> bool:
        return self._clock_view.draw_countdown(self._clock_data)







class Init(_State):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, rtc:DS1302) -> None:
        super().__init__(clock_view, clock_data)

        self._rtc = rtc
        self._is_drawn = False


    def prepareView(self) -> bool:
        was_drawn = self._is_drawn
        if not was_drawn:
            self._clock_view.draw_init_state(self._clock_data)

        self._is_drawn = True
        return not was_drawn


    def init(self) -> str:
        cd = self._clock_data
        cd.is_init = cd.from_rtc(self._rtc.DateTime())

        for offset in (0,3,6):
            d = 0
            for b in range(3):
                d |= self._rtc.ram(offset + b) << (8 * b)

            if d >= 0 and d < 3600:
                if offset == 0:
                    cd.t1_duration = d
                elif offset == 3:
                    cd.t2_duration = d
                elif offset == 6:
                    cd.t3_duration = d
                else:
                    raise IndexError("Unexpected offset {:d}".format(offset))
            else:
                for b in range(3):
                    self._rtc.ram(offset + b, 0)

        if cd.is_init:
            return "Normal"
        return "SetHour10"







class Normal(_TimeState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, rtc:DS1302) -> None:
        super().__init__(clock_view, clock_data)

        self._rtc = rtc


    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        self._clock_view.force_update() # Force display update at least once
        self._clock_data.from_rtc(self._rtc.DateTime())


    def prepareView(self) -> bool:
        return self._clock_view.draw_normal_state(self._clock_data)


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "SetHour10"
        if event.event_type == Event.EVENT_BTN_CLICK:
            return "Timer1Select"

        return self.__class__.__name__









class Timer1Select(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData) -> None:
        super().__init__(clock_view, clock_data, DEFAULT_TIMEOUT, "Normal")

        self._offset = const(0)
        self._is_drawn = False


    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._clock_data.active_timer_selected = 1
        super().initState(reset_timer_callback)

        self._is_drawn = False
        self._is_timer_init = self._clock_data.t1_duration > 0


    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._hdr_t1_x)
        wr.printstring("T1", invert=True)

        was_drawn = self._is_drawn
        self._is_drawn = True
        return has_changes or not was_drawn


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "TimerSetMinute10"
        if event.event_type == Event.EVENT_BTN_CLICK:
            return "TimerStart" if self._is_timer_init else "TimerSetMinute10"
        if event.event_type == Event.EVENT_ROT_INC:
            return "Timer2Select"
        if event.event_type == Event.EVENT_ROT_DEC:
            return "TimerBackSelect"

        return self.__class__.__name__









class Timer2Select(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData) -> None:
        super().__init__(clock_view, clock_data, DEFAULT_TIMEOUT, "Normal")

        self._offset = const(3)
        self._is_drawn = False


    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._clock_data.active_timer_selected = 2
        super().initState(reset_timer_callback)

        self._is_drawn = False
        self._is_timer_init = self._clock_data.t2_duration > 0


    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._hdr_t2_x)
        wr.printstring("T2", invert=True)

        was_drawn = self._is_drawn
        self._is_drawn = True
        return has_changes or not was_drawn


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "TimerSetMinute10"
        if event.event_type == Event.EVENT_BTN_CLICK:
            return "TimerStart" if self._is_timer_init else "TimerSetMinute10"
        if event.event_type == Event.EVENT_ROT_INC:
            return "Timer3Select"
        if event.event_type == Event.EVENT_ROT_DEC:
            return "Timer1Select"

        return self.__class__.__name__









class Timer3Select(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData) -> None:
        super().__init__(clock_view, clock_data, DEFAULT_TIMEOUT, "Normal")

        self._offset = const(6)
        self._is_drawn = False


    def initState(self, reset_timer_callback: FunctionType) -> None:
        self._clock_data.active_timer_selected = 3
        super().initState(reset_timer_callback)

        self._is_drawn = False
        self._is_timer_init = self._clock_data.t3_duration > 0


    def prepareView(self) -> bool:
        has_changes = super().prepareView()

        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._hdr_t3_x)
        wr.printstring("T3", invert=True)

        was_drawn = self._is_drawn
        self._is_drawn = True
        return has_changes or not was_drawn


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "TimerSetMinute10"
        if event.event_type == Event.EVENT_BTN_CLICK:
            return "TimerStart" if self._is_timer_init else "TimerSetMinute10"
        if event.event_type == Event.EVENT_ROT_INC:
            return "TimerBackSelect"
        if event.event_type == Event.EVENT_ROT_DEC:
            return "Timer2Select"

        return self.__class__.__name__





class TimerBackSelect(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData) -> None:
        super().__init__(clock_view, clock_data, DEFAULT_TIMEOUT, "Normal")

        self._is_drawn = False


    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        self._is_drawn = False


    def prepareView(self) -> bool:
        self._fb.clear()

        wr = self._wri_default
        wr.set_textpos(self._fb, 92, 20)
        wr.printstring("Back")

        was_drawn = self._is_drawn
        self._is_drawn = True
        return not was_drawn


    def processEvent(self, event: Event) -> str:
        if event.event_type == Event.EVENT_BTN_CLICK \
            or event.event_type == Event.EVENT_BTN_LONG_CLICK:
            return "Normal"
        if event.event_type == Event.EVENT_ROT_INC:
            return "Timer1Select"
        if event.event_type == Event.EVENT_ROT_DEC:
            return "Timer3Select"

        return self.__class__.__name__







class TimerStart(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, countdown_timer: Timer, process_event_callback: FunctionType) -> None:
        super().__init__(clock_view, clock_data)

        self._process_event_callback = process_event_callback
        self._countdown_timer = countdown_timer
        self._countdown_value = 0
        self._fb_update_ms = 680


    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)

        self._header_x = 0
        if self._clock_data.active_timer_selected == 1:
            self._header_x = self._hdr_t1_x
        elif self._clock_data.active_timer_selected == 2:
            self._header_x = self._hdr_t2_x
        elif self._clock_data.active_timer_selected == 3:
            self._header_x = self._hdr_t3_x
        else:
            raise IndexError("Unexpected active timer value: {}".format(self._clock_data.active_timer_selected))

        self._countdown_value = self._timer_min * 60 + self._timer_sec

        if self._countdown_value <= 0 or self._countdown_value >= 3600:
            raise ValueError("Countdown value must be between 1 and 3599 (is: {})".format(self._countdown_value))

        self._fb.init()
        self._countdown_timer.init(mode=Timer.ONE_SHOT, period=1000, callback=self._handle_countdown_timer)


    def _handle_countdown_timer(self, timer: Timer) -> None:
        self._countdown_value -= 1
        self._timer_min = self._countdown_value // 60
        self._timer_sec = self._countdown_value % 60
        if self._countdown_value <= 0:
            self.prepareView()
            self._fb.show()
            self._process_event_callback(None)
        schedule(self._update_fb, None)
        pass


    def _update_fb(self, any) -> None:
        ts = ticks_ms()
        self.prepareView()
        self._fb.show()
        self._fb.wait_until_ready()
        self._fb_update_ms = ticks_diff(ticks_ms(), ts)
        if self._countdown_value > 0:
            self._countdown_timer.init(mode=Timer.ONE_SHOT, period=(1000-self._fb_update_ms), callback=self._handle_countdown_timer)


    def prepareView(self) -> bool:
        super().prepareView()

        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._header_x)
        wr.printstring("T{}".format(self._clock_data.active_timer_selected), invert=True)

        return False # only countdown timer handler updates the display


    def processEvent(self, event: Event) -> str:
        if event is None:
            if self._countdown_value <= 0:
                return "TimerAlarm"
        elif event.event_type == Event.EVENT_BTN_LONG_CLICK:
            self._countdown_timer.deinit()
            return "Normal"

        return self.__class__.__name__





class TimerAlarm(_CountdownState):
    def __init__(self, clock_view: ClockView, clock_data: ClockData, countdown_timer: Timer, process_event_callback: FunctionType, buzzer_pin: Pin, motor_pin: Pin = None) -> None:
        super().__init__(clock_view, clock_data)

        self._process_event_callback = process_event_callback
        self._countdown_timer = countdown_timer
        self._buzzer_pin = buzzer_pin
        self._motor_pin = motor_pin

        self._is_drawn = False


    def initState(self, reset_timer_callback: FunctionType) -> None:
        super().initState(reset_timer_callback)
        self._is_drawn = False
        self._timer_min = 0
        self._timer_sec = 0

        self._header_x = 0
        if self._clock_data.active_timer_selected == 1:
            self._header_x = self._hdr_t1_x
        elif self._clock_data.active_timer_selected == 2:
            self._header_x = self._hdr_t2_x
        elif self._clock_data.active_timer_selected == 3:
            self._header_x = self._hdr_t3_x
        else:
            raise IndexError("Unexpected active timer value: {}".format(self._clock_data.active_timer_selected))

        self._do_alarm(None)


    def _do_alarm(self, any:Any) -> None:
        if self._buzzer_pin:
            self._buzzer_pin.on()
        if self._motor_pin:
            self._motor_pin.on()
        self._countdown_timer.init(mode=Timer.ONE_SHOT, period=20_000, callback=self._finish_alarm)


    def _finish_alarm(self, timer: Timer, call_home: bool = True) -> None:
        timer.deinit()
        if self._buzzer_pin:
            self._buzzer_pin.off()
        if self._motor_pin:
            self._motor_pin.off()

        if call_home:
            self._process_event_callback(None)



    def prepareView(self) -> bool:
        super().prepareView()

        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._header_x)
        wr.printstring("T{}".format(self._clock_data.active_timer_selected), invert=True)

        msg = "Countdown finished"
        wr.set_textpos(self._fb, self._date_y, 100 - wr.stringlen(msg)//2)
        wr.printstring(msg)

        was_drawn = self._is_drawn
        self._is_drawn = True
        return not was_drawn


    def processEvent(self, event: Event) -> str:
        if event is None or \
            event.event_type == Event.EVENT_BTN_CLICK \
            or event.event_type == Event.EVENT_BTN_LONG_CLICK:
            self._finish_alarm(self._countdown_timer, False)
            return "Normal"

        return self.__class__.__name__
