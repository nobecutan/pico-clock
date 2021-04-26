

class ClockData:
    _WEEKDAY_STR = ("So", "Mo", "Di", "Mi", "Do", "Fr", "Sa")
    _MONTH_STR = ("", "Jan", "Feb", "Mar", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")
    _MONTH_LOOKUP_TABLE = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)


    def __init__(self):
        self.year = 2020
        self.month = 6
        self.day = 15
        self.weekday = 1
        self.hour = 0
        self.minute = 0
        self.second = 0
        self.temperature = None
        self.pressure = None
        self.battery = 100
        self.t1_duration = 0
        self.t2_duration = 0
        self.t3_duration = 0
        self.is_init = False

    def from_rtc(self, rtc_tuple:Tuple[int, int, int, int, int, int, int]) -> bool:
        self.year = rtc_tuple[0]
        self.month = rtc_tuple[1]
        self.day = rtc_tuple[2]
        self.weekday = rtc_tuple[3]
        self.hour = rtc_tuple[4]
        self.minute = rtc_tuple[5]
        self.second = rtc_tuple[6]
        self.is_init = self.year >= 2020
        return self.is_init



    def calc_weekday(self) -> None:
        m = self.month
        y = self.year
        d = self.day
        if m < 3:
            y -= 1
        self.weekday = (y + y//4 - y//100 + y//400 + self._MONTH_LOOKUP_TABLE[m-1] + d) % 7


    def get_weekday_str(self) -> str:
        return self._WEEKDAY_STR[self.weekday]


    def get_month_str(self) -> str:
        return self._MONTH_STR[self.month]


    def get_date_str(self) -> str:
        return self.get_weekday_str() + ", " + "{:02d}. {:s} {:04d}".format(self.day, self.get_month_str(), self.year)


    def __str__(self) -> str:
        return self.get_date_str() + " {:02d}:{:02d}".format(self.hour, self.minute)

