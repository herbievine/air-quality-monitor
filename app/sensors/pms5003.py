"""PM1.0/PM2.5/PM10 via Plantower PMS5003 (UART).

Uses Adafruit's adafruit_pm25 driver (the official library for this exact
Adafruit product) for frame parsing/checksums, but talks to the serial port
via plain pyserial rather than Blinka's busio.UART. Blinka's bcm2712
uartPorts table maps board.TX/board.RX to hardware UART index 1 (resolving
to /dev/ttyAMA1 or /dev/serial1), but the Pi 5 `uart0-pi5` overlay used to
put PMS5003 on the GPIO header exposes it as /dev/ttyAMA0 instead - so
busio.UART can't find it. adafruit_pm25.uart.PM25_UART only calls
`.read(n)` on whatever "uart" object it's given, and pyserial's
serial.Serial.read(n) already matches that, so we hand it a Serial
instance directly.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

import serial
from adafruit_pm25.uart import PM25_UART

logger = logging.getLogger(__name__)

_BAUDRATE = 9600
_READ_TIMEOUT_SECONDS = 3
_RETRY_DELAY_SECONDS = 2


@dataclass
class Pms5003Reading:
    pm1_0: int
    pm2_5: int
    pm10: int


class Pms5003Sensor:
    def __init__(self, device: str):
        uart = serial.Serial(device, baudrate=_BAUDRATE, timeout=_READ_TIMEOUT_SECONDS)
        self._pm25 = PM25_UART(uart)
        self._lock = threading.Lock()
        self._latest: Optional[Pms5003Reading] = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def poll(self) -> Optional[Pms5003Reading]:
        with self._lock:
            return self._latest

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data = self._pm25.read()
            except RuntimeError as exc:
                logger.warning("PMS5003 read failed, retrying: %s", exc)
                time.sleep(_RETRY_DELAY_SECONDS)
                continue

            with self._lock:
                self._latest = Pms5003Reading(
                    pm1_0=data["pm10 standard"],
                    pm2_5=data["pm25 standard"],
                    pm10=data["pm100 standard"],
                )
