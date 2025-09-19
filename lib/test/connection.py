"""Module to handle IPMI connection configuration."""

import configparser
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ipmi.ipmi_tool import IPMIConfig, IPMIConnectionMode

CONFIG_FILE_PATH = Path(__file__).parent.parent / 'config.ini'


def get_config() -> Optional[IPMIConfig]:
    """Get IPMI configuration from environment or config file.

    Priority:
    1. config.ini file
    2. Environment variables
    """
    config = get_ipmi_config_from_env()
    if (config_file := get_ipmi_config_from_file()) is not None:
        for key, value in config_file.__dict__.items():
            if value is not None:
                setattr(config, key, value)
    return config


def get_ipmi_config_from_env() -> IPMIConfig:
    """Get IPMI configuration from environment variables.

    Environment variables:
    - IPMI_HOST
    - IPMI_USERNAME
    - IPMI_PASSWORD
    - IPMI_INTERFACE (open, lan, lanplus)
    - IPMI_TOOL_PATH
    - IPMI_TIMEOUT
    """
    host = os.environ.get('IPMI_HOST')
    username = os.environ.get('IPMI_USERNAME')
    password = os.environ.get('IPMI_PASSWORD')
    interface_str = os.environ.get('IPMI_INTERFACE', 'open').lower()
    tool_path = os.environ.get('IPMI_TOOL_PATH', 'ipmitool')
    timeout = int(os.environ.get('IPMI_TIMEOUT', '30'))

    interface = IPMIConnectionMode.OPEN
    if interface_str == 'lan':
        interface = IPMIConnectionMode.LAN
    elif interface_str == 'lanplus':
        interface = IPMIConnectionMode.LAN_PLUS

    return IPMIConfig(
        host=host,
        username=username,
        password=password,
        interface=interface,
        tool_path=tool_path,
        timeout=timeout
    )


def get_ipmi_config_from_file(
    config_file: Path = CONFIG_FILE_PATH
) -> Optional[IPMIConfig]:
    """Get IPMI configuration from a config.ini file.

    The file should have a section [ipmi] with keys:
    - host
    - username
    - password
    - interface (open, lan, lanplus)
    - tool_path
    - timeout
    """
    config = configparser.ConfigParser()
    if not config_file.exists():
        return None

    config.read(config_file)

    if 'ipmi' not in config:
        return None

    ipmi_section = config['ipmi']

    ipmi_config = IPMIConfig()
    for key in IPMIConfig.__annotations__.keys():
        if key in ipmi_section:
            setattr(ipmi_config, key, ipmi_section[key])

    return ipmi_config
