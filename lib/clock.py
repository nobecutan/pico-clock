
from utime import ticks_diff, ticks_ms
from micropython import const
import states, states_edit

from machine import Timer
from rotary import Event
from drivers.display import Display
from clockdata import ClockData
from bmp280 import BMP280


class Clock():
    _ELEVATION = const(360)

    def __init__(self, display:Display, clock_data: ClockData, temp_sensor: BMP280) -> None:
        self._clock_data = clock_data
        self._display = display
        self._temp_sensor = temp_sensor
        self._cur_state = None
        self._timeout_timer = Timer()
        self._time_refresh_timer = Timer()
        self._registered_states = {}
        self._last_temp_ts = 0
        self._last_update_time = 900


    def register_state(self, state: states._State) -> None:
        self._registered_states[state.__class__.__name__] = state
        if self._cur_state is None and isinstance(state, states.Init):
            self._cur_state = state


    def init(self) -> None:
        if not isinstance(self._cur_state, states.Init):
            return

        self._update_temperature()
        self.processEvent(None)
        new_state_name = self._cur_state.init()
        if new_state_name == states.Normal.__name__:
            self._start_time_refresh_timer()
        self._handle_state_change(new_state_name)


    def _update_temperature(self) -> None:
        pressure = self._temp_sensor.pressure
        pressure_sl = (pressure/pow(1-360./44330, 5.255))/100.0
        self._clock_data.temperature = "{:7.1f}".format(self._temp_sensor.temperature)
        self._clock_data.pressure = "{:7.1f}".format(pressure_sl)


    def _start_time_refresh_timer(self) -> None:
        next_update = (60-self._clock_data.second)*1000 - self._last_update_time
        if next_update < 0:
            next_update = 100

        self._time_refresh_timer.init(mode=Timer.ONE_SHOT, period=next_update, callback=self._handle_time_refresh)
        print(next_update, self._clock_data.second, self._last_update_time)



    def _handle_time_refresh(self, timer: Timer) -> None:
        if not isinstance(self._cur_state, states.Normal):
            return # no update during setup

        ts = ticks_ms()
        self._update_temperature()
        self._cur_state.initState(self._reset_timout_timer)

        self._handle_state_change(self._cur_state.__class__.__name__)
        self._last_update_time = ticks_diff(ticks_ms(), ts)
        self._start_time_refresh_timer()


    def _handle_timeout(self, timer: Timer) -> None:
        timer.deinit()
        if self._cur_state._timeout_state_name is not None:
            self._handle_state_change(self._cur_state._timeout_state_name)


    def _reset_timout_timer(self) -> None:
        self._timeout_timer.deinit()
        if self._cur_state._timeout_ms > 0:
            self._timeout_timer.init(mode=Timer.ONE_SHOT, period=self._cur_state._timeout_ms, callback=self._handle_timeout)
            # print("start timer:", self._cur_state._timeout_ms)


    def _handle_state_change(self, new_state_name: str) -> None:
        # print("handle state change:", new_state_name)
        new_state = self._registered_states.get(new_state_name)
        if new_state is None:
            raise NotImplementedError("State '{:s}' is not implemented".format(new_state_name))

        if new_state is not self._cur_state:
            self._cur_state = new_state
            self._reset_timout_timer()
            self._cur_state.initState(self._reset_timout_timer)

        update_display = self._cur_state.prepareView()
        if update_display:
            self._display.wait_until_ready()
            self._display.init()
            self._display.show()
            self._display.sleep()


    def processEvent(self, event: Event) -> None:
        if self._cur_state is None:
            return

        new_state_name = self._cur_state.processEvent(event)

        self._handle_state_change(new_state_name)
