import sys

from test.connection import get_config

from ipmi.ipmi_tool import IPMIExecutor
from ipmi_thermals import ThermalManager


if __name__ == "__main__":
    # Example usage
    config = get_config()

    ipmi_executor = IPMIExecutor(config)
    if not ipmi_executor.test_connection():
        sys.stderr.write("IPMI connection failed\n")
        exit(1)

    thermals = ThermalManager(ipmi_executor)
    sensors = thermals.get_temperatures()
    for sensor in sensors:
        print(
            f"Sensor: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}, Status: {sensor.status}"
        )
