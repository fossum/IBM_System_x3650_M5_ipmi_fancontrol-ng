import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ipmi import IPMIInterface


class CPU:
    """Helper class to read and parse temperatures from IPMI sensors."""

    _log = logging.getLogger(__name__)

    def __init__(self, ipmi: "IPMIInterface") -> None:
        self._ipmi = ipmi

    def get_cpu_temps(self) -> tuple[float, ...]:
        """Return the CPU temperatures reported by IPMI sensors."""
        try:
            sensors = self._ipmi.get_sensors(sensor_type="Temperature")
        except Exception as exc:
            self._log.error("Failed to read IPMI temperature sensors: %s", exc)
            raise RuntimeError("IPMI sensor read failure") from exc

        cpu_temps: list[float] = []
        fallback_temps: list[float] = []
        for sensor in sensors:
            # Skip sensors with no value.
            if sensor.value is None:
                continue
            # Make sure the value can be converted to float.
            try:
                value = float(sensor.value)
            except (TypeError, ValueError):
                continue
            # Identify CPU temperature sensors.
            name = sensor.name.lower()
            if (
                "cpu" in name
                and "temp" in name
                and "vr" not in name    # Exclude voltage regulator temps.
            ):
                cpu_temps.append(value)
            else:
                fallback_temps.append(value)

        if cpu_temps:
            return tuple(cpu_temps)
        if fallback_temps:
            return tuple(fallback_temps)
        return ()

    def detect_number_of_cpus(self) -> int:
        """Detects the number of CPUs by querying IPMI sensors."""
        self._log.debug("Detecting number of CPUs...")
        cpu_sensors = self._ipmi.get_sensors(sensor_type='Processor')
        self._log.debug("--- Found IPMI CPU Sensors ---")
        for sensor in cpu_sensors:
            self._log.debug(f"  - Name: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}")
        self._log.debug("------------------------------")
        return len(cpu_sensors)
