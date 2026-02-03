import configparser
import logging
from os import PathLike
from pathlib import Path
from typing import Any

class FanConfig:
    def __init__(self, config_file: PathLike = 'config.conf'):
        self._log = logging.getLogger(__name__)
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        if self.config_file.exists():
            self.config.read(self.config_file)
        else:
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

    def get_value(self, section: str, key: str, default: Any = None) -> str:
        """Get a value from the configuration.

        Args:
            section (str): The section in the config file.
            key (str): The key within the section.
            default (Any, optional): The default value to return if the key is not found.

        Returns:
            str: The value from the config file or the default if not found.
        """
        try:
            return self.config[section][key]
        except KeyError:
            return default

    def get_section(self, section: str) -> dict[str, str]:
        """Get a section from the configuration.

        Args:
            section (str): The section in the config file.

        Returns:
            dict[str, str]: A dictionary of key-value pairs from the section.
        """
        return dict(self.config[section]) if section in self.config else {}

    def validate_config(self) -> bool:
        required_sections = ['system', 'ipmi', 'temperature_curve']
        for section in required_sections:
            if section not in self.config:
                self._log.error(f"Missing required section: [{section}]")
                return False
        # Optionally check for required keys here
        return True

    @property
    def preamble(self) -> str:
        ipmi = self.get_section('ipmi')
        preamble = ipmi.get('binary', 'ipmitool')
        if 'host' in ipmi:
            preamble += f" -H {ipmi['host']}"
        if 'username' in ipmi:
            preamble += f" -U {ipmi['username']}"
        if 'password' in ipmi:
            preamble += f" -P {ipmi['password']}"
        if 'connectmode' in ipmi:
            preamble += f" -I {ipmi['connectmode']}"
        return preamble
