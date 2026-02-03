import sys
from pathlib import Path
from time import sleep

LIB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIB_ROOT))

from test.connection import get_config

from ipmi.ipmi_tool import IPMIExecutor
from ipmi.ipmi_fans import FanController


if __name__ == "__main__":
    config = get_config()

    speed = 30  # Desired fan speed percentage

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

    max_bank = fans.max_fan_bank
    for bank in range(1, max_bank + 1):
        success = fans.set_fan_speed_raw(bank, speed)
        print(f"Set fan bank {bank} to {speed}%, success: {success}")
    sleep(30)

    sensors = fans.get_fans(refresh=True)
    for sensor in sensors:
        print(
            f"Sensor: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}, Status: {sensor.status}"
        )
