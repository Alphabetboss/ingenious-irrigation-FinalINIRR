"""
moisture_sensor.py
Supports two modes:
  1) DIGITAL: on/off moisture module via a GPIO pin.
  2) ANALOG: capacitive sensor via MCP3008 ADC -> percentage 0..100.

Usage:
  from sensors.moisture_sensor import MoistureSensor
  ms = MoistureSensor(mode="ANALOG", mcp_channel=0)  # or mode="DIGITAL", pin=17
  pct = ms.read_percent()
"""

from __future__ import annotations
import os, time

# Hardware fallbacks so this works on Windows dev too
try:
    from gpiozero import MCP3008, InputDevice
    _HAVE_GPIOZERO = True
except Exception:
    _HAVE_GPIOZERO = False
    MCP3008 = InputDevice = None  # type: ignore

class MoistureSensor:
    def __init__(
        self,
        mode: str = None,
        pin: int | None = None,
        mcp_channel: int | None = None,
        dry_cal: float | None = None,
        wet_cal: float | None = None,
        samples: int = 5,
        sample_delay: float = 0.02,
    ):
        """
        mode: "DIGITAL" or "ANALOG". Default auto: ANALOG if MCP3008 available, else DIGITAL.
        pin: BCM pin for digital module (active_low = wet usually).
        mcp_channel: 0..7 for MCP3008 analog input.
        dry_cal/wet_cal: optional calibration raw values for 0%/100% mapping.
        """
        self.mode = (mode or os.getenv("MOISTURE_MODE") or "").upper()
        if not self.mode:
            self.mode = "ANALOG" if _HAVE_GPIOZERO else "DIGITAL"

        self.samples = samples
        self.sample_delay = sample_delay

        self.dry_cal = float(os.getenv("MOISTURE_DRY_CAL", dry_cal if dry_cal is not None else 0.0))
        self.wet_cal = float(os.getenv("MOISTURE_WET_CAL", wet_cal if wet_cal is not None else 1.0))

        if self.mode == "DIGITAL":
            self.pin = int(os.getenv("MOISTURE_PIN", pin if pin is not None else 17))
            if _HAVE_GPIOZERO:
                # Many digital modules pull LOW when wet
                self.dev = InputDevice(self.pin, pull_up=True)
            else:
                self.dev = None
        elif self.mode == "ANALOG":
            self.mcp_channel = int(os.getenv("MOISTURE_MCP_CH", mcp_channel if mcp_channel is not None else 0))
            if _HAVE_GPIOZERO:
                self.adc = MCP3008(channel=self.mcp_channel)  # value 0.0(dry?)..1.0(wet?) depends on sensor
            else:
                self.adc = None
        else:
            raise ValueError("mode must be DIGITAL or ANALOG")

    def _read_raw(self) -> float:
        if self.mode == "DIGITAL":
            if not _HAVE_GPIOZERO or self.dev is None:
                # Mock for dev on Windows
                return 0.0  # assume dry
            # InputDevice.is_active: True means pin pulled to GND; depends on wiring.
            # Convention: LOW when wet -> treat active as wet (1.0)
            return 1.0 if self.dev.is_active else 0.0
        else:
            if not _HAVE_GPIOZERO or self.adc is None:
                return 0.2  # mock analog raw
            return float(self.adc.value)  # 0..1

    def read_percent(self) -> float:
        vals = []
        for _ in range(max(1, self.samples)):
            vals.append(self._read_raw())
            time.sleep(self.sample_delay)
        raw = sum(vals) / len(vals)

        # Normalize using calibration; ensure sane order
        lo, hi = sorted((self.dry_cal, self.wet_cal))
        # Map raw in [lo,hi] -> [0,100]
        if hi - lo < 1e-6:
            pct = raw * 100.0
        else:
            pct = (raw - lo) / (hi - lo) * 100.0
        pct = max(0.0, min(100.0, pct))
        return pct

    def is_dry(self, threshold_pct: float = 30.0) -> bool:
        return self.read_percent() < threshold_pct
