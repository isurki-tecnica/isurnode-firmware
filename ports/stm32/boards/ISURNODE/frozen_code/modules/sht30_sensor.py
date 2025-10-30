# src/modules/sht30_sensor.py
from machine import I2C, Pin
from modules import utils
from lib.SHT30 import SHT30, SHT30Error, DEFAULT_I2C_ADDRESS
import time

class SHT30Sensor:
    def __init__(self, i2c_bus=None, address=DEFAULT_I2C_ADDRESS):
        """
        Initializes the SHT30 sensor wrapper.

        Args:
            i2c_bus: An already initialized I2C bus object. If None, it will be created.
            address: The I2C address of the sensor (default: 0x44).
        """
        self.i2c_bus = i2c_bus
        self.address = address
        self.sensor = None

        try:
            # If no I2C bus is provided, create one using config or defaults
            if self.i2c_bus is None:
                # I2C configuration from config.json, or use defaults
                # Assuming your new board uses hardware I2C(1)
                self.i2c_bus = I2C(1)
            
            # Initialize the low-level SHT30 driver
            self.sensor = SHT30(i2c_addr=self.address, i2c_device=self.i2c_bus)

            # Check if the sensor is present on the bus
            if self.sensor.is_present():
                utils.log_info("SHT30 sensor initialized successfully.")
            else:
                utils.log_error("SHT30 sensor not found on the I2C bus.")
                self.sensor = None

        except Exception as e:
            utils.log_error(f"Failed to initialize SHT30 sensor: {e}")
            self.sensor = None
    
    def read_data(self):
        """
        Reads the sensor data (temperature and humidity).

        Returns:
            A dictionary containing the sensor data, or None if an error occurred.
        
        Example Usage:
        
        sht_sensor = SHT30Sensor() # Assumes I2C bus is configured in config.json
        for _ in range(10):
            sht_data = sht_sensor.read_data()
            if sht_data:
                utils.log_info(f"Temperature: {sht_data['temperature']:.2f} C")
                utils.log_info(f"Humidity: {sht_data['humidity']:.2f} %RH")
            else:
                utils.log_error("Failed to read SHT30 sensor data.")
            time.sleep(2)
        """
        if self.sensor:
            try:
                # The measure() method from the low-level library returns a tuple
                temperature, humidity = self.sensor.measure()
                
                data = {
                    "temperature": temperature,
                    "humidity": humidity,
                }
                return data
            
            except SHT30Error as e:
                # Handle specific errors from the low-level library
                utils.log_error(f"SHT30 sensor error: {e}")
                return None
            except Exception as e:
                # Handle other potential errors (e.g., general OSError)
                utils.log_error(f"Error reading SHT30 sensor data: {e}")
                return None
        else:
            utils.log_error("SHT30 sensor not initialized.")
            return None
