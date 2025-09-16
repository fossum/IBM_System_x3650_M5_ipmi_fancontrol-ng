#!/usr/bin/env python3
"""
IPMI Sensor Module

This module provides high-level sensor reading and parsing functionality
for IPMI systems, built on top of the core IPMI executor.

Author: Enhanced for IBM System x3650 M5 IPMI Fan Control
License: See LICENSE file included with this distribution
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

from lib.ipmi_tool import (
    IPMIError, IPMIConfig, IPMIConnectionMode, IPMIExecutor
)


@dataclass
class SensorReading:
    """IPMI sensor reading."""
    name: str
    value: Optional[float]
    unit: Optional[str]
    status: Optional[str]
    lower_critical: Optional[float] = None
    lower_warning: Optional[float] = None
    upper_warning: Optional[float] = None
    upper_critical: Optional[float] = None


class SensorManager:
    """
    High-level interface for IPMI sensor operations.

    This class provides methods for reading and parsing sensor data,
    with specific support for temperature and fan sensors.
    """

    def __init__(self, ipmi_executor: IPMIExecutor):
        """
        Initialize sensor manager.

        Args:
            ipmi_executor: IPMI command executor instance
        """
        self.ipmi = ipmi_executor
        self.logger = logging.getLogger(__name__)

    def get_sensor_list(self) -> list[SensorReading]:
        """
        Get list of all sensors.

        Returns:
            List of sensor readings.
        """
        try:
            output = self.ipmi.execute(["sensor", "list"])
            sensors: list[SensorReading] = []

            for line in output.split('\n'):
                if '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 3:
                        sensor = SensorReading(
                            name=parts[0],
                            value=self._parse_float(parts[1]),
                            unit=parts[2] if parts[2] != 'na' else None,
                            status=(
                                parts[3]
                                if len(parts) > 3 and parts[3] != 'na'
                                else None
                            )
                        )
                        sensors.append(sensor)

            return sensors

        except IPMIError:
            self.logger.error("Failed to get sensor list")
            return []

    def get_temperature_sensors(self) -> list[SensorReading]:
        """
        Get temperature sensors only.

        Returns:
            List of temperature sensor readings.
        """
        sensors = self.get_sensor_list()
        return [s for s in sensors if s.unit and 'degrees' in s.unit.lower()]

    def get_cpu_temperatures(self) -> list[SensorReading]:
        """
        Get CPU temperature sensors.

        Returns:
            List of CPU temperature readings.
        """
        sensors = self.get_temperature_sensors()
        cpu_patterns = [r'cpu', r'processor', r'package', r'core']
        cpu_sensors: list[SensorReading] = []

        for sensor in sensors:
            for pattern in cpu_patterns:
                if re.search(pattern, sensor.name, re.IGNORECASE):
                    cpu_sensors.append(sensor)
                    break

        return cpu_sensors

    def get_max_cpu_temperature(self) -> Optional[float]:
        """
        Get maximum CPU temperature.

        Returns:
            Maximum CPU temperature in degrees Celsius, or None if no readings.
        """
        cpu_temps = self.get_cpu_temperatures()
        valid_temps = [s.value for s in cpu_temps if s.value is not None]

        return max(valid_temps) if valid_temps else None

    def get_fan_sensors(self) -> list[SensorReading]:
        """
        Get fan sensors.

        Returns:
            List of fan sensor readings.
        """
        sensors = self.get_sensor_list()
        return [s for s in sensors if 'fan' in s.name.lower()]

    def get_sensor_by_name(self, name: str) -> Optional[SensorReading]:
        """
        Get specific sensor by name.

        Args:
            name: Sensor name to search for

        Returns:
            Sensor reading if found, None otherwise.
        """
        sensors = self.get_sensor_list()
        for sensor in sensors:
            if sensor.name.lower() == name.lower():
                return sensor
        return None

    def get_sensors_by_pattern(self, pattern: str) -> list[SensorReading]:
        """
        Get sensors matching a regex pattern.

        Args:
            pattern: Regular expression pattern to match sensor names

        Returns:
            List of matching sensors.
        """
        sensors = self.get_sensor_list()
        matching_sensors: list[SensorReading] = []

        for sensor in sensors:
            if re.search(pattern, sensor.name, re.IGNORECASE):
                matching_sensors.append(sensor)

        return matching_sensors

    def get_bmc_info(self) -> dict[str, str]:
        """
        Get BMC information.

        Returns:
            Dictionary containing BMC information.
        """
        try:
            output = self.ipmi.execute(["bmc", "info"])
            info: dict[str, str] = {}

            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()

            return info

        except IPMIError:
            self.logger.error("Failed to get BMC info")
            return {}

    def get_sdr_list(self) -> list[dict[str, str | None]]:
        """
        Get Sensor Data Repository (SDR) list.

        Returns:
            List of SDR entries as dictionaries.
        """
        try:
            output = self.ipmi.execute(["sdr", "list", "full"])
            sdr_entries: list[dict[str, str | None]] = []

            for line in output.split('\n'):
                if '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                    if len(parts) >= 3:
                        entry: dict[str, str | None] = {
                            'id': parts[0],
                            'name': parts[1],
                            'type': parts[2],
                            'value': parts[3] if len(parts) > 3 else None
                        }
                        sdr_entries.append(entry)

            return sdr_entries

        except IPMIError:
            self.logger.error("Failed to get SDR list")
            return []

    def _parse_float(self, value: str) -> Optional[float]:
        """Parse string to float, return None if not parsable."""
        try:
            # Remove any non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d.-]', '', value)
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None


if __name__ == "__main__":
    from os import environ

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    config = IPMIConfig(
        host=environ.get('IPMI_HOST', "localhost"),
        username=environ.get('IPMI_USER', 'admin'),
        password=environ.get('IPMI_PASSWORD', 'password'),
        interface=IPMIConnectionMode.LAN_PLUS
    )

    # Create IPMI executor
    ipmi = IPMIExecutor(config)

    # Create sensor manager
    sensors = SensorManager(ipmi)

    # Test connection
    if ipmi.test_connection():
        print("IPMI connection successful")

        # Get BMC info
        bmc_info = sensors.get_bmc_info()
        print(f"BMC Version: {bmc_info.get('Firmware Revision', 'Unknown')}")

        # Get all temperature sensors
        temp_sensors = sensors.get_temperature_sensors()
        print(f"Found {len(temp_sensors)} temperature sensors")

        # Get CPU temperatures
        cpu_temps = sensors.get_cpu_temperatures()
        for temp in cpu_temps:
            print(f"CPU Temp: {temp.name} = {temp.value}°C")

        # Get max CPU temperature
        max_temp = sensors.get_max_cpu_temperature()
        print(f"Max CPU Temperature: {max_temp}°C")

        # Get fan sensors
        fan_sensors = sensors.get_fan_sensors()
        for fan in fan_sensors:
            print(f"Fan: {fan.name} = {fan.value} {fan.unit or ''}")

    else:
        print("IPMI connection failed")
