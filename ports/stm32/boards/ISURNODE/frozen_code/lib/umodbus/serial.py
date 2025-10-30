from machine import UART
from machine import Pin
import struct
import time

# custom packages
from . import const as Const
from . import functions
from .common import Request
from .common import ModbusException
from .modbus import Modbus

# typing not natively supported on MicroPython
from .typing import List, Optional, Union


class ModbusRTU(Modbus):

    def __init__(self,
                 addr: int,
                 baudrate: int = 9600,
                 data_bits: int = 8,
                 stop_bits: int = 1,
                 parity: Optional[int] = None,
                 pins: List[Union[int, Pin], Union[int, Pin]] = None,
                 ctrl_pin: int = None,
                 uart_id = 1,
                 rx_led_pin = None, # MODIFICATION: Add rx_led_pin parameter
                 tx_led_pin = None): # MODIFICATION: Add tx_led_pin parameter
        super().__init__(
            # set itf to Serial object, addr_list to [addr]
            Serial(uart_id=uart_id,
                   baudrate=baudrate,
                   data_bits=data_bits,
                   stop_bits=stop_bits,
                   parity=parity,
                   pins=pins,
                   ctrl_pin=ctrl_pin,
                   rx_led_pin=rx_led_pin, # MODIFICATION: Pass rx_led_pin to Serial
                   tx_led_pin=tx_led_pin), # MODIFICATION: Pass tx_led_pin to Serial
            [addr]
        )


