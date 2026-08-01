"""MQTT publishing + Home Assistant MQTT discovery."""

import json
import logging

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

_DEVICE = {
    "identifiers": ["air_monitor"],
    "name": "Air Monitor",
    "manufacturer": "DIY",
    "model": "SCD-41 + SGP41 + PMS5003",
}

# (unique_id suffix, display name, unit, device_class, state_class, json key)
_SENSORS = [
    ("co2", "CO2", "ppm", "carbon_dioxide", "measurement", "co2_ppm"),
    ("temperature", "Temperature", "°C", "temperature", "measurement", "temp_c"),
    ("humidity", "Humidity", "%", "humidity", "measurement", "humidity_pct"),
    ("pm1_0", "PM1.0", "µg/m³", "pm1", "measurement", "pm1_0"),
    ("pm2_5", "PM2.5", "µg/m³", "pm25", "measurement", "pm2_5"),
    ("pm10", "PM10", "µg/m³", "pm10", "measurement", "pm10"),
    ("voc_index", "VOC Index", None, None, "measurement", "voc_index"),
    ("nox_index", "NOx Index", None, None, "measurement", "nox_index"),
]


class MqttPublisher:
    def __init__(self, host: str, port: int, state_topic: str, discovery_prefix: str):
        self._state_topic = state_topic
        self._discovery_prefix = discovery_prefix
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.connect(host, port)
        self._client.loop_start()
        self._publish_discovery_configs()

    def _publish_discovery_configs(self) -> None:
        for object_id, name, unit, device_class, state_class, json_key in _SENSORS:
            config = {
                "name": name,
                "unique_id": f"air_monitor_{object_id}",
                "state_topic": self._state_topic,
                "value_template": f"{{{{ value_json.{json_key} }}}}",
                "state_class": state_class,
                "device": _DEVICE,
            }
            if unit is not None:
                config["unit_of_measurement"] = unit
            if device_class is not None:
                config["device_class"] = device_class

            topic = f"{self._discovery_prefix}/sensor/air_monitor_{object_id}/config"
            self._client.publish(topic, json.dumps(config), retain=True)

    def publish_state(self, reading: dict) -> None:
        self._client.publish(self._state_topic, json.dumps(reading))

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
