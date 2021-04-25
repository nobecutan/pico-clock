
import states

from machine import Timer
from rotary import Event
from drivers.display import Display
from clockdata import ClockData


class Clock():

    def __init__(self, display:Display, clock_data: ClockData) -> None:
        self._clock_data = clock_data
        self._last_event_ts = 0
        self._display = display
        self._cur_state = None
        self._timeout_timer = Timer()
        self._registered_states = {}


    def register_state(self, state: states._State) -> None:
        self._registered_states[state.__class__.__name__] = state
        if self._cur_state is None and isinstance(state, states.Init):
            self._cur_state = state


    def init(self) -> None:
        if not isinstance(self._cur_state, states.Init):
            return

        self.processEvent(None)
        new_state_name = self._cur_state.init()
        self._handle_state_change(new_state_name)


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
            self._display.show()


    def processEvent(self, event: Event) -> None:
        if self._cur_state is None:
            return

        new_state_name = self._cur_state.processEvent(event)

        self._handle_state_change(new_state_name)