class Serial():
    def __init__(self,
                 uart_id = 1,
                 baudrate: int = 9600,
                 data_bits: int = 8,
                 stop_bits: int = 1,
                 parity=None,
                 pins: List[Union[int, Pin], Union[int, Pin]] = None,
                 ctrl_pin: int = None,
                 rx_led_pin = None, # MODIFICATION: Add rx_led_pin parameter
                 tx_led_pin = None): # MODIFICATION: Add tx_led_pin parameter

        # UART flush function is introduced in Micropython v1.20.0
        self._has_uart_flush = callable(getattr(UART, "flush", None))
        self._uart = UART(uart_id,
                          baudrate=baudrate,
                          bits=data_bits,
                          parity=parity,
                          stop=stop_bits
                          )

        if ctrl_pin is not None:
            self._ctrlPin = Pin(ctrl_pin, mode=Pin.OUT)
        else:
            self._ctrlPin = None

        # MODIFICATION: Store LED pin objects
        self._rx_led = rx_led_pin
        self._tx_led = tx_led_pin

        # timing of 1 character in microseconds (us)
        self._t1char = (1000000 * (data_bits + stop_bits + 2)) // baudrate

        if baudrate <= 19200:
            self._inter_frame_delay = (self._t1char * 3500) // 1000
        else:
            self._inter_frame_delay = 1750

    def _calculate_crc16(self, data: bytearray) -> bytes:
        crc = 0xFFFF
        for char in data:
            crc = (crc >> 8) ^ Const.CRC16_TABLE[((crc) ^ char) & 0xFF]
        return struct.pack('<H', crc)

    def _exit_read(self, response: bytearray) -> bool:

        response_len = len(response)
        if response_len >= 2 and response[1] >= Const.ERROR_BIAS:
            if response_len < Const.ERROR_RESP_LEN:
                return False
        elif response_len >= 3 and (Const.READ_COILS <= response[1] <= Const.READ_INPUT_REGISTER):
            expected_len = Const.RESPONSE_HDR_LENGTH + 1 + response[2] + Const.CRC_LENGTH
            if response_len < expected_len:
                return False
        elif response_len < Const.FIXED_RESP_LEN:
            return False

        return True

    def _uart_read(self) -> bytearray:

        response = bytearray()

        for x in range(1, 120):
            if self._uart.any():
                response.extend(self._uart.read())

                # variable length function codes may require multiple reads
                if self._exit_read(response):
                    break

            # wait for the maximum time between two frames
            time.sleep_us(self._inter_frame_delay)

        return response

    def _uart_read_frame(self, timeout: Optional[int] = None) -> bytearray:
        
        received_bytes = bytearray()

        # set default timeout to at twice the inter-frame delay
        if timeout == 0 or timeout is None:
            timeout = 2 * self._inter_frame_delay  # in microseconds

        start_us = time.ticks_us()

        # stay inside this while loop at least for the timeout time
        while (time.ticks_diff(time.ticks_us(), start_us) <= timeout):
            # check amount of available characters
            if self._uart.any():
                # MODIFICATION: Turn RX LED on when data is detected
                if self._rx_led:
                    self._rx_led.on()
                # remember this time in microseconds
                last_byte_ts = time.ticks_us()

                while time.ticks_diff(time.ticks_us(), last_byte_ts) <= self._inter_frame_delay:

                    r = self._uart.read()

                    if r is not None:
                        received_bytes.extend(r)
                        last_byte_ts = time.ticks_us()

            if len(received_bytes) > 0:
                # MODIFICATION: Turn RX LED off after frame is received
                if self._rx_led:
                    self._rx_led.off()
                return received_bytes

        # MODIFICATION: Also turn RX LED off on timeout
        if self._rx_led:
            self._rx_led.off()

        return received_bytes

    def _send(self, modbus_pdu: bytes, slave_addr: int) -> None:

        modbus_adu = bytearray()
        modbus_adu.append(slave_addr)
        modbus_adu.extend(modbus_pdu)
        modbus_adu.extend(self._calculate_crc16(modbus_adu))
        
        #print(f"DEBUG: _send() - Final frame to transmit: {modbus_adu}")
        #print("DEBUG: _send() - About to call self._uart.write()")
        
        # MODIFICATION: Turn TX LED on right before sending
        if self._tx_led:
            self._tx_led.on()

        if self._ctrlPin:
            self._ctrlPin.on()
            time.sleep_us(200)

        send_start_time = time.ticks_us()
        self._uart.write(modbus_adu)
        send_finish_time = time.ticks_us()
        
        #print("DEBUG: _send() - self._uart.write() finished")

        if self._has_uart_flush:
            self._uart.flush()
            time.sleep_us(self._t1char)
        else:
            sleep_time_us = (
                self._t1char * len(modbus_adu) -    # total frame time in us
                time.ticks_diff(send_finish_time, send_start_time) +
                100     # only required at baudrates above 57600, but hey 100us
            )
            time.sleep_us(sleep_time_us)

        if self._ctrlPin:
            self._ctrlPin.off()
            
        # MODIFICATION: Turn TX LED off right after sending
        if self._tx_led:
            self._tx_led.off()

    def send_response(self,
                      slave_addr: int,
                      function_code: int,
                      request_register_addr: int,
                      request_register_qty: int,
                      request_data: list,
                      values: Optional[list] = None,
                      signed: bool = True) -> None:

        #print(f"DEBUG: Processing in serial.py - Modbus response: {values}")
        modbus_pdu = functions.response(
            function_code=function_code,
            request_register_addr=request_register_addr,
            request_register_qty=request_register_qty,
            request_data=request_data,
            value_list=values,
            signed=signed
        )
        #print(f"DEBUG: Processing in serial.py - Modbus pdu: {modbus_pdu}")
        self._send(modbus_pdu=modbus_pdu, slave_addr=slave_addr)

    def send_exception_response(self,
                                slave_addr: int,
                                function_code: int,
                                exception_code: int) -> None:

        modbus_pdu = functions.exception_response(
            function_code=function_code,
            exception_code=exception_code)
        self._send(modbus_pdu=modbus_pdu, slave_addr=slave_addr)

    def get_request(self,
                    unit_addr_list: List[int],
                    timeout: Optional[int] = None) -> Union[Request, None]:

        req = self._uart_read_frame(timeout=timeout)
        
        #print(f"DEBUG: Frame received: {req}")

        if len(req) < 8:
            return None

        if req[0] not in unit_addr_list:
            #print(f"DEBUG: Wrong Slave ID. Got {req[0]}, expected one of {unit_addr_list}")
            return None

        req_crc = req[-Const.CRC_LENGTH:]
        req_no_crc = req[:-Const.CRC_LENGTH]
        expected_crc = self._calculate_crc16(req_no_crc)

        if (req_crc[0] != expected_crc[0]) or (req_crc[1] != expected_crc[1]):
            #print(f"DEBUG: CRC Mismatch. Got {req_crc}, expected {expected_crc}")
            return None
        
        #print("DEBUG: Slave ID and CRC OK!")

        try:
            request = Request(interface=self, data=req_no_crc)
        except ModbusException as e:
            self.send_exception_response(
                slave_addr=req[0],
                function_code=e.function_code,
                exception_code=e.exception_code)
            return None

        return request
