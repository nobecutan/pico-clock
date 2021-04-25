# The MIT License (MIT)
# Copyright (c) 2020 Mike Teachman
# https://opensource.org/licenses/MIT

# Platform-independent MicroPython code for the rotary encoder module

# Documentation:
#   https://github.com/MikeTeachman/micropython-rotary

import micropython
import utime
from machine import Timer
from micropython import const

_DIR_CW = const(0x10)  # Clockwise step
_DIR_CCW = const(0x20)  # Counter-clockwise step

# Rotary Encoder States
_R_START = const(0x0)
_R_CW_1 = const(0x1)
_R_CW_2 = const(0x2)
_R_CW_3 = const(0x3)
_R_CCW_1 = const(0x4)
_R_CCW_2 = const(0x5)
_R_CCW_3 = const(0x6)
_R_ILLEGAL = const(0x7)

_transition_table = [

    # |------------- NEXT STATE -------------|            |CURRENT STATE|
    # CLK/DT    CLK/DT     CLK/DT    CLK/DT
    #   00        01         10        11
    [_R_START, _R_CCW_1, _R_CW_1,  _R_START],             # _R_START
    [_R_CW_2,  _R_START, _R_CW_1,  _R_START],             # _R_CW_1
    [_R_CW_2,  _R_CW_3,  _R_CW_1,  _R_START],             # _R_CW_2
    [_R_CW_2,  _R_CW_3,  _R_START, _R_START | _DIR_CW],   # _R_CW_3
    [_R_CCW_2, _R_CCW_1, _R_START, _R_START],             # _R_CCW_1
    [_R_CCW_2, _R_CCW_1, _R_CCW_3, _R_START],             # _R_CCW_2
    [_R_CCW_2, _R_START, _R_CCW_3, _R_START | _DIR_CCW],  # _R_CCW_3
    [_R_START, _R_START, _R_START, _R_START]]             # _R_ILLEGAL

_transition_table_half_step = [
    [_R_CW_3,            _R_CW_2,  _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CCW, _R_START, _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CW,  _R_CW_2,  _R_START, _R_START],
    [_R_CW_3,            _R_CCW_2, _R_CCW_1, _R_START],
    [_R_CW_3,            _R_CW_2,  _R_CCW_1, _R_START | _DIR_CW],
    [_R_CW_3,            _R_CCW_2, _R_CW_3,  _R_START | _DIR_CCW]]

_STATE_MASK = const(0x07)
_DIR_MASK = const(0x30)

_PERIOD_LONG_CLICK = const(800)
_PERIOD_CLICK = 300
_PERIOD_DBL_CLICK = 450

