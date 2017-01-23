import usocket as socket
import ustruct as struct
import utime
import machine
import sys

from machine import RTC
from machine import Pin

global pins
pins = {}
for i in range(16):
    pins[i] = Pin('GP' + str(i), mode=Pin.OUT)

global wakeup
wakeup = False

def alarm_handler (rtc_o):
    global wakeup
    wakeup = True

class TwentyFourHourClock:
    # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
    NTP_DELTA = 3155673600

    def __init__(self, host):
        time = self.fetch_ntp_time(host)
        self.rtc = self.set_ntp_time(time)

    def fetch_ntp_time(self, host):
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1b
        addr = socket.getaddrinfo(host, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
        s.close()
        val = struct.unpack("!I", msg[40:44])[0]
        return val - self.NTP_DELTA

    def set_ntp_time(self, time):
        tm = utime.localtime(time)
        return RTC(datetime=tm)

class HalfDay:
    LIGHT_COUNT = 8
    MICROSECONDS_PER_DAY = 24 * 60 * 60 * 1000
    PERIODS_PER_DAY = 2 ** LIGHT_COUNT
    MICROSECONDS_PER_PERIOD = MICROSECONDS_PER_DAY // PERIODS_PER_DAY
    MAX_DISPLAY_STATE = PERIODS_PER_DAY - 1
    DISPLAY_FORMATTER = '{0:0' + str(LIGHT_COUNT) + 'b}'

    def __init__(self):
        self.display_state = 0
        pass

    def set_clock(self, clock):
        self.tfhc = clock

    def test(self):
        self.tfhc.rtc.alarm(
            time=1000,
            repeat=True)

        self.tick_interrupt = self.tfhc.rtc.irq(
            trigger=RTC.ALARM0,
            handler=alarm_handler,
            wake=machine.SLEEP | machine.IDLE)

    def tick(self):
        if self.display_state == self.MAX_DISPLAY_STATE:
            self.display_state -= self.MAX_DISPLAY_STATE
        else:
            self.display_state += 1

        for idx, val in enumerate(list(self.DISPLAY_FORMATTER.format(self.display_state))):
            pins[idx].value(int(val))

clock = TwentyFourHourClock('pool.ntp.org')

half_day = HalfDay()
half_day.set_clock(clock)
half_day.test()

while True:
    machine.idle()

    if wakeup == True:
        half_day.tick()
        wakeup = False
