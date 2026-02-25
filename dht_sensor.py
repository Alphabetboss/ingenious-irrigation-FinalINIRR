"""
dht_sensor.py
Reads temperature/humidity from DHT11/DHT22 using Adafruit_DHT, with retries.

Usage:
  from sensors.dht_sensor import DHTSensor
  d = DHTSensor(model="DHT22", pin=4)
  reading = d.read()
  -> {"humidity": 52.3, "temperature_c": 26.4, "temperature_f": 79.5, "ok": True}
"""

from __future__ import annotations
import os, time, math

try:
    import Adafruit_DHT  # type: ignore
    _HAVE_DHT = True
except Exception:
    _HAVE_DHT = False
    Adafruit_DHT = None  # type: ignore

_MODELS = {"DHT11": 11, "DHT22": 22, "AM2302": 22}

class DHTSensor:
    def __init__(self, model: str = None, pin: int | None = None, retries: int = 3, delay_s: float = 1.0):
        self.model = (model or os.getenv("DHT_MODEL") or "DHT22").upper()
        self.pin = int(os.getenv("DHT_PIN", pin if pin is not None else 4))
        self.retries = retries
        self.delay_s = delay_s

    def read(self) -> dict:
        if not _HAVE_DHT:
            # Dev fallback
            return {"humidity": 50.0, "temperature_c": 25.0, "temperature_f": 77.0, "ok": True, "mock": True}

        sensor = _MODELS.get(self.model, 22)
        humidity = temperature_c = None
        for _ in range(max(1, self.retries)):
            humidity, temperature_c = Adafruit_DHT.read_retry(sensor, self.pin)
            if humidity is not None and temperature_c is not None and 0.0 <= humidity <= 100.0:
                break
            time.sleep(self.delay_s)

        if humidity is None or temperature_c is None:
            return {"humidity": None, "temperature_c": None, "temperature_f": None, "ok": False}

        temperature_f = temperature_c * 9.0/5.0 + 32.0
        return {"humidity": float(humidity), "temperature_c": float(temperature_c), "temperature_f": float(temperature_f), "ok": True}
