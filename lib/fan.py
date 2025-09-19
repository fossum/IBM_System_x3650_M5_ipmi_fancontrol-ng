import logging
from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from .fanconfig import FanConfig
    from .ipmi import IPMIInterface


class Fan:
    log = logging.getLogger(__name__)

    def __init__(self, config: "FanConfig", ipmi: "IPMIInterface"):
        self.config = config
        self.ipmi = ipmi

        # Load non-IPMI settings from config
        system_config = self.config.get_section('system')
        self.number_of_fanbanks = int(system_config.get('number_of_fanbanks', 1))
        self.min_temp_change = float(system_config.get('min_temp_change', 0))
        self.hostname = system_config.get('hostname', 'localhost')

        # Initialize state
        self.current_fan_duty_cycle = 0
        self.current_cpu_temp = 0
        self.current_gpu_temp = 0
        self.last_set_cpu_temp = 0
        self.last_set_gpu_temp = 0
        self.cpu_temp_to_fan_speed = {}
        self.cpu_temp_scale = {}

        self._load_temperature_curve()
        self._calculate_scalars()

    def _load_temperature_curve(self):
        curve = self.config.get_section('temperature_curve')
        for key, value in curve.items():
            if key.startswith('temp_'):
                try:
                    temp = int(key.split('_')[1])
                    self.cpu_temp_to_fan_speed[temp] = float(value)
                except (ValueError, IndexError):
                    self.log.warning(f"Could not parse temperature curve entry: {key}={value}")

    def _internal_do_set_fan_speed(self, fan_speed: float):
        for i in range(1, self.number_of_fanbanks + 1):
            self.log.info(f"Setting FanBank n°{i} speed to {fan_speed}%")
            # IPMI raw command to set fan speed for IBM System x3650 M5
            # netfn=0x3a, cmd=0x07, data=[bank, speed, 0x01]
            self.ipmi.send_raw_command(netfn=0x3a, cmd=0x07, data=[i, int(fan_speed), 0x01])

    def set_fan_speed(self, fan_speed: float):
        cpu_temp_difference = self.current_cpu_temp - self.last_set_cpu_temp
        gpu_temp_difference = self.current_gpu_temp - self.last_set_gpu_temp
        if abs(cpu_temp_difference) > self.min_temp_change or abs(gpu_temp_difference) > self.min_temp_change:
            print("\n********************** Updating Fan Speeds **********************")
            print(f"We last updated fan speed {cpu_temp_difference}°C ago (CPU Temperature).")
            print(f"We last updated fan speed {gpu_temp_difference}°C ago (GPU Temperature).")
            print(f"Current CPU Temperature is {self.current_cpu_temp}°C.")
            print(f"Current GPU Temperature is {self.current_gpu_temp}°C.")
            print("*****************************************************************")
            self.last_set_cpu_temp = self.current_cpu_temp
            self.last_set_gpu_temp = self.current_gpu_temp
            self.current_fan_duty_cycle = fan_speed
            self._internal_do_set_fan_speed(fan_speed)

    def _calculate_scalars(self):
        previous = None
        for a in sorted(self.cpu_temp_to_fan_speed.keys()):
            current = (a, self.cpu_temp_to_fan_speed[a])
            if previous:
                try:
                    m = (current[1] - previous[1]) / (current[0] - previous[0])
                    b = current[1] - (m * current[0])
                    self.cpu_temp_scale[a] = (m, b)
                except ZeroDivisionError:
                    self.log.warning(f"Cannot calculate slope for temp {a}; duplicate temperature points in config?")
            previous = current

    def calculate_desired_fan_speed(self, current_cpu_temp: float) -> Tuple[float, float]:
        desired_fan_speed = 0
        calculated_speed = 0

        # Find the correct temperature range for interpolation
        for temp_threshold in sorted(self.cpu_temp_scale.keys(), reverse=True):
            if current_cpu_temp <= temp_threshold:
                m, b = self.cpu_temp_scale[temp_threshold]
                calculated_speed = (m * current_cpu_temp) + b
                desired_fan_speed = round(calculated_speed)
                break # Found the correct range

        # If temperature is above all defined points, use the highest setting
        if calculated_speed == 0 and self.cpu_temp_to_fan_speed:
             highest_temp = max(self.cpu_temp_to_fan_speed.keys())
             if current_cpu_temp > highest_temp:
                 desired_fan_speed = self.cpu_temp_to_fan_speed[highest_temp]
                 calculated_speed = desired_fan_speed

        return desired_fan_speed, calculated_speed

    def update_fan_speed(self, current_cpu_temp: float, current_gpu_temp: Optional[float] = 0):
        self.current_cpu_temp = current_cpu_temp
        self.current_gpu_temp = current_gpu_temp or 0
        print(f"Maximum CPU Temperature Seen: {current_cpu_temp}°C.")
        print(f"Maximum GPU Temperature Seen: {self.current_gpu_temp}°C.")

        desired_fan_speed, calculated_speed = self.calculate_desired_fan_speed(current_cpu_temp)

        print(f"Current Fan Duty Cycle: {self.current_fan_duty_cycle}%")
        print(f"Desired Fan Duty Cycle: {desired_fan_speed}%")

        speed_raw = format(int(calculated_speed), 'x')
        try:
            with open('/tmp/fan_speed_telegraf', 'w') as fh:
                fh.write(f"fans,host={self.hostname} speed_percent={calculated_speed}\n")
                fh.write(f"fans,host={self.hostname} speed_raw={speed_raw}\n")
        except IOError as e:
            self.log.warning(f"Could not write to /tmp/fan_speed_telegraf: {e}")

        self.set_fan_speed(desired_fan_speed)

    def get_current_fan_duty_cycle(self) -> float:
        return self.current_fan_duty_cycle

    def get_temperature_curve(self) -> Dict[int, float]:
        return self.cpu_temp_to_fan_speed

    def detect_number_of_fans(self) -> int:
        """Detects the number of fans by querying IPMI sensors."""
        self.log.debug("Detecting number of fans...")
        fan_sensors = self.ipmi.get_sensors(sensor_type='Fan')

        self.log.debug("--- Found IPMI Fan Sensors ---")
        for sensor in fan_sensors:
            self.log.debug(f"  - Name: {sensor.name}, Value: {sensor.value}, Unit: {sensor.unit}")
        self.log.debug("------------------------------")

        return len(fan_sensors)
