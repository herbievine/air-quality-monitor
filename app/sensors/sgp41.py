"""VOC/NOx index via Sensirion SGP41 (I2C).

The gas index algorithm needs raw ticks fed at a steady 1 Hz to build an
accurate rolling baseline, and the chip needs ~10s of conditioning() calls
right after power-up before its output is meaningful. Both run in a
dedicated background thread so the main polling loop (which runs on a much
slower cadence) can just read whatever the latest computed index is.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import board
from adafruit_sgp41.sgp41 import SGP41

logger = logging.getLogger(__name__)

_CONDITIONING_SECONDS = 10
_SAMPLE_INTERVAL_SECONDS = 1.0
_DEFAULT_TEMP_C = 25.0
_DEFAULT_HUMIDITY_PCT = 50.0

CompensationSource = Callable[[], Optional[Tuple[float, float]]]


@dataclass
class Sgp41Reading:
    voc_index: int
    nox_index: int


class Sgp41Sensor:
    def __init__(self, i2c: board.I2C, compensation_source: Optional[CompensationSource] = None):
        self._sensor = SGP41(i2c)
        self._compensation_source = compensation_source
        self._lock = threading.Lock()
        self._latest: Optional[Sgp41Reading] = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def poll(self) -> Optional[Sgp41Reading]:
        with self._lock:
            return self._latest

    def _compensation(self) -> Tuple[float, float]:
        if self._compensation_source is not None:
            values = self._compensation_source()
            if values is not None:
                return values
        return _DEFAULT_TEMP_C, _DEFAULT_HUMIDITY_PCT

    def _run(self) -> None:
        logger.info("SGP41 conditioning for %ds...", _CONDITIONING_SECONDS)
        for _ in range(_CONDITIONING_SECONDS):
            if self._stop.is_set():
                return
            temp_c, humidity_pct = self._compensation()
            self._sensor.conditioning(humidity=humidity_pct, temperature=temp_c)
            time.sleep(_SAMPLE_INTERVAL_SECONDS)

        logger.info("SGP41 conditioning complete, starting index measurement loop")
        while not self._stop.is_set():
            temp_c, humidity_pct = self._compensation()
            voc_index, nox_index = self._sensor.measure_index(humidity=humidity_pct, temperature=temp_c)
            with self._lock:
                self._latest = Sgp41Reading(voc_index=voc_index, nox_index=nox_index)
            time.sleep(_SAMPLE_INTERVAL_SECONDS)
