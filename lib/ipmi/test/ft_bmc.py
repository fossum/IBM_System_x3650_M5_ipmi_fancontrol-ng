import sys

from test.connection import get_config

from ipmi.ipmi_tool import IPMIExecutor
from ipmi.ipmi_bmc import BMCManager


if __name__ == "__main__":
    # Example usage
    config = get_config()

    ipmi_executor = IPMIExecutor(config)
    if not ipmi_executor.test_connection():
        sys.stderr.write("IPMI connection failed\n")
        exit(1)

    bmc_manager = BMCManager(ipmi_executor)
    bmc_report = bmc_manager.get_bmc_report()
    print(f"Manufacturer ID: {bmc_report.manufacturer_id}")
    print(f"Product ID: {bmc_report.product_id}")
