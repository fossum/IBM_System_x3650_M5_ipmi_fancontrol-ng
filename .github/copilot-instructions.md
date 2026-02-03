# IBM System x3650 M5 IPMI Fan Control – Copilot Instructions

## Big picture
- Two entry points: legacy Perl daemon [ipmi_fancontrol-ng](ipmi_fancontrol-ng) and Python modules in lib/ used by scripts like [temp_fan.py](temp_fan.py) and tests in lib/test/.
- Python IPMI stack:
	- Low-level executor: lib/ipmi/ipmi_tool.py (`IPMIExecutor`, `IPMIConfig`).
	- Parsers/managers: lib/ipmi/ipmi_sensors.py, lib/ipmi/ipmi_bmc.py.
	- Fan control: lib/ipmi_fans.py (`FanController`) using raw OEM netfn 0x3a cmd 0x07.
	- Fan curve logic: lib/fan.py (`Fan`) reads [config.conf](config.conf).

## Configuration and data flow
- INI-style config in [config.conf](config.conf) with sections [ipmi], [system], [temperature_curve]. Example in [config.conf.example](config.conf.example).
- Tests and scripts should treat lib/ as the package root (see sys.path usage in lib/test/).
- Metrics output file: `/tmp/fan_speed_telegraf` written by `Fan.update_fan_speed()`.

## Project-specific behaviors
- x3650 M5 has 6 physical fans, but OEM raw control only accepts fan banks 1–4 (see `FanController._CMD_CACHE` in lib/ipmi_fans.py). Banks 5–6 are implicitly tied to the controlled banks.
- Raw commands must be a list of hex byte strings (e.g., ["0x3a","0x07",...]); do not pass a single concatenated string.
- Sensor parsing supports both 10-column and 5-column ipmitool outputs (see lib/ipmi/ipmi_sensors.py).

## Workflows (hardware-dependent)
- Functional tests in lib/test/ talk to real IPMI hardware and require ipmitool + working IPMI access.
- Typical manual runs:
	- Python: use temp_fan.py or lib/test/ft_fans.py (reads config.conf via lib/test/connection.py).
	- Perl daemon: ipmi_fancontrol-ng.

## Conventions to follow
- Keep Python imports using lib as the package root (e.g., `from ipmi.ipmi_tool import IPMIExecutor`).
- Avoid introducing new dependencies unless needed for IPMI interaction.
