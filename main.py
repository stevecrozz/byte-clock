import usocket as socket
import ustruct as struct
import utime
import machine
import sys

from machine import RTC
from machine import Pin

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600
host = "pool.ntp.org"
lightcnt = 8
seconds_per_day = 86400
periods_per_day = 2 ** lightcnt
seconds_per_period = seconds_per_day // periods_per_day

global display_state
display_state = 0

global max_display_state
max_display_state = periods_per_day - 1

global display_formatter
display_formatter = '{0:0' + str(lightcnt) + 'b}'

global pins
pins = {}
for i in range(16):
    pins[i] = Pin('GP' + str(i), mode=Pin.OUT)

global wakeup
wakeup = False

def tick():
    global display_state

    if display_state == max_display_state:
        display_state -= max_display_state
    else:
        display_state += 1

    for idx, val in enumerate(list(display_formatter.format(display_state))):
        pins[idx].value(int(val))

def alarm_handler (rtc_o):
    global wakeup
    wakeup = True

class TwentyFourHourClock:
    def __init__(self):
        time = self.fetch_ntp_time()
        self.rtc = self.set_ntp_time(time)

    def fetch_ntp_time(self):
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1b
        addr = socket.getaddrinfo(host, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
        s.close()
        val = struct.unpack("!I", msg[40:44])[0]
        return val - NTP_DELTA

    def set_ntp_time(self, time):
        tm = utime.localtime(time)
        return RTC(datetime=tm)

clock = TwentyFourHourClock()

clock.rtc.alarm(time=1000, repeat=True)
rtc_i = clock.rtc.irq(trigger=RTC.ALARM0, handler=alarm_handler, wake=machine.SLEEP | machine.IDLE)

while True:
    machine.idle()

    if wakeup == True:
        tick()
        wakeup = False
