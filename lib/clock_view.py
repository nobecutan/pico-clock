from framebuf import FrameBuffer
from clockdata import ClockData

class ClockView:
    def __init__(self, fb: FrameBuffer, cd: ClockData) -> None:
        self._fb = fb
        self._cur_cd = cd
        self._prev_cd = ClockData()
        self._force_update = False

    def force_update(self) -> None:
        self._force_update = True

    def draw_background(self) -> bool:
        if self._force_update:
            self._force_update = False
            self._fb.fill(0)
            return True
        return False

    def draw_time(self) -> bool:
        if self._force_update:
            self._force_update = False
            self._fb.fill(0)
            return True
        return False

    def draw_countdown(self) -> bool:
        if self._force_update:
            self._force_update = False
            self._fb.fill(0)
            return True
        return False

#####################################################
    def draw_init_state(self) -> bool:
        if self._force_update:
            self._force_update = False
            self._fb.fill(0)
            return True
        return False

    def draw_normal_state(self) -> bool:
        if self._force_update:
            self._force_update = False
            self._fb.fill(0)
            return True
        return False

