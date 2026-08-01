# One-time Pi setup

This Pi (Raspberry Pi 5, Debian 13 "trixie") needs I2C and a second UART
enabled before the sensors are usable. Neither is on by default.

## 1. Enable I2C and the header UART

Edit `/boot/firmware/config.txt`:

```diff
-#dtparam=i2c_arm=on
+dtparam=i2c_arm=on
```

and add, anywhere below the `[all]` line:

```
dtoverlay=uart0-pi5
```

`uart0-pi5` puts a UART on GPIO14/15 (physical pins 8/10) as its own device,
separate from the Pi 5's debug-console UART (`/dev/ttyAMA10`/`serial0`), so
you do **not** need to disable the console to use it.

Reboot: `sudo reboot`

## 2. Verify

```
ls /dev/i2c-*      # expect /dev/i2c-1
ls -la /dev/ttyAMA0  # expect this to now exist
```

If `/dev/ttyAMA0` isn't there, double check the overlay line was added and
that you rebooted (`dtoverlay` changes only take effect on boot).

## 3. Wiring

STEMMA QT / Qwiic cable or jumper wires from the 40-pin header:

| Signal | SCD-41 / SGP41 (I2C, daisy-chained) | Pi pin |
|---|---|---|
| 3.3V | VIN | Pin 1 |
| GND | GND | Pin 9 |
| SDA | SDA | Pin 3 (GPIO2) |
| SCL | SCL | Pin 5 (GPIO3) |

| Signal | PMS5003 | Pi pin |
|---|---|---|
| 5V | VCC | Pin 4 |
| GND | GND | Pin 6 |
| TX (sensor) | → Pi RX | Pin 10 (GPIO15) |
| RX (sensor) | ← Pi TX | Pin 8 (GPIO14) |

The PMS5003 breadboard adapter kit has no enable/reset pins wired, which is
fine — the driver we use (`adafruit_pm25`) doesn't require them.

## 4. Bring the stack up

```
docker compose up -d --build
docker compose logs -f air-monitor
```

Expect a log line every `POLL_INTERVAL_SECONDS` (default 30s) once the SGP41
finishes its ~10s startup conditioning.

## 5. Check the data

SQLite (from the host, since `./data` is bind-mounted):
```
sqlite3 data/air_quality.db "select * from readings order by ts desc limit 5;"
```

MQTT (from the host, install `mosquitto-clients` if needed: `sudo apt install mosquitto-clients`):
```
mosquitto_sub -h localhost -t 'airmonitor/#' -v
```

## 6. Adding Home Assistant later

Whenever Home Assistant is set up (on this Pi or elsewhere on the LAN), add
the MQTT integration and point it at this Pi's IP, port 1883, no
credentials (the bundled Mosquitto currently allows anonymous connections —
fine on a trusted home LAN, but add a username/password in
`mosquitto/mosquitto.conf` if that's ever not true). An "Air Monitor" device
with 8 sensors (CO2, temperature, humidity, PM1.0/2.5/10, VOC index, NOx
index) will appear automatically — no manual entity YAML needed, since
`app/mqtt_client.py` publishes Home Assistant MQTT discovery configs on
startup.

## Notes / tradeoffs

- **Anonymous MQTT**: simplest for a first pass. Add `password_file` to
  `mosquitto/mosquitto.conf` and update `MQTT_HOST`/credentials in `.env` if
  you want auth later.
- **Device mappings, not `--privileged`**: `docker-compose.yml` maps the
  specific device nodes needed (`/dev/i2c-1`, `/dev/gpiochip0`,
  `/dev/ttyAMA0`) rather than the whole `/dev` tree. The container runs as
  root internally, so it doesn't need matching host group IDs to read them.
- **`BLINKA_FORCECHIP`/`BLINKA_FORCEBOARD`**: unprivileged containers can't
  see `/sys/firmware/devicetree`, which is how Blinka normally autodetects
  the board, so `docker-compose.yml` forces the values (confirmed by
  running the same detection natively on this Pi).
- **`setuptools<81`**: Blinka's `board.py` still imports the deprecated
  `pkg_resources` module (from `setuptools`) at import time. Setuptools
  81+ dropped it, which breaks `import board` with `ModuleNotFoundError`.
  Pinned in `pyproject.toml` until upstream Blinka drops the dependency.
