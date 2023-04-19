# ds3231_port.py Portable driver for DS3231 precison real time clock.
# Adapted from WiPy driver at https://github.com/scudderfish/uDS3231

# Author: Peter Hinch
# Copyright Peter Hinch 2018 Released under the MIT license.

import utime
import machine
import sys
from micropython import const

DS3231_I2C_ADDR = const(0x68) # 104
DS3231_REG_SECONDS  = const(0x00)
DS3231_REG_AL1_SEC  = const(0x07)
DS3231_REG_AL2_MIN  = const(0x0B)
DS3231_REG_CONTROL  = const(0x0E)
DS3231_REG_STATUS   = const(0x0F)
DS3231_REG_TEMP_MSB = const(0x11)

PREV_MONTH_DAYS = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

try:
    rtc = machine.RTC()
except:
    print('Warning: machine module does not support the RTC.')
    rtc = None

def _bcd2dec(bcd):
    return (((bcd & 0xf0) >> 4) * 10 + (bcd & 0x0f))

def _dec2bcd(dec):
    tens, units = divmod(dec, 10)
    return (tens << 4) + units

def _tobytes(num: int) -> bytes:
    return num.to_bytes(1, 'little')

def _frombytes(bytes: Union[Iterable[int], SupportsBytes]) -> int:
    return int.from_bytes(bytes, 'little')


