#!/usr/bin/env python3
"""IPMI Thermals Module

This module provides high-level thermal sensor reading functionality for IPMI systems.

License: See LICENSE file included with this distribution
"""

from ipmi.ipmi_sensors import SensorManager, SensorReading, SensorReport, Unit
from ipmi.ipmi_tool import IPMIExecutor
from ipmi.ipmi_manager import SensorBasedManager


class ThermalManager(SensorBasedManager):
    """High-level interface for IPMI thermal sensor operations."""

    def __init__(self, ipmi_exec: IPMIExecutor, sensor_report: SensorReport | None = None):
        """Initialize thermals.

        Args:
            ipmi_exec (IPMIExecutor): IPMI command executor instance.
        """
        super().__init__(ipmi_exec, sensor_report)

    def get_temperatures(self) -> tuple[SensorReading, ...]:
        """Get current temperature sensors."""
        temps: list[SensorReading] = []
        for sensor in self.sensor_list:
            if (
                sensor.unit == Unit.DEGREES_C
            ):
                temps.append(sensor)

        return tuple(temps)
