# epd1in54_V2_fb.py nanogui driver for Waveshare ePpaper 1.54" v2 display
# Tested with Raspberry Pi Pico
# EPD is subclassed from framebuf.FrameBuffer for use with Writer class and nanogui.
# Optimisations to reduce allocations and RAM use.

# Copyright (c) Christof Rath 2021
# Released under the MIT license see LICENSE

# Based on the following sources:
# https://www.waveshare.com/wiki/1.54inch_e-Paper_Module
# https://github.com/mcauser/micropython-waveshare-epaper referred to as "mcauser"
# https://github.com/waveshare/e-Paper/blob/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd1in54_V2.py ("official")

import utime
import framebuf
import uasyncio as asyncio

from micropython import const
from machine import SPI, Pin
from utime import sleep_ms, ticks_ms, ticks_diff
from drivers.display import Display

# Display resolution
EPD_WIDTH = const(200)
EPD_HEIGHT = const(200)

BUSY = const(1)  # 1=busy, 0=idle
BUFFER_SIZE = const(EPD_WIDTH // 8 * EPD_HEIGHT)
WHITE_FRAME = bytearray([0xFF] * BUFFER_SIZE)
BLACK_FRAME = bytearray(BUFFER_SIZE)

DEFAULT_FULL_REFRESH_CYCLE = const(60 * 60 * 1000) # Full display update every hour

class EPD(framebuf.FrameBuffer):
    # A monochrome approach should be used for coding this. The rgb method ensures
    # nothing breaks if users specify colors.
    @staticmethod
    def rgb(r, g, b):
        return int((r > 127) or (g > 127) or (b > 127))

    def __init__(self, spi: SPI, cs: Pin, dc: Pin, rst: Pin, busy: Pin, landscape:bool = False, asyn:bool = False, enablePartial: bool = True, fullRefreshCycleSec: int = DEFAULT_FULL_REFRESH_CYCLE) -> EDP:
        self._spi = spi
        self._cs = cs
        self._dc = dc
        self._rst = rst
        self._busy = busy
        self._lsc = landscape
        self._asyn = asyn
        self._enablePartial = enablePartial
        self._fullRefreshCycle = fullRefreshCycleSec

        self._as_busy = False  # Set immediately on start of task. Cleared when busy pin is logically false (physically 1).
        self._updated = asyncio.Event()
        self._last_full_update_ts = 0

        self._cs.init(Pin.OUT, value=1)
        self._dc.init(Pin.OUT, value=0)
        self._rst.init(Pin.OUT, value=0)
        self._busy.init(Pin.IN)
        # Dimensions in pixels.
        # Public bound variables required by nanogui.
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.demo_mode = False  # Special mode enables demos to run
        self._buffer = bytearray(BUFFER_SIZE)
        self._mvb = memoryview(self._buffer)
        mode = framebuf.MONO_VLSB if landscape else framebuf.MONO_HLSB
        super().__init__(self._buffer, self.width, self.height, mode)
        self.init()

    def _command(self, command: bytes, data: bytes = None) -> None:
        self._cs.value(0)
        self._dc.value(0)
        self._spi.write(command)

        if data is not None:
            self._dc.value(1)
            self._spi.write(data)

        self._cs.value(1)


    # Hardware reset
    def reset(self) -> None:
        self._rst.value(1)
        sleep_ms(10)
        self._rst.value(0)
        sleep_ms(10)
        self._rst.value(1)
        sleep_ms(10)


    def init(self):
        # EPD hardware init start
        self.reset()

        # Initialisation
        cmd = self._command
        cmd(b'\x12')  # SWRESET
        self.wait_until_ready()

        cmd(b'\x01', b'\xC7\x00\x01')  # DRIVER_OUTPUT_CONTROL
        # \xC7 -> (EPD_HEIGHT - 1) & \xFF
        # \x00 -> ((EPD_HEIGHT - 1) >> 8) & \xFF
        # \x01 -> GD = 0 SM = 0 TB = 0

        cmd(b'\x11', b'\x01')  # data entry mode

        cmd(b'\x44', b'\x00\x18')  # set Ram-X address start/end position
        # \x18-->(24+1)*8=200

        cmd(b'\x45', b'\xC7\x00\x00\x00') # set Ram-Y address start/end position
        # \xC7-->(199+1)=200

        cmd(b'\x3C', b'\x01')  # BorderWavefrom orig
        cmd(b'\x18', b'\x80')  # ??

        cmd(b'\x21', b'\x08')  # Invers B/W RAM
        cmd(b'\x22', b'\xB1')  # Load Temperature and waveform setting.
        cmd(b'\x20')  # MASTER_ACTIVATION

        cmd(b'\x4E', b'\x00')  # set RAM x address count to 0;
        cmd(b'\x4F', b'\xC7\x00')  # set RAM y address count to 199;

        self.wait_until_ready()
        print('Init Done.')



    def wait_until_ready(self):
        sleep_ms(25)
        t = ticks_ms()
        while not self.ready():
            sleep_ms(10)
        sleep_ms(10)
        dt = ticks_diff(ticks_ms(), t)
        # print('wait_until_ready {}ms {:4.1f}sec'.format(dt, dt/1_000))

    async def wait(self):
        await asyncio.sleep_ms(0)  # Ensure tasks run that might make it unready
        while not self.ready():
            await asyncio.sleep_ms(25)


    # Pause until framebuf has been copied to device.
    async def updated(self):
        await self._updated.wait()

    # For polling in asynchronous code. Just checks pin state.
    # 0 == busy. Comment in official code is wrong. Code is correct.
    def ready(self):
        return not(self._as_busy or (self._busy.value() == BUSY))  # 0 == busy


    def force_full_refresh(self) -> None:
        self._last_full_update_ts = 0


    def clear(self) -> None:
        self.fill(0)


    async def _as_show(self, buf1=bytearray(1)) -> None:
        self._activate_display()
        await asyncio.sleep(1)
        while self._busy.value() == BUSY:
            await asyncio.sleep_ms(25)  # Don't release lock until update is complete
        self._as_busy = False


    def show(self, buf1=bytearray(1)) -> None:
        if self._as_busy:
            raise RuntimeError('Cannot refresh: display is busy.')

        mvb = self._mvb
        send = self._spi.write
        cmd = self._command
        t = ticks_ms()
        if self._lsc:  # Landscape mode
            wid = self.width
            tbc = self.height // 8  # Vertical bytes per column
            iidx = wid * (tbc - 1)  # Initial index
            idx = iidx  # Index into framebuf
            vbc = 0  # Current vertical byte count
            hpc = 0  # Horizontal pixel count
            self._cs.value(0)
            for i in range(len(mvb)):
                buf1[0] = mvb[idx]  # INVERSION HACK ~data
                send(buf1)
                idx -= self.width
                vbc += 1
                vbc %= tbc
                if not vbc:
                    hpc += 1
                    idx = iidx + hpc
                # if not(i & 0x1f) and (ticks_diff(ticks_ms(), t) > 20):
                #     await asyncio.sleep_ms(0)
                #     t = ticks_ms()
            self._cs.value(1)
            print("Copy Landscape FB:", ticks_diff(ticks_ms(), t))
        else:
            cmd(b'\x24', mvb)
            cmd(b'\x26', mvb)


        if self._asyn:
            self._updated.set()  # framebuf has now been copied to the device
            self._updated.clear()
            self._as_busy = True
            asyncio.create_task(self._as_show())
        else:
            self._activate_display()

            te = ticks_ms()
            # print('show time', ticks_diff(te, t), 'ms')
            if not self.demo_mode:
                # Immediate return to avoid blocking the whole application.
                # User should wait for ready before calling refresh()
                return
            self.wait_until_ready()
            sleep_ms(2000)  # Give time for user to see result



    def _activate_display(self) -> None:
        now = utime.ticks_ms()
        if self._last_full_update_ts == 0 \
            or utime.ticks_diff(now, self._last_full_update_ts) > self._fullRefreshCycle:
            self._command(b'\x22', b'\xF7') # DISPLAY_UPDATE_CONTROL_1
        else:
            self._command(b'\x22', b'\xFF') # DISPLAY_UPDATE_CONTROL_2

        self._command(b'\x20') # MASTER_ACTIVATION
        self._last_full_update_ts = now


    def sleep(self):
        self._as_busy = False
        self.wait_until_ready()
        cmd = self._command

        cmd(b'\x10', b'\x01')  # DEEP_SLEEP_MODE
        self._rst.value(0)

### END OF FILE ###
