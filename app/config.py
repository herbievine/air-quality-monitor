import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    pms5003_serial_port: str
    poll_interval_seconds: float
    mqtt_host: str
    mqtt_port: int
    mqtt_state_topic: str
    mqtt_discovery_prefix: str
    sqlite_path: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            pms5003_serial_port=os.environ.get("PMS5003_SERIAL_PORT", "/dev/ttyAMA0"),
            poll_interval_seconds=float(os.environ.get("POLL_INTERVAL_SECONDS", "30")),
            mqtt_host=os.environ.get("MQTT_HOST", "mosquitto"),
            mqtt_port=int(os.environ.get("MQTT_PORT", "1883")),
            mqtt_state_topic=os.environ.get("MQTT_STATE_TOPIC", "airmonitor/state"),
            mqtt_discovery_prefix=os.environ.get("MQTT_DISCOVERY_PREFIX", "homeassistant"),
            sqlite_path=os.environ.get("SQLITE_PATH", "/app/data/air_quality.db"),
        )
