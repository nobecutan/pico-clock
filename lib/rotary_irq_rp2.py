# The MIT License (MIT)
# Copyright (c) 2020 Mike Teachman
# Copyright (c) 2021 Eric Moyer
# https://opensource.org/licenses/MIT

# Platform-specific MicroPython code for the rotary encoder module
# Raspberry Pi Pico implementation

# Documentation:
#   https://github.com/MikeTeachman/micropython-rotary

from machine import Pin,Timer
from rotary import Rotary

IRQ_RISING_FALLING = Pin.IRQ_RISING | Pin.IRQ_FALLING


class RotaryIRQ(Rotary):
    def __init__(
        self,
        pin_num_clk,
        pin_num_dt,
        min_val=0,
        max_val=10,
        start_val=None,
        reverse=True,
        range_mode=Rotary.RANGE_UNBOUNDED,
        pull_up=False,
        half_step=False,
        pin_num_sw=None,
    ):
        super().__init__(min_val, max_val, reverse, range_mode, half_step, start_val, pin_num_sw is not None)

        if pull_up:
            self._pin_clk = Pin(pin_num_clk, Pin.IN, Pin.PULL_UP)
            self._pin_dt = Pin(pin_num_dt, Pin.IN, Pin.PULL_UP)
        else:
            self._pin_clk = Pin(pin_num_clk, Pin.IN)
            self._pin_dt = Pin(pin_num_dt, Pin.IN)


        if pin_num_sw is not None:
            self._pin_sw = Pin(pin_num_sw, Pin.IN, Pin.PULL_DOWN)
            self._pin_sw_timer = Timer(-1)
        else: self._pin_sw = None

        self._hal_enable_irq()


    def _debounce_switch_pin(self, pin):
        self._disable_sw_irq()
        self._pin_sw_timer.init(mode=Timer.ONE_SHOT, period=50, callback=self._debounce_switch_pin_timer_callback)


    def _debounce_switch_pin_timer_callback(self, timer):
        self._process_switch_pin(self._pin_sw)
        self._enable_sw_irq()


    def _enable_clk_irq(self):
        self._pin_clk.irq(self._process_rotary_pins, IRQ_RISING_FALLING)

    def _enable_dt_irq(self):
        self._pin_dt.irq(self._process_rotary_pins, IRQ_RISING_FALLING)

    def _enable_sw_irq(self):
        if self._pin_sw is not None:
            self._pin_sw.irq(self._debounce_switch_pin, IRQ_RISING_FALLING)

    def _disable_clk_irq(self):
        self._pin_clk.irq(None, 0)

    def _disable_dt_irq(self):
        self._pin_dt.irq(None, 0)

    def _disable_sw_irq(self):
        if self._pin_sw is not None:
            self._pin_sw.irq(None, 0)

    def _hal_get_clk_value(self):
        return self._pin_clk.value()

    def _hal_get_dt_value(self):
        return self._pin_dt.value()

    def _hal_get_sw_value(self):
        if self._pin_sw is not None: return not self._pin_sw.value()
        else: return None

    def _hal_enable_irq(self):
        self._enable_clk_irq()
        self._enable_dt_irq()
        self._enable_sw_irq()

    def _hal_disable_irq(self):
        self._disable_clk_irq()
        self._disable_dt_irq()
        self._disable_sw_irq()

    def _hal_close(self):
        self._hal_disable_irq()
