#!/usr/bin/env python3
"""IPMI Thermals Module

This module provides high-level thermal sensor reading functionality for IPMI systems.

License: See LICENSE file included with this distribution
"""

from ipmi.ipmi_sensors import SensorManager, SensorReading, SensorReport, Unit
from ipmi.ipmi_tool import IPMIExecutor


class Thermals:
    """High-level interface for IPMI thermal sensor operations."""

    def __init__(self, ipmi_exec: IPMIExecutor, sensor_report: SensorReport | None = None):
        """Initialize thermals.

        Args:
            ipmi_executor (IPMIExecutor): IPMI command executor instance.
        """
        self.ipmi = ipmi_exec
        self.sensor_report = sensor_report
        if sensor_report is None:
            sensor_manager = SensorManager(ipmi_exec)
            self.sensor_list = sensor_manager.get_sensor_list()
        else:
            self.sensor_list = self.sensor_report.sensors

    def get_temperatures(self, refresh: bool = False) -> tuple[SensorReading, ...]:
        """Get current temperature sensors.

        Args:
            refresh (bool): Whether to refresh sensor readings.
        """
        if refresh:
            sensor_manager = SensorManager(self.ipmi)
            self.sensor_list = sensor_manager.get_sensor_list()

        temps: list[SensorReading] = []
        for sensor in self.sensor_list:
            if (
                sensor.unit == Unit.DEGREES_C
            ):
                temps.append(sensor)

        return tuple(temps)