class DS3231:
    AL1_ONCE_PER_SECOND =                  const(0x0F)
    AL1_SECONDS_MATCH =                    const(0x0E)
    AL1_MINUTES_SECONDS_MATCH =            const(0x0C)
    AL1_HOURS_MINUTES_SECONDS_MATCH =      const(0x08)
    AL1_DATE_HOURS_MINUTES_SECONDS_MATCH = const(0x00)
    AL1_DAY_HOURS_MINUTES_SECONDS_MATCH =  const(0x10)


    AL2_ONCE_PER_MINUTE =          const(0x0E)
    AL2_MINUTES_MATCH =            const(0x0C)
    AL2_HOURS_MINUTES_MATCH =      const(0x08)
    AL2_DATE_HOURS_MINUTES_MATCH = const(0x00)
    AL2_DAY_HOURS_MINUTES_MATCH =  const(0x10)


    INT_SQW_OUT_OFF =    const(0x04)
    INT_SQW_OUT_INT =    const(0x07)
    INT_SQW_OUT_1Hz =    const(0x00)
    INT_SQW_OUT_1024Hz = const(0x08)
    INT_SQW_OUT_4096Hz = const(0x10)
    INT_SQW_OUT_8192Hz = const(0x18)


    def __init__(self, i2c:machine.I2C):
        self._i2c = i2c
        self._timebuf = bytearray(7)
        self._regbuf =  bytearray(1)
        if DS3231_I2C_ADDR not in self._i2c.scan():
            raise RuntimeError("DS3231 not found on I2C bus at %d" % DS3231_I2C_ADDR)

    @staticmethod
    def _leap_day(year:int, month:int) -> int:
        if month <= 2:
            return 0
        if year % 100 == 0:
            return 0
        if year % 4 == 0:
            return 1
        return 0


    @staticmethod
    def _get_year_day(year:int, month:int, day:int) -> int:
        return PREV_MONTH_DAYS[month] + day + DS3231._leap_day(year, month)


    @staticmethod
    def _bit_test(word:int, bit_num:int) -> int:
        if bit_num < 0 or bit_num > 31:
            raise IndexError("bit number {} not supported".format(bit_num))
        return (word >> bit_num) & 0x01


    def _read_register(self, reg:int) -> int:
        self._i2c.readfrom_mem_into(DS3231_I2C_ADDR, reg, self._regbuf)
        return _frombytes(self._regbuf)


    def _read_bytes(self, reg:int, nbytes:int) -> bytes:
        return self._i2c.readfrom_mem(DS3231_I2C_ADDR, reg, nbytes)


    def _write_register(self, reg:int, value: int) -> None:
        self._i2c.writeto_mem(DS3231_I2C_ADDR, reg, _tobytes(value))


    def _read_buffer(self, reg:int, buffer:bytearray) -> None:
        self._i2c.readfrom_mem_into(DS3231_I2C_ADDR, reg, buffer)


    # def _write_buffer(self, reg:int, buffer: bytes) -> None:
    #     self._i2c.writeto_mem(DS3231_I2C_ADDR, reg, buffer)


    def get_time(self, set_rtc:bool=False):
        if set_rtc:
            self.await_transition()  # For accuracy set RTC immediately after a seconds transition
        else:
            self._read_buffer(DS3231_REG_SECONDS, self._timebuf)
        return self.convert(set_rtc)

    def convert(self, set_rtc:bool=False):  # Return a tuple in localtime() format
        data = self._timebuf
        ss = _bcd2dec(data[0])
        mm = _bcd2dec(data[1])
        if data[2] & 0x40:
            hh = _bcd2dec(data[2] & 0x1f)
            if data[2] & 0x20:
                hh += 12
        else:
            hh = _bcd2dec(data[2])
        wday = data[3]
        DD = _bcd2dec(data[4])
        MM = _bcd2dec(data[5] & 0x1f)
        YY = _bcd2dec(data[6])
        if data[5] & 0x80:
            YY += 2000
        else:
            YY += 1900
        # Time from DS3231 in time.localtime() format (less yday)
        result = (YY, MM, DD, hh, mm, ss, wday - 1, self._get_year_day(YY, MM, DD))
        if set_rtc:
            if rtc is None:
                # Best we can do is to set local time
                secs = utime.mktime(result)
                utime.localtime(secs)
            else:
                rtc.datetime((YY, MM, DD, wday, hh, mm, ss))
        return result


    def save_time(self, date = None):
        if date is None:
            (YY, MM, mday, hh, mm, ss, wday, yday) = utime.localtime()  # Based on RTC
        else:
            (YY, MM, mday, hh, mm, ss, wday) = date[0:7]
        mem_addr = DS3231_REG_SECONDS
        self._write_register(mem_addr, _dec2bcd(ss))
        mem_addr += 1
        self._write_register(mem_addr, _dec2bcd(mm))
        mem_addr += 1
        self._write_register(mem_addr, _dec2bcd(hh))
        mem_addr += 1
        self._write_register(mem_addr, _dec2bcd(wday + 1))
        mem_addr += 1
        self._write_register(mem_addr, _dec2bcd(mday))
        mem_addr += 1
        cc,yy = divmod(YY, 100)
        if cc >= 20:
            self._write_register(mem_addr, _dec2bcd(MM) | 0x80)  # Century bit
            mem_addr += 1
            self._write_register(mem_addr, _dec2bcd(yy))
        else:
            self._write_register(mem_addr, _dec2bcd(MM))
            mem_addr += 1
            self._write_register(mem_addr, _dec2bcd(yy))


    # Wait until DS3231 seconds value changes before reading and returning data
    def await_transition(self):
        self._read_buffer(DS3231_REG_SECONDS, self._timebuf)
        ss = self._timebuf[0]
        while ss == self._timebuf[0]:
            self._read_buffer(DS3231_REG_SECONDS, self._timebuf)
        return self._timebuf


    # Test hardware RTC against DS3231. Default runtime 10 min. Return amount
    # by which DS3231 clock leads RTC in PPM or seconds per year.
    # Precision is achieved by starting and ending the measurement on DS3231
    # one-seond boundaries and using ticks_ms() to time the RTC.
    # For a 10 minute measurement +-1ms corresponds to 1.7ppm or 53s/yr. Longer
    # runtimes improve this, but the DS3231 is "only" good for +-2ppm over 0-40C.
    def rtc_test(self, runtime=600, ppm=False, verbose=True):
        if rtc is None:
            raise RuntimeError('machine.RTC does not exist')
        verbose and print('Waiting {} minutes for result'.format(runtime//60))
        factor = 1_000_000 if ppm else 114_155_200  # seconds per year

        self.await_transition()  # Start on transition of DS3231. Record time in .timebuf
        t = utime.ticks_ms()  # Get system time now
        ss = rtc.datetime()[6]  # Seconds from system RTC
        while ss == rtc.datetime()[6]:
            pass
        ds = utime.ticks_diff(utime.ticks_ms(), t)  # ms to transition of RTC
        ds3231_start = utime.mktime(self.convert())  # Time when transition occurred
        t = rtc.datetime()
        rtc_start = utime.mktime((t[0], t[1], t[2], t[4], t[5], t[6], t[3] - 1, 0))  # y m d h m s wday 0

        utime.sleep(runtime)  # Wait a while (precision doesn't matter)

        self.await_transition()  # of DS3231 and record the time
        t = utime.ticks_ms()  # and get system time now
        ss = rtc.datetime()[6]  # Seconds from system RTC
        while ss == rtc.datetime()[6]:
            pass
        de = utime.ticks_diff(utime.ticks_ms(), t)  # ms to transition of RTC
        ds3231_end = utime.mktime(self.convert())  # Time when transition occurred
        t = rtc.datetime()
        rtc_end = utime.mktime((t[0], t[1], t[2], t[4], t[5], t[6], t[3] - 1, 0))  # y m d h m s wday 0

        d_rtc = 1000 * (rtc_end - rtc_start) + de - ds  # ms recorded by RTC
        d_ds3231 = 1000 * (ds3231_end - ds3231_start)  # ms recorded by DS3231
        ratio = (d_ds3231 - d_rtc) / d_ds3231
        ppm = ratio * 1_000_000
        verbose and print('DS3231 leads RTC by {:4.1f}ppm {:4.1f}mins/yr'.format(ppm, ppm*1.903))
        return ratio * factor


    @staticmethod
    def _twos_complement(input_value: int, num_bits: int) -> int:
        mask = 2 ** (num_bits - 1)
        return -(input_value & mask) + (input_value & ~mask)


    def get_temperature(self):
        t = self._read_bytes(DS3231_REG_TEMP_MSB, 2)
        i = t[0] << 8 | t[1]
        return self._twos_complement(i >> 6, 10) * 0.25


    def alarm1_set(self, control:int, second:int = 0, minute:int = 0, hour:int = 0, wday_or_date:int = 0) -> None:
        ss_bcd = _dec2bcd(second)
        mm_bcd = _dec2bcd(minute)
        hh_bcd = _dec2bcd(hour)
        dd_bcd = _dec2bcd(wday_or_date)

        mem_addr = DS3231_REG_AL1_SEC
        self._write_register(mem_addr, ss_bcd | (self._bit_test(control, 0) << 7))
        mem_addr += 1
        self._write_register(mem_addr, mm_bcd | (self._bit_test(control, 1) << 7))
        mem_addr += 1
        self._write_register(mem_addr, hh_bcd | (self._bit_test(control, 2) << 7))
        mem_addr += 1
        if self._bit_test(control, 4):
            self._write_register(mem_addr, dd_bcd | 0x40 | (self._bit_test(control, 3) << 7))
        else:
            self._write_register(mem_addr, dd_bcd | (self._bit_test(control, 3) << 7))


    def alarm1_get(self):
        mem_addr = DS3231_REG_AL1_SEC

# RTC_Time *Alarm1_Get()                                        //


    def alarm1_enable(self) -> None:
        self.alarm1_if_reset()
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg |= 0x01
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def alarm1_disable(self) -> None:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg &= 0xFE
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def alarm1_if_check(self) -> bool:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        return self._bit_test(stat_reg, 0) == 1


    def alarm1_if_reset(self) -> None:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        stat_reg &= 0xFE
        self._write_register(DS3231_REG_STATUS, stat_reg)


    def alarm1_is_enabled(self) -> bool:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        return self._bit_test(ctrl_reg, 0) == 1


    def alarm2_set(self, control:int, minute:int = 0, hour:int = 0, wday_or_date:int = 0) -> None:
        min_bcd = _dec2bcd(minute)
        hou_bcd = _dec2bcd(hour)
        day_bcd = _dec2bcd(wday_or_date)

        mem_addr = DS3231_REG_AL2_MIN
        self._write_register(mem_addr, min_bcd | (self._bit_test(control, 1) << 7))
        mem_addr += 1
        self._write_register(mem_addr, hou_bcd | (self._bit_test(control, 2) << 7))
        mem_addr += 1
        if self._bit_test(control, 4):
            self._write_register(mem_addr, day_bcd | 0x40 | (self._bit_test(control, 3) << 7))
        else:
            self._write_register(mem_addr, day_bcd | (self._bit_test(control, 3) << 7))


# RTC_Time *Alarm2_Get()                                        //

    def alarm2_enable(self) -> None:
        self.alarm2_if_reset()
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg |= 0x02
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def alarm2_disable(self) -> None:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg &= 0xFD
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def alarm2_if_check(self) -> bool:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        return self._bit_test(stat_reg, 1) == 1


    def alarm2_if_reset(self) -> None:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        stat_reg &= 0xFD
        self._write_register(DS3231_REG_STATUS, stat_reg)


    def alarm2_is_enabled(self) -> bool:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        return self._bit_test(ctrl_reg, 1) == 1


    def int_sqw_setup(self, config: int) -> None:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg &= 0xA3
        ctrl_reg |= config
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def enable_32kHz(self) -> None:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        stat_reg |= 0x08
        self._write_register(DS3231_REG_STATUS, stat_reg)


    def disable_32kHz(self) -> None:
        stat_reg = self._read_register(DS3231_REG_STATUS)
        stat_reg &= 0xF7
        self._write_register(DS3231_REG_STATUS, stat_reg)


    def vbat_osc_stop(self) -> None:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg |= 0x08
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def vbat_osc_start(self) -> None:
        ctrl_reg = self._read_register(DS3231_REG_CONTROL)
        ctrl_reg &= 0xF7
        self._write_register(DS3231_REG_CONTROL, ctrl_reg)


    def print_mem(self) -> None:
        mem = self._read_bytes(DS3231_REG_SECONDS, 19)
        for i in range(19):
            print("{:02x}: {:08b}".format(i, mem[i]))

