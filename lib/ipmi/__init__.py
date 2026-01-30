"""High-level IPMI interface for fan control.

This module exposes `IPMIInterface` as a compatibility layer used by the
fan control logic and helper scripts.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from fan_config import FanConfig
from .ipmi_bmc import BMCManager
from .ipmi_sensors import SensorManager, SensorReading
from .ipmi_tool import IPMIConfig, IPMIConnectionMode, IPMIExecutor

__all__ = ["IPMIInterface"]


class IPMIInterface:
	"""High-level IPMI interface used by fan control logic.

	This class wraps the lower-level IPMI modules to provide a stable API
	for existing scripts while using the newer IPMI executor and managers.
	"""

	def __init__(self, config: FanConfig) -> None:
		"""Initialize the interface using configuration.

		Args:
			config: Fan configuration object.
		"""
		self._log = logging.getLogger(__name__)
		self._config = config
		self._ipmi = IPMIExecutor(self._build_ipmi_config(config))
		self._sensor_manager = SensorManager(self._ipmi)
		self._bmc_manager = BMCManager(self._ipmi)

	@staticmethod
	def _build_ipmi_config(config: FanConfig) -> IPMIConfig:
		ipmi_section = config.get_section("ipmi")
		connectmode = ipmi_section.get("connectmode", "open").lower()
		interface = IPMIConnectionMode.OPEN
		if connectmode == "lan":
			interface = IPMIConnectionMode.LAN
		elif connectmode in {"lanplus", "lan_plus", "lan+"}:
			interface = IPMIConnectionMode.LAN_PLUS

		return IPMIConfig(
			host=ipmi_section.get("host"),
			username=ipmi_section.get("username"),
			password=ipmi_section.get("password"),
			interface=interface,
			tool_path=ipmi_section.get("binary", "ipmitool"),
			timeout=int(ipmi_section.get("timeout", 30)),
		)

	def connect(self) -> bool:
		"""Validate the IPMI tool and connection settings.

		Returns:
			True if a connection test succeeds, False otherwise.
		"""
		return self._ipmi.test_connection()

	def close(self) -> None:
		"""Close the interface (no-op for ipmitool)."""
		return None

	def get_sensors(self, sensor_type: Optional[str] = None) -> tuple[SensorReading, ...]:
		"""Return sensor readings.

		Args:
			sensor_type: Optional sensor type (e.g. "Fan", "Temperature").

		Returns:
			Tuple of sensor readings.
		"""
		if not sensor_type:
			return self._sensor_manager.get_sensor_list()

		sensor_type_normalized = sensor_type.strip().lower()
		if sensor_type_normalized == "fan":
			return self._sensor_manager.get_fan_sensors()
		if sensor_type_normalized in {"temp", "temperature"}:
			return self._sensor_manager._get_sensors_by_type("temperature")

		return self._sensor_manager._get_sensors_by_type(sensor_type_normalized)

	def send_raw_command(self, netfn: int, cmd: int, data: Iterable[int]) -> bytes | None:
		"""Send a raw IPMI command.

		Args:
			netfn: IPMI NetFn value.
			cmd: IPMI command value.
			data: Iterable of data bytes.

		Returns:
			Response bytes if any, otherwise None.
		"""
		raw_command = [self._as_hex(netfn), self._as_hex(cmd)]
		raw_command.extend(self._as_hex(value) for value in data)
		output = self._ipmi.execute_raw(raw_command)
		return self._parse_raw_output(output)

	@staticmethod
	def _as_hex(value: int) -> str:
		if not 0 <= value <= 0xFF:
			raise ValueError("Raw command values must be between 0 and 255")
		return f"0x{value:02X}"

	@staticmethod
	def _parse_raw_output(output: str) -> bytes | None:
		if not output:
			return None
		try:
			parts = [part for part in output.split() if part]
			return bytes(int(part, 16) for part in parts)
		except ValueError:
			return None
