import struct

# custom packages
from . import const as Const

# typing not natively supported on MicroPython
from .typing import List, Optional, Union


def response(function_code: int,
             request_register_addr: int,
             request_register_qty: int,
             request_data: list,
             value_list: Optional[list] = None,
             signed: bool = True) -> bytes:

    if function_code in [Const.READ_COILS, Const.READ_DISCRETE_INPUTS]:
        sectioned_list = [value_list[i:i + 8] for i in range(0, len(value_list), 8)]    # noqa: E501

        output_value = []
        for index, byte in enumerate(sectioned_list):

            output = 0
            for bit in byte:
                output = (output << 1) | bit
            output_value.append(output)

        fmt = 'B' * len(output_value)
        return struct.pack('>BB' + fmt,
                           function_code,
                           ((len(value_list) - 1) // 8) + 1,
                           *output_value)

    elif function_code in [Const.READ_HOLDING_REGISTERS,
                           Const.READ_INPUT_REGISTER]:
        quantity = len(value_list)

        if not (0x0001 <= quantity <= 0x007D):
            raise ValueError('invalid number of registers')

        if signed is True or signed is False:
            fmt = ('h' if signed else 'H') * quantity
        else:
            fmt = ''
            for s in signed:
                fmt += 'h' if s else 'H'

        return struct.pack('>BB' + fmt,
                           function_code,
                           quantity * 2,
                           *value_list)

    elif function_code in [Const.WRITE_SINGLE_COIL,
                           Const.WRITE_SINGLE_REGISTER]:
        return struct.pack('>BHBB',
                           function_code,
                           request_register_addr,
                           *request_data)

    elif function_code in [Const.WRITE_MULTIPLE_COILS,
                           Const.WRITE_MULTIPLE_REGISTERS]:
        return struct.pack('>BHH',
                           function_code,
                           request_register_addr,
                           request_register_qty)


def exception_response(function_code: int, exception_code: int) -> bytes:

    return struct.pack('>BB', Const.ERROR_BIAS + function_code, exception_code)


def bytes_to_bool(byte_list: bytes, bit_qty: Optional[int] = 1) -> List[bool]:

    bool_list = []

    for index, byte in enumerate(byte_list):
        this_qty = bit_qty

        if this_qty >= 8:
            this_qty = 8

        # evil hack for missing keyword support in MicroPython format()
        fmt = '{:0' + str(this_qty) + 'b}'

        bool_list.extend([bool(int(x)) for x in fmt.format(byte)])

        bit_qty -= 8

    return bool_list


def to_short(byte_array: bytes, signed: bool = True) -> bytes:

    response_quantity = int(len(byte_array) / 2)
    fmt = '>' + (('h' if signed else 'H') * response_quantity)

    return struct.unpack(fmt, byte_array)


def float_to_bin(num: float) -> bin:

    return '{:0>{w}}'.format(
        bin(struct.unpack('!I', struct.pack('!f', num))[0])[2:],
        w=32)


def bin_to_float(binary: str) -> float:

    return struct.unpack('!f', struct.pack('!I', int(binary, 2)))[0]


def int_to_bin(num: int) -> str:

    return "{0:b}".format(num)
