#!/usr/bin/env python3
"""IPMI Fan Control Module

This module provides high-level fan control functionality for IPMI systems,
specifically designed for IBM System x3650 M5 servers.

License: See LICENSE file included with this distribution
"""

import logging

from ipmi.ipmi_bmc import BMCManager
from ipmi.ipmi_sensors import SensorManager, SensorReading, SensorReport, Unit
from ipmi.ipmi_tool import IPMIExecutor, IPMIError


class FanController:
    """High-level interface for IPMI fan control operations.

    This class provides methods for controlling fan speeds using IPMI,
    with specific support for IBM System x3650 M5 servers.
    """

    # Manufacturer IDs as keys to
    # Product IDs as sub-keys to
    # Command sets as values
    _CMD_CACHE: dict[int, dict[int, dict[str, object]]] = {
        19046: {  # Lenovo
            # 3a == OEM NetFn for Lenovo/IBM systems
            # 7 == set the fan duty cycle
            1045: {
                "command": ["0x3a", "0x07"],
                "max_bank": 4,
            }  # x3650 M5
        }
    }

    _log = logging.getLogger(__name__)

    def __init__(self, ipmi_exec: IPMIExecutor, sensor_report: SensorReport | None = None):
        """Initialize fan controller.

        Args:
            ipmi_executor (IPMIExecutor): IPMI command executor instance.
        """
        self.ipmi = ipmi_exec
        self.sensor_report = sensor_report
        if sensor_report is None:
            sensor_manager = SensorManager(ipmi_exec)
            self.sensor_list = sensor_manager.get_fan_sensors()
        self._bmc_report = BMCManager(self.ipmi).get_bmc_report()
        self._max_fan_bank = self._get_max_fan_bank()

    @property
    def max_fan_bank(self) -> int:
        """Return the maximum supported fan bank for raw control."""
        return self._max_fan_bank

    def _get_max_fan_bank(self) -> int:
        manu_cmds = FanController._CMD_CACHE.get(self._bmc_report.manufacturer_id)
        if manu_cmds is None:
            return 0
        cmd_entry = manu_cmds.get(self._bmc_report.product_id)
        if not cmd_entry:
            return 0
        return int(cmd_entry.get("max_bank", 0))

    def set_fan_speed_raw(self, fan_bank: int, speed_percent: int) -> bool:
        """Set fan speed using raw IPMI command (for IBM x3650 M5).

        Args:
            fan_bank: Fan bank number (1-based)
            speed_percent: Fan speed percentage (0-100)

        Returns:
            True if successful, False otherwise.

        Raises:
            ValueError: If fan_bank or speed_percent are out of valid range
        """
        if not 0 <= speed_percent <= 100:
            raise ValueError("Speed percent must be between 0 and 100")

        if self._max_fan_bank and fan_bank > self._max_fan_bank:
            raise ValueError(
                f"Fan bank {fan_bank} is not supported; max bank is {self._max_fan_bank}"
            )

        # Find the correct raw command.
        raw_command: list[str] | None = None
        if (manu_cmds := FanController._CMD_CACHE.get(self._bmc_report.manufacturer_id)):
            if (cmd_entry := manu_cmds.get(self._bmc_report.product_id)):
                fan_cmd = cmd_entry.get("command")
                if isinstance(fan_cmd, list):
                    raw_command = list(fan_cmd)
                else:
                    raise ValueError(f"Invalid command format in cmd_entry: {fan_cmd}")
                raw_command.extend(
                    [
                        FanController.as_hex_byte_str(fan_bank),
                        FanController.as_hex_byte_str(speed_percent),
                        FanController.as_hex_byte_str(1),
                    ]
                )
        if not raw_command:
            raise ValueError("Unsupported manufacturer/product for raw fan control")

        try:
            self.ipmi.execute_raw(raw_command)
        except IPMIError as e:
            self._log.error(f"Failed to set fan bank {fan_bank} speed: {e}")
            return False
        self._log.info(f"Set fan bank {fan_bank} to {speed_percent}%")
        return True

    def set_all_fans_speed(self, speed_percent: int) -> bool:
        """Set speed for all fan banks.

        Args:
            speed_percent: Fan speed percentage (0-100)

        Returns:
            True if all successful, False if any failed.
        """
        success = True

        for bank in range(1, self.num_fan_banks + 1):
            if not self.set_fan_speed_raw(bank, speed_percent):
                success = False

        return success

    def get_fan_speeds(self, refresh: bool = False) -> tuple[float, ...]:
        """Get current fan speeds from sensors.

        Args:
            refresh (bool): Whether to refresh sensor readings.

        Returns:
            tuple of float: List of sensor readings with current speeds.
        """
        return tuple(float(sensor.value) for sensor in self.get_fans(refresh=refresh))

    def get_fans(self, refresh: bool = False) -> tuple[SensorReading, ...]:
        """Get current fan sensors.

        Args:
            refresh (bool): Whether to refresh sensor readings.
        """
        if refresh:
            sensor_manager = SensorManager(self.ipmi)
            self.sensor_list = sensor_manager.get_fan_sensors()
        fans: list[SensorReading] = []
        for sensor in self.sensor_list:
            if (
                'fan' in sensor.name.lower()
                and sensor.unit == Unit.RPM
            ):
                fans.append(sensor)

        return tuple(fans)

    def enter_full_speed_mode(self) -> bool:
        """Enter full fan speed mode.

        Returns:
            Bool: True if successful, False otherwise.
        """
        return self.set_all_fans_speed(100)

    @staticmethod
    def as_hex_byte_str(value: int) -> str:
        """Convert integer to hex byte string.

        Args:
            value: Integer value (0-255)

        Returns:
            Hex byte string (e.g., '0x1A')

        Raises:
            ValueError: If value is out of range.
        """
        if not 0 <= value <= 255:
            raise ValueError("Value must be between 0 and 255")
        return f"0x{value:02X}"
