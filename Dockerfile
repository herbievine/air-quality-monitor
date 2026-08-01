# syntax=docker/dockerfile:1
FROM python:3.13-slim-trixie AS builder

# lgpio (a dependency of rpi-lgpio, needed by Blinka on Pi 5) ships as a
# source distribution that swig-compiles against libgpio's headers/shared
# lib, which live in the Raspberry Pi apt repo rather than stock Debian.
# The keyring is vendored (docker/raspberrypi-archive-keyring.pgp) rather
# than fetched, since archive.raspberrypi.com only serves it inside a .deb.
COPY docker/raspberrypi-archive-keyring.pgp /usr/share/keyrings/raspberrypi-archive-keyring.pgp
RUN echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.pgp] http://archive.raspberrypi.com/debian/ trixie main" \
        > /etc/apt/sources.list.d/raspi.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        build-essential swig liblgpio-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY app/ ./app/

FROM python:3.13-slim-trixie

COPY docker/raspberrypi-archive-keyring.pgp /usr/share/keyrings/raspberrypi-archive-keyring.pgp
RUN echo "deb [signed-by=/usr/share/keyrings/raspberrypi-archive-keyring.pgp] http://archive.raspberrypi.com/debian/ trixie main" \
        > /etc/apt/sources.list.d/raspi.list \
    && apt-get update && apt-get install -y --no-install-recommends liblgpio1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
