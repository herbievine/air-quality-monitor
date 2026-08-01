"""CO2/temperature/humidity via Sensirion SCD-41 (I2C)."""

import threading
from dataclasses import dataclass
from typing import Optional

import adafruit_scd4x
import board


@dataclass
class Scd41Reading:
    co2_ppm: int
    temp_c: float
    humidity_pct: float


class Scd41Sensor:
    def __init__(self, i2c: board.I2C):
        self._sensor = adafruit_scd4x.SCD4X(i2c)
        self._sensor.start_periodic_measurement()
        self._lock = threading.Lock()
        self._latest: Optional[Scd41Reading] = None

    def poll(self) -> Optional[Scd41Reading]:
        """Reads a new value if the sensor has one ready (updates ~every 5s), else returns the last known reading."""
        with self._lock:
            if self._sensor.data_ready:
                self._latest = Scd41Reading(
                    co2_ppm=self._sensor.CO2,
                    temp_c=self._sensor.temperature,
                    humidity_pct=self._sensor.relative_humidity,
                )
            return self._latest
