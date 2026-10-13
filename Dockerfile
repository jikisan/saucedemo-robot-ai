# Self-contained test runner: Python + Chromium + chromedriver from Debian (amd64 and arm64).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    # Chrome's sandbox needs privileges a container lacks; Debian's wrapper reads these flags.
    && echo 'export CHROMIUM_FLAGS="$CHROMIUM_FLAGS --no-sandbox --disable-dev-shm-usage"' \
       > /etc/chromium.d/docker-flags

# Point Selenium Manager at the installed browser and driver; never download.
ENV SE_BROWSER_PATH=/usr/bin/chromium \
    SE_OFFLINE=true \
    HEADLESS=true \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["robot", "-A", "robot.args", "tests"]
