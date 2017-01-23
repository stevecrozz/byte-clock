import usocket as socket
import ustruct as struct
import utime
import machine
import sys

from machine import RTC
from machine import Pin

class TwentyFourHourClock:
    # (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
    NTP_DELTA = 3155673600

    def sync_with_retries(self, host, tries):
        for i in range(0, tries):
            try:
                self.sync(host)
            except TimeoutError:
                continue
            break

    def sync(self, host):
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

    def seconds_since_midnight(self):
        now = self.rtc.now()
        return now[3] * 24 * 60 + now[4] * 60 + now[5]

class Counter:
    LIGHT_COUNT = 8
    MICROSECONDS_PER_DAY = 24 * 60 * 60 * 1000
    PERIODS_PER_DAY = 2 ** LIGHT_COUNT
    MICROSECONDS_PER_PERIOD = MICROSECONDS_PER_DAY // PERIODS_PER_DAY
    MAX_DISPLAY_STATE = PERIODS_PER_DAY - 1

    def __init__(self, clock, display):
        self.tfhc = clock
        self.display = display
        self.tick_ready = False
        self.test()
        self.set_state()

    def handle_interrupt(self, rtc_o):
        self.tick_ready = True

    def set_clock(self, clock):
        self.tfhc = clock

    def set_state(self):
        seconds_since_midnight = self.tfhc.seconds_since_midnight()
        self.state = seconds_since_midnight // self.PERIODS_PER_DAY
        self.display.display(self.state)

    def test(self):
        self.tfhc.rtc.alarm(
            time=1000,
            repeat=True)

        self.tick_interrupt = self.tfhc.rtc.irq(
            trigger=RTC.ALARM0,
            handler=self.handle_interrupt,
            wake=machine.SLEEP | machine.IDLE)

    def set_interrupt(self):
        self.tfhc.rtc.alarm(
            time=self.MICROSECONDS_PER_PERIOD,
            repeat=True)

        self.tick_interrupt = self.tfhc.rtc.irq(
            trigger=RTC.ALARM0,
            handler=self.handle_interrupt,
            wake=machine.SLEEP | machine.IDLE)

    def run(self):
        while True:
            machine.idle()

            if self.tick_ready:
                self.tick_ready = False
                self.tick()

    def tick(self):
        if self.state == self.MAX_DISPLAY_STATE:
            self.state -= self.MAX_DISPLAY_STATE
        else:
            self.state += 1

        self.display.display(self.state)

class Display:
    PINS = {}

    def __init__(self, pin_count):
        self.DISPLAY_FORMATTER = '{0:0' + str(pin_count) + 'b}'

        for i in range(pin_count):
            self.PINS[i] = Pin('GP' + str(i), mode=Pin.OUT)

    def display(self, state):
        for i, v in enumerate(list(self.DISPLAY_FORMATTER.format(state))):
            self.PINS[i].value(int(v))

clock = TwentyFourHourClock()
clock.sync_with_retries('pool.ntp.org', 3)

display = Display(8)

counter = Counter(clock, display)
counter.run()
