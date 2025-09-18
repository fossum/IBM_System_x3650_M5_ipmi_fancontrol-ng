#!/usr/bin/env python3
"""
IPMI Sensor Module

This module provides high-level sensor reading and parsing functionality
for IPMI systems, built on top of the core IPMI executor.

Author: Enhanced for IBM System x3650 M5 IPMI Fan Control
License: See LICENSE file included with this distribution
"""

from curses.ascii import isdigit, isxdigit
from enum import StrEnum, auto
import re
import logging
from typing import Optional
from dataclasses import dataclass

from .ipmi_tool import IPMIExecutor


class Unit(StrEnum):
    """Enumeration of sensor units."""
    VOLTS = auto()
    WATTS = auto()
    DEGREES_C = "degrees c"
    RPM = auto()
    DISCRETE = auto()
    NOT_APPLICABLE = "na"
    UNSPECIFIED = auto()


@dataclass
class SensorReading:
    """IPMI sensor reading."""
    name: str
    value: float | int | str
    unit: Unit
    status: str | int | None
    lower_non_recoverable: float | None = None
    lower_critical: float | None = None
    lower_non_critical: float | None = None
    upper_non_recoverable: float | None = None
    upper_critical: float | None = None
    upper_non_critical: float | None = None


class SensorReport:
    """IPMI sensor report."""

    logger = logging.getLogger(__name__)

    def __init__(self, report: str) -> None:
        """Initialize sensor report.

        Args:
            report: Raw sensor report string
        """
        self.raw_report = report

    @property
    def sensors(self) -> tuple[SensorReading, ...]:
        """Get list of all sensors.

        Returns:
            Tuple of sensor readings.
        """
        sensors: list[SensorReading] = []

        for line in self.raw_report.splitlines():
            sensor = self._parse_line(line)
            if sensor:
                sensors.append(sensor)

        return tuple(sensors)

    @staticmethod
    def _parse_line(line: str) -> Optional[SensorReading]:
        """Parse a line of sensor output into a SensorReading object.

        Args:
            line: A line of sensor output

        Returns:
            SensorReading object or None if parsing fails.
        """
        parts = [part.strip() for part in line.split('|')]
        sensor: SensorReading | None = None
        if len(parts) == 10:
            if parts[1].lower() not in ('na'):
                sensor = SensorReading(
                    name=parts[0],
                    value=SensorReport._parse_value(parts[1]),
                    unit=Unit(parts[2].lower()),
                    status=SensorReport._parse_value(parts[3]),
                    lower_non_recoverable=SensorReport._parse_value(parts[4]),
                    lower_critical=SensorReport._parse_value(parts[5]),
                    lower_non_critical=SensorReport._parse_value(parts[6]),
                    upper_non_critical=SensorReport._parse_value(parts[7]),
                    upper_critical=SensorReport._parse_value(parts[8]),
                    upper_non_recoverable=SensorReport._parse_value(parts[9]),
                )
        else:
            SensorReport.logger.warning(f"Unexpected sensor report format: {line}")
        return sensor

    @staticmethod
    def _parse_value(value: str) -> str | float | int | None:
        """Parse a sensor value string into appropriate type.

        Args:
            value: Sensor value string

        Returns:
            Parsed value as float, int, str
        """
        if all(isdigit(char) for char in value):
            return int(value)
        elif value.startswith('0x') and all(isxdigit(char) for char in value[2:]):
            return int(value, 16)
        elif re.match(r'^-?\d+\.\d+$', value):
            return float(value)
        else:
            return value if value.lower() != 'na' else None


class SensorManager:
    """High-level interface for IPMI sensor operations.

    This class provides methods for reading and parsing sensor data,
    with specific support for temperature and fan sensors.
    """

    def __init__(self, ipmi_executor: IPMIExecutor):
        """Initialize sensor manager.

        Args:
            ipmi_executor: IPMI command executor instance
        """
        self.ipmi = ipmi_executor
        self.logger = logging.getLogger(__name__)

    def get_sensor_list(self) -> tuple[SensorReading, ...]:
        """Get list of all sensors.

        Returns:
            Tuple of sensor readings.
        """
        output = self.ipmi.execute(["sensor"])

        sensors = SensorReport(output).sensors
        return sensors

