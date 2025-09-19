#!/usr/bin/env python3
"""
IPMI Command Executor

This module provides a low-level Python interface for executing IPMI commands.
It focuses solely on command line execution and basic connection management.

Author: Enhanced for IBM System x3650 M5 IPMI Fan Control
License: See LICENSE file included with this distribution
"""

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

# spell-checker:ignore: lanplus


class IPMIConnectionMode(Enum):
    """IPMI connection modes."""
    OPEN = "open"
    LAN = "lan"
    LAN_PLUS = "lanplus"


@dataclass
class IPMIConfig:
    """Configuration for IPMI connections."""
    host: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    interface: IPMIConnectionMode = IPMIConnectionMode.OPEN
    tool_path: str = "ipmitool"
    timeout: int = 30


class IPMIError(Exception):
    """Base exception for IPMI operations."""


class IPMIConnectionError(IPMIError):
    """Exception raised when IPMI connection fails."""


class IPMICommandError(IPMIError):
    """Exception raised when IPMI command execution fails."""


class IPMIExecutor:
    """Low-level IPMI command executor.

    This class provides methods for executing IPMI commands and managing
    connections, without any high-level logic for sensors or fans.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, config: Optional[IPMIConfig] = None):
        """Initialize IPMI command executor.

        Args:
            config: IPMI configuration. If None, uses local interface.
        """
        self.config = config or IPMIConfig()

        # Verify ipmitool is available
        if not self._check_tool_availability():
            raise IPMIError(f"IPMI tool not found at: {self.config.tool_path}")

    def _check_tool_availability(self) -> bool:
        """Check if ipmitool is available."""
        try:
            result = subprocess.run(
                ["which", self.config.tool_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _build_command(self, subcommand: Sequence[str]) -> List[str]:
        """Build IPMI command with proper authentication."""
        cmd = [self.config.tool_path]

        # Add interface if not local
        if self.config.interface != IPMIConnectionMode.OPEN:
            cmd.extend(["-I", self.config.interface.value])

        # Add connection details for remote hosts
        if self.config.host:
            cmd.extend(["-H", self.config.host])
        if self.config.username:
            cmd.extend(["-U", self.config.username])
        if self.config.password:
            cmd.extend(["-P", self.config.password])

        cmd.extend(subcommand)
        return cmd

    def execute(self, subcommand: Sequence[str]) -> str:
        """Execute IPMI command and return output.

        Args:
            subcommand: Sequence of command arguments (e.g., ["sensor", "list"])

        Returns:
            Command output as string

        Raises:
            IPMICommandError: If command execution fails
            IPMIConnectionError: If connection times out
            IPMIError: If tool is not found
        """
        cmd = self._build_command(subcommand)
        self.logger.debug(f"Executing IPMI command: {' '.join(cmd[:3])} ...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise IPMIConnectionError(
                f"IPMI command timed out after {self.config.timeout} seconds"
            ) from exc
        except FileNotFoundError as exc:
            raise IPMIError(f"IPMI tool not found: {self.config.tool_path}") from exc

        if result.returncode != 0:
            error_msg = f"IPMI command failed (exit {result.returncode}): {result.stderr.strip()}"
            self.logger.error(error_msg)
            raise IPMICommandError(error_msg)

        return result.stdout.strip()


    def execute_raw(self, raw_command: Sequence[str]) -> str:
        """Execute raw IPMI command.

        Args:
            raw_command: Raw command bytes/values (e.g., ["0x3a", "0x07", "1", "50", "0x01"])

        Returns:
            Command output as string
        """
        return self.execute(["raw"] + list(raw_command))

    def test_connection(self) -> bool:
        """Test IPMI connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            self.execute(["bmc", "info"])
            return True
        except (IPMIError, IPMIConnectionError, IPMICommandError) as e:
            return False

    def __str__(self) -> str:
        """String representation of IPMI executor."""
        if self.config.host:
            return f"IPMIExecutor(host={self.config.host}, interface={self.config.interface.value})"
        else:
            return "IPMIExecutor(local)"

    def __repr__(self) -> str:
        """Detailed representation of IPMI executor."""
        return f"IPMIExecutor(config={self.config})"
