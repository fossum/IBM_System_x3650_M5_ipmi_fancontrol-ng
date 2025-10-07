import sys
from time import sleep

sys.path.append("lib")

from test.connection import get_config

from ipmi.ipmi_tool import IPMIExecutor
from ipmi_fans import FanController


if __name__ == "__main__":
    # Example usage
    config = get_config()

    ipmi_executor = IPMIExecutor(config)
    if not ipmi_executor.test_connection():
        sys.stderr.write("IPMI connection failed\n")
        exit(1)

    fans = FanController(ipmi_executor)
    sensors = fans.get_fans()
    for sensor in sensors:
        print(
            f"Sensor: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}, Status: {sensor.status}"
        )

    fans.set_fan_speed_raw(1, 99)
    sleep(5)

    sensors = fans.get_fans(refresh=True)
    for sensor in sensors:
        print(
            f"Sensor: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}, Status: {sensor.status}"
        )
