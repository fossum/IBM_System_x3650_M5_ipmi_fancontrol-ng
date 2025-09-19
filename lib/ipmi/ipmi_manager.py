#!/usr/bin/env python3
"""IPMI Base Manager Module

This module provides base classes for other IPMI manager modules.

License: See LICENSE file included with this distribution
"""

import logging
from typing import TYPE_CHECKING

from .ipmi_tool import IPMIExecutor

if TYPE_CHECKING:
    from .ipmi_sensors import SensorReport, SensorReading


class BaseManager:
    """Base class for IPMI manager classes."""

    def __init__(self, ipmi_exec: IPMIExecutor):
        """Initialize BaseManager.

        Args:
            ipmi_exec (IPMIExecutor): IPMI command executor instance.
        """
        self.ipmi = ipmi_exec
        self.logger = logging.getLogger(self.__class__.__name__)


class SensorBasedManager(BaseManager):
    """Base class for manager classes that use sensor data."""

    _sensor_list: tuple['SensorReading', ...] = tuple()
    _sensor_report: 'SensorReport | None' = None
    _ipmi_exec_for_refresh: 'IPMIExecutor | None' = None

    def __init__(self, ipmi_exec: IPMIExecutor, sensor_report: 'SensorReport | None' = None):
        """Initialize SensorBasedManager.

        Args:
            ipmi_exec (IPMIExecutor): IPMI command executor instance.
            sensor_report (SensorReport, optional): A sensor report to use instead of fetching a new one. Defaults to None.
        """
        super().__init__(ipmi_exec)

        if not SensorBasedManager._ipmi_exec_for_refresh:
            SensorBasedManager._ipmi_exec_for_refresh = self.ipmi

        if sensor_report:
            if sensor_report is not SensorBasedManager._sensor_report:
                SensorBasedManager._sensor_report = sensor_report
                SensorBasedManager._sensor_list = sensor_report.sensors
        elif not SensorBasedManager._sensor_list:
            self.refresh_sensor_list()

    def refresh_sensor_list(self):
        """Refresh the shared sensor list from the IPMI interface."""
        if SensorBasedManager._sensor_report:
            raise TypeError("Cannot refresh sensor list when initialized with a static report.")

        if not SensorBasedManager._ipmi_exec_for_refresh:
            raise RuntimeError("No IPMI executor available to perform the refresh.")

        from .ipmi_sensors import SensorManager
        sensor_manager = SensorManager(SensorBasedManager._ipmi_exec_for_refresh)
        SensorBasedManager._sensor_list = sensor_manager.get_sensor_list()
        SensorBasedManager._sensor_report = None

    @property
    def sensor_list(self) -> tuple['SensorReading', ...]:
        """Get the shared sensor list."""
        return SensorBasedManager._sensor_list
