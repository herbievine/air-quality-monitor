import logging
import time

import board
import serial

from app.config import Config
from app.db import Database
from app.mqtt_client import MqttPublisher
from app.sensors.pms5003 import Pms5003Sensor
from app.sensors.scd41 import Scd41Sensor
from app.sensors.sgp41 import Sgp41Sensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    config = Config.from_env()
    logger.info("Starting air-monitor with config: %s", config)

    db = Database(config.sqlite_path)
    mqtt_publisher = MqttPublisher(
        host=config.mqtt_host,
        port=config.mqtt_port,
        state_topic=config.mqtt_state_topic,
        discovery_prefix=config.mqtt_discovery_prefix,
    )

    i2c = board.I2C()

    try:
        scd41 = Scd41Sensor(i2c)
    except (ValueError, OSError) as exc:
        logger.warning("SCD-41 not found, continuing without CO2/temp/humidity: %s", exc)
        scd41 = None

    def scd41_compensation():
        reading = scd41.poll() if scd41 else None
        if reading is None:
            return None
        return reading.temp_c, reading.humidity_pct

    try:
        sgp41 = Sgp41Sensor(i2c, compensation_source=scd41_compensation)
        sgp41.start()
    except (ValueError, OSError) as exc:
        logger.warning("SGP41 not found, continuing without VOC/NOx: %s", exc)
        sgp41 = None

    try:
        pms5003 = Pms5003Sensor(config.pms5003_serial_port)
        pms5003.start()
    except serial.SerialException as exc:
        logger.warning("PMS5003 not found, continuing without PM readings: %s", exc)
        pms5003 = None

    if scd41 is None and sgp41 is None and pms5003 is None:
        logger.error("No sensors detected, nothing to do - exiting")
        mqtt_publisher.close()
        db.close()
        return

    logger.info("Entering polling loop (every %ss)", config.poll_interval_seconds)
    try:
        while True:
            scd41_reading = scd41.poll() if scd41 else None
            sgp41_reading = sgp41.poll() if sgp41 else None
            pms5003_reading = pms5003.poll() if pms5003 else None

            row = {
                "co2_ppm": scd41_reading.co2_ppm if scd41_reading else None,
                "temp_c": scd41_reading.temp_c if scd41_reading else None,
                "humidity_pct": scd41_reading.humidity_pct if scd41_reading else None,
                "pm1_0": pms5003_reading.pm1_0 if pms5003_reading else None,
                "pm2_5": pms5003_reading.pm2_5 if pms5003_reading else None,
                "pm10": pms5003_reading.pm10 if pms5003_reading else None,
                "voc_index": sgp41_reading.voc_index if sgp41_reading else None,
                "nox_index": sgp41_reading.nox_index if sgp41_reading else None,
            }

            logger.info("Reading: %s", row)
            db.insert_reading(row)
            mqtt_publisher.publish_state(row)

            time.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        if sgp41:
            sgp41.stop()
        if pms5003:
            pms5003.stop()
        mqtt_publisher.close()
        db.close()


if __name__ == "__main__":
    main()
