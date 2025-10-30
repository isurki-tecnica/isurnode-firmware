# src/modules/analog.py
from machine import I2C, Pin
from lib.ADS1115 import *
from modules import utils
import json
#from modules.config_manager import config_manager

class AnalogInput:
    def __init__(self, sda_pin=None, scl_pin=None, i2c_freq=None, ads1115_addr=None):
        """
        Initializes the AnalogInput module.

        Args:
            sda_pin: The I2C SDA pin.
            scl_pin: The I2C SCL pin.
            i2c_freq: The I2C frequency.
            ads1115_addr: The I2C address of the ADS1115.
        """
        
        self.ads1115_addr = ads1115_addr if ads1115_addr is not None else 0x48

        # Initialize I2C bus.
        self.i2c = I2C(1)

        # Initialize ADS1115.
        try:
            self.ads = ADS1115(address=self.ads1115_addr, i2c=self.i2c)
            # Set gain, depending on the voltage to be read.
            self.ads.setVoltageRange_mV(ADS1115_RANGE_4096)
            # Set resolution to 16-SPS (ADS1115).
            self.ads.setConvRate(ADS1115_16_SPS)
            utils.log_info("ADS1115 initialized successfully.")
        except Exception as e:
            utils.log_error(f"Error initializing ADS1115: {e}")
            self.ads = None

    def read_analog(self, channel_nums):
        """
        Reads the analog value of the specified channel or channels.

        Args:
            channel_nums: A list of channel numbers (0-3) to read, or a single integer for one channel.

        Returns:
            A list with the analog readings in volts for the specified channels,
            or a single value if only one channel was requested.
            Returns None if there is an error.
        """
        if self.ads:
            values = []
            if isinstance(channel_nums, int):
                channel_nums = [channel_nums]  # Convert to list if a single integer is provided

            for channel_num in channel_nums:
                if 0 <= channel_num <= 3:
                    try:
                        # Select the channel using MUX bits.
                        if channel_num == 0:
                            self.ads.setCompareChannels(ADS1115_COMP_0_GND)
                        elif channel_num == 1:
                            self.ads.setCompareChannels(ADS1115_COMP_1_GND)
                        elif channel_num == 2:
                            self.ads.setCompareChannels(ADS1115_COMP_2_GND)
                        elif channel_num == 3:
                            self.ads.setCompareChannels(ADS1115_COMP_3_GND)

                        # Set to single shot mode.
                        self.ads.setMeasureMode(ADS1115_SINGLE)
                        # Start measurement.
                        self.ads.startSingleMeasurement()
                        # Wait for the conversion to finish.
                        while self.ads.isBusy():
                            pass
                        # Read the value.
                        value_mV = self.ads.getResult_mV()  # Read in millivolts.
                        value = value_mV / 1000.0  # Convert to volts.
                        #print(f"Channel {channel_num}: Voltage = {value} V, raw value = {self.ads.getRawResult()}")
                        values.append(value)

                    except Exception as e:
                        utils.log_error(f"Error reading analog channel {channel_num}: {e}")
                        values.append(None)  # Append None for error channels.
                else:
                    utils.log_error(f"Invalid channel number: {channel_num}. Must be between 0 and 3.")
                    values.append(None)  # Append None for invalid channels.

            return values if len(values) > 1 else values[0]  # Return single value if only one channel was requested.
        else:
            utils.log_error("Error: ADS1115 not initialized.")
            return None
        
    def convert_value(self, value, zero, full_scale):
        """
        Converts the analog value to engineering units

        Args:
            value: Analog value in volts
            zero: zero of engineering units
            full_scale: full_scale of engineering units

        Returns:
            Value in engineering units of the passed value in volts.
        """
        
        slope = (full_scale - zero)/(1.611 - 0.322)
        return slope*(value - 0.322) + zero
