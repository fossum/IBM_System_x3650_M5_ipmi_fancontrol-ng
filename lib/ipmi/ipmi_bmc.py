#!/usr/bin/env python3
"""IPMI BMC Module

This module provides high-level BMC reading and parsing functionality
for IPMI systems, built on top of the core IPMI executor.

Author: Enhanced for IBM System x3650 M5 IPMI Fan Control
License: See LICENSE file included with this distribution
"""

import re
import logging
from curses.ascii import isdigit

from .ipmi_tool import IPMIExecutor


class BMCReport:
    """IPMI BMC report."""

    logger = logging.getLogger(__name__)

    def __init__(self, report: str) -> None:
        """Initialize BMC report.

        Args:
            report: Raw BMC report string
        """
        self.raw_report = report

    def _require_row(self, substr: str) -> str:
        """Require a specific row from the BMC report."""
        for line in self.raw_report.splitlines():
            if substr in line:
                return line
        raise ValueError(f"Could not find row containing '{substr}' in:\n{self.raw_report}")

    @staticmethod
    def _parse_line(line: str) -> tuple[str, str]:
        """Splits a normal BMC line into key and value.

        Note: Does not work for multiline, such as Additional Device Support.
        """
        if (parts := line.split(":")) and len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        raise ValueError(f"Unable to parse '{line}'")

    @staticmethod
    def _parse_int(value: str) -> int:
        """Parse int value from int and hex.

        Example: 1045 (0x0415)

        Note: Unknown (0x415) will also result in 1045.
        """
        if all(isdigit(char) for char in value):
            return int(value)
        if (match := re.search(r"0x(\d+)", value)):
            return int(match.group(1), 16)
        raise ValueError(f"Unable to parse int from '{value}'.")

    @property
    def manufacturer_id(self) -> int:
        """Get the manufacturer ID from the raw report."""
        manufacturer_line: str | None = self._require_row("Manufacturer ID")
        value = BMCReport._parse_line(manufacturer_line)[1]
        return BMCReport._parse_int(value)

    @property
    def product_id(self) -> int:
        """Get the product ID from the raw report."""
        product_line: str | None = self._require_row("Product ID")
        value = BMCReport._parse_line(product_line)[1]
        return BMCReport._parse_int(value)


class BMCManager:
    """High-level interface for IPMI BMC operations.

    This class provides methods for reading and parsing BMC data,
    with specific support for temperature and fan sensors.
    """

    logger = logging.getLogger(__name__)

    def __init__(self, ipmi_executor: IPMIExecutor):
        """Initialize BMC manager.

        Args:
            ipmi_executor: IPMI command executor instance
        """
        self.ipmi = ipmi_executor

    def get_bmc_report(self) -> BMCReport:
        """Get the BMC report.

        Returns:
            BMCReport object containing the parsed report data.
        """
        output = self.ipmi.execute(["bmc", "info"])
        return BMCReport(output)
