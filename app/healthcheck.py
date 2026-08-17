"""Container healthcheck: healthy only when every sensor value is landing in SQLite.

Run as `python -m app.healthcheck`; exits 0 (healthy) or 1 (unhealthy) and prints
the reason, which Docker surfaces in `docker inspect`.

The polling loop writes NULL for any sensor that didn't answer rather than
failing, so a container can look "up" for days while a sensor is dead - which is
exactly what happened when the SCD-41 and SGP41 dropped off the I2C bus. This
check treats that as unhealthy.
"""

import os
import sqlite3
import sys

from app.config import Config

# Every column the polling loop writes. A NULL in any of them means the
# corresponding sensor didn't answer on the most recent poll.
REQUIRED_COLUMNS = (
    "co2_ppm",
    "temp_c",
    "humidity_pct",
    "pm1_0",
    "pm2_5",
    "pm10",
    "voc_index",
    "nox_index",
)

# Age is computed by SQLite itself so this doesn't depend on the container
# clock agreeing with the timestamps the writer generated.
QUERY = f"""
SELECT (julianday('now') - julianday(ts)) * 86400.0 AS age_seconds,
       {", ".join(REQUIRED_COLUMNS)}
FROM readings
ORDER BY id DESC
LIMIT 1;
"""


def check() -> str | None:
    """Return None when healthy, or a message describing why it isn't."""
    config = Config.from_env()
    max_age_seconds = float(
        os.environ.get("HEALTHCHECK_MAX_AGE_SECONDS", config.poll_interval_seconds * 3)
    )

    # Read-only so a probe can never interfere with the writer; the timeout
    # rides out the brief lock held while a reading is being committed.
    try:
        conn = sqlite3.connect(f"file:{config.sqlite_path}?mode=ro", uri=True, timeout=5)
    except sqlite3.OperationalError as exc:
        return f"cannot open {config.sqlite_path}: {exc}"

    try:
        row = conn.execute(QUERY).fetchone()
    except sqlite3.OperationalError as exc:
        return f"cannot read readings table: {exc}"
    finally:
        conn.close()

    if row is None:
        return "no readings recorded yet"

    age_seconds, values = row[0], row[1:]

    if age_seconds > max_age_seconds:
        return f"last reading is {age_seconds:.0f}s old (max {max_age_seconds:.0f}s)"

    missing = [name for name, value in zip(REQUIRED_COLUMNS, values) if value is None]
    if missing:
        return f"last reading missing {', '.join(missing)}"

    return None


def main() -> int:
    problem = check()
    if problem:
        print(f"unhealthy: {problem}")
        return 1
    print("healthy: all sensor values present in the latest reading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
