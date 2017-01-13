import usocket as socket
import ustruct as struct
import utime
import machine

from machine import RTC
from machine import Pin

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600
host = "pool.ntp.org"

global pins;
pins = {}
for i in range(16):
    pins[i] = Pin('GP' + str(i), mode=Pin.OUT)

def gettime():
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

def alarm_handler (rtc_o):
    pins[0].toggle()
    pins[1].toggle()

t = gettime()
tm = utime.localtime(t)
rtc = RTC(datetime=tm)
rtc.alarm(time=1000, repeat=True)
rtc_i = rtc.irq(trigger=RTC.ALARM0, handler=alarm_handler, wake=machine.SLEEP | machine.IDLE)