def _wrap(value, incr, lower_bound, upper_bound):
    range = upper_bound - lower_bound + 1
    value = value + incr

    if value < lower_bound:
        value += range * ((lower_bound - value) // range + 1)

    return lower_bound + (value - lower_bound) % range


def _bound(value, incr, lower_bound, upper_bound):
    return min(upper_bound, max(lower_bound, value + incr))


def _trigger(event):
    for listener in event.owner._listener:
        listener(event)


class Event(object):
    EVENT_ROT_INC = const(1)
    EVENT_ROT_DEC = const(2)
    EVENT_BTN_UP = const(4)
    EVENT_BTN_DOWN = const(8)
    EVENT_BTN_CLICK = const(16)
    EVENT_BTN_DBL_CLICK = const(32)
    EVENT_BTN_TRBL_CLICK = const(64)
    EVENT_BTN_LONG_CLICK = const(128)

    def __init__(self, owner, event_type, value, btn_pushed):
        self.owner = owner
        self.event_type = event_type
        self.value = value
        self.btn_pushed = btn_pushed

    def _type_name(self):
        if self.event_type == self.EVENT_ROT_INC: return 'EVENT_ROT_INC'
        elif self.event_type == self.EVENT_ROT_DEC: return 'EVENT_ROT_DEC'
        elif self.event_type == self.EVENT_BTN_UP: return 'EVENT_BTN_UP'
        elif self.event_type == self.EVENT_BTN_DOWN: return 'EVENT_BTN_DOWN'
        elif self.event_type == self.EVENT_BTN_CLICK: return 'EVENT_BTN_CLICK'
        elif self.event_type == self.EVENT_BTN_DBL_CLICK: return 'EVENT_BTN_DBL_CLICK'
        elif self.event_type == self.EVENT_BTN_TRBL_CLICK: return 'EVENT_BTN_TRBL_CLICK'
        elif self.event_type == self.EVENT_BTN_LONG_CLICK: return 'EVENT_BTN_LONG_CLICK'
        else: return 'Unsupported event type'

    def __str__(self):
        return 'Event type: ' + self._type_name() + ' value: ' + str(self.value) + ' btn_pushed: ' + str(self.btn_pushed)
class Rotary(object):


    RANGE_UNBOUNDED = const(1)
    RANGE_WRAP = const(2)
    RANGE_BOUNDED = const(3)

    def __init__(self, min_val, max_val, reverse, range_mode, half_step, start_val=None, has_switch_pin = False):
        self._min_val = min_val
        self._max_val = max_val
        self._reverse = -1 if reverse else 1
        self._range_mode = range_mode
        self._value = min_val
        self._state = _R_START
        self._half_step = half_step
        self._listener = []
        if start_val is not None:
            self._value = start_val
        if has_switch_pin:
            self._last_click_time = 0
            self._last_dbl_click_time = 0
            self._sw_down_time = 0
            self._long_click_timer = Timer(-1)

    def set(self, value=None, min_val=None,
            max_val=None, reverse=None, range_mode=None):
        # disable DT and CLK pin interrupts
        self._hal_disable_irq()

        if value is not None:
            self._value = value
        if min_val is not None:
            self._min_val = min_val
        if max_val is not None:
            self._max_val = max_val
        if reverse is not None:
            self._reverse = -1 if reverse else 1
        if range_mode is not None:
            self._range_mode = range_mode
        self._state = _R_START

        # enable DT and CLK pin interrupts
        self._hal_enable_irq()

    def value(self):
        return self._value

    def reset(self):
        self._value = 0

    def close(self):
        self._hal_close()

    def add_listener(self, l):
        self._listener.append(l)

    def remove_listener(self, l):
        if l not in self._listener:
            raise ValueError('{} is not an installed listener'.format(l))
        self._listener.remove(l)

    def _process_rotary_pins(self, pin):
        old_value = self._value
        clk_dt_pins = (self._hal_get_clk_value() <<
                       1) | self._hal_get_dt_value()
        # Determine next state
        if self._half_step:
            self._state = _transition_table_half_step[self._state &
                                                      _STATE_MASK][clk_dt_pins]
        else:
            self._state = _transition_table[self._state &
                                            _STATE_MASK][clk_dt_pins]
        direction = self._state & _DIR_MASK

        incr = 0
        if direction == _DIR_CW:
            incr = 1
        elif direction == _DIR_CCW:
            incr = -1

        incr *= self._reverse

        if self._range_mode == self.RANGE_WRAP:
            self._value = _wrap(
                self._value,
                incr,
                self._min_val,
                self._max_val)
        elif self._range_mode == self.RANGE_BOUNDED:
            self._value = _bound(
                self._value,
                incr,
                self._min_val,
                self._max_val)
        else:
            self._value = self._value + incr

        try:
            if old_value != self._value and len(self._listener) != 0:
                micropython.schedule(_trigger, Event(self, Event.EVENT_ROT_INC if incr > 0 else Event.EVENT_ROT_DEC, self._value, self._hal_get_sw_value()))
        except:
            pass




    def _process_switch_pin(self, pin):
        if len(self._listener) == 0: return


        try:
            if self._hal_get_sw_value(): # Btn down
                self._long_click_timer.deinit() # Stop long click timer
                self._sw_down_time = utime.ticks_ms()
                self._long_click_timer.init(mode=Timer.ONE_SHOT, period=_PERIOD_LONG_CLICK, callback=self._issue_long_click_event)
                micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_DOWN, self._value, self._hal_get_sw_value()))
            else:
                self._long_click_timer.deinit() # Stop long click timer
                if utime.ticks_diff(utime.ticks_ms(), self._last_dbl_click_time) < _PERIOD_DBL_CLICK: # triple click
                    self._last_click_time = self._last_dbl_click_time = 0
                    micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_TRBL_CLICK, self._value, self._hal_get_sw_value()))
                elif utime.ticks_diff(utime.ticks_ms(), self._last_click_time) < _PERIOD_DBL_CLICK: # double click
                    self._last_dbl_click_time = utime.ticks_ms()
                    self._long_click_timer.init(mode=Timer.ONE_SHOT, period=_PERIOD_DBL_CLICK, callback=self._issue_dbl_click_event)
                elif utime.ticks_diff(utime.ticks_ms(), self._sw_down_time) <= _PERIOD_CLICK: #click
                    self._last_click_time = utime.ticks_ms()
                    self._long_click_timer.init(mode=Timer.ONE_SHOT, period=_PERIOD_DBL_CLICK, callback=self._issue_click_event)

                micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_UP, self._value, self._hal_get_sw_value()))

        except:
            pass


    def _issue_long_click_event(self, timer):
        micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_LONG_CLICK, self._value, self._hal_get_sw_value()))


    def _issue_click_event(self, timer):
        self._last_click_time = 0
        micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_CLICK, self._value, self._hal_get_sw_value()))


    def _issue_dbl_click_event(self, timer):
        self._last_dbl_click_time = 0
        micropython.schedule(_trigger, Event(self, Event.EVENT_BTN_DBL_CLICK, self._value, self._hal_get_sw_value()))

