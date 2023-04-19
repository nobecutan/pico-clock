from framebuf import FrameBuffer
from rp2 import const
from clock_view import ClockView
from clockdata import ClockData
from gui.core.writer import Writer
import gui.fonts.arial_50 as huge_font
import gui.fonts.freesans20 as small_font

class ClockView200x200(ClockView):
    def __init__(self, fb: FrameBuffer) -> None:
        super().__init__(fb)
        self._wri_default = Writer(self._fb, small_font, False)
        self._wri_time = Writer(self._fb, huge_font, False)
        # _State
        self._header_y = const(5)
        self._hdr_t1_x = const(13)
        self._hdr_t2_x = const(39)
        self._hdr_t3_x = const(70)
        self._footer_y = const(175)

        # _TimerState
        self._hour_start_x = const(25)
        self._minutes_start_x = const(108)
        self._time_y = const(55)
        self._date_y = const(110)
        self._date_x_end = const(182)



    def draw_init_state(self) -> bool:
        self._fb.fill(0)

        wr = self._wri_default
        wr.set_textpos(self._fb, 92, 20)
        wr.printstring("Initialisierung...")
        return True


    def draw_background(self, cd: ClockData) -> bool:
        has_changes = super().draw_background(cd)
        if self._prev_cd.battery != cd.battery:
            has_changes = True
            self._prev_cd.battery = cd.battery
        if self._prev_cd.temperature != cd.temperature:
            has_changes = True
            self._prev_cd.temperature = cd.temperature
        if self._prev_cd.pressure != cd.pressure:
            has_changes = True
            self._prev_cd.pressure = cd.pressure
        if not has_changes:
            return False

        self._fb.fill(0)
        wr = self._wri_default
        wr.set_textpos(self._fb, self._header_y, self._hdr_t1_x)
        wr.printstring("T1")
        wr.set_textpos(self._fb, self._header_y, self._hdr_t2_x)
        wr.printstring("T2")
        wr.set_textpos(self._fb, self._header_y, self._hdr_t3_x)
        wr.printstring("T3")
        self._fb.hline(5, 26, 190, 1)
        self._fb.vline(36, 9, 13, 1)
        self._fb.vline(66, 9, 13, 1)
        self._fb.vline(96, 9, 13, 1)

        if cd.battery >= 0:
            wr.set_textpos(self._fb, 5, 195 -
                           wr.stringlen(str(cd.battery)))
            wr.printstring(str(cd.battery))

        if cd.temperature is not None:
            wr.set_textpos(self._fb, self._footer_y, 5)
            wr.printstring(cd.temperature)
            if cd.pressure is not None:
                wr.set_textpos(self._fb, self._footer_y, 195 -
                               wr.stringlen(cd.pressure))
                wr.printstring(cd.pressure)
            self._fb.hline(5, 173, 190, 1)

        return True



    def draw_time(self, cd: ClockData) -> bool:
        has_changes = self.draw_background(cd)
        if self._prev_cd.hour != cd.hour:
            has_changes = True
            self._prev_cd.hour = cd.hour
        if self._prev_cd.minute != cd.minute:
            has_changes = True
            self._prev_cd.minute = cd.minute
        if not has_changes:
            return False

        t_writer = self._wri_time
        t_writer.set_textpos(self._fb, 50, 91)
        t_writer.printstring(":")
        t_writer.set_textpos(self._fb, self._time_y, self._hour_start_x)
        t_writer.printstring("{:02d}".format(cd.hour))
        t_writer.set_textpos(self._fb, self._time_y,
                             self._minutes_start_x)
        t_writer.printstring("{:02d}".format(cd.minute))

        return True


    def draw_countdown(self, cd: ClockData) -> bool:
        has_changes = self.draw_background(cd)
        if self._prev_cd.hour != cd.hour:
            self._prev_cd.hour = cd.hour
            has_changes = True
        if self._prev_cd.minute != cd.minute:
            self._prev_cd.minute = cd.minute
            has_changes = True
        if self._prev_cd.active_timer_remaining != cd.active_timer_remaining:
            has_changes = True
            self._prev_cd.active_timer_remaining = cd.active_timer_remaining
        if not has_changes:
            return False

        min, sec = divmod(cd.active_timer_remaining, 60)
        t_writer = self._wri_time
        t_writer.set_textpos(self._fb, 50, 91)
        t_writer.printstring(":")
        t_writer.set_textpos(self._fb, self._time_y, self._hour_start_x)
        t_writer.printstring("{:02d}".format(min))
        t_writer.set_textpos(self._fb, self._time_y, self._minutes_start_x)
        t_writer.printstring("{:02d}".format(sec))

        time = "{:02d}:{:02d}".format(cd.hour, cd.minute)
        wr = self._wri_default
        wr.set_textpos(self._fb, self._date_y, self._date_x_end - wr.stringlen(time))
        wr.printstring(time)


        return True




    def draw_normal_state(self, cd: ClockData) -> bool:
        has_changes = self.draw_background(cd)
