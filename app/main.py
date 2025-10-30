from lib.umodbus.serial import ModbusRTU
from machine import Pin, lightsleep, Timer
import time
from modules import analog_sensor, sht30_sensor

# RTU Client/Slave setup

# --- MODIFICATION: Global variables for the counters ---
counter_1 = 0
counter_2 = 0
last_pulse_time_1 = 0
last_pulse_time_2 = 0
DEBOUNCE_MS_COUNTERS = 150 # Ignore pulses faster than 150ms for counters

print("Starting ISURNODE RTU slave...")

last_interrupt_time = 0

rtu_pins = (Pin("PA2"), Pin("PA3"))
uart_id = "LP1"
slave_addr = 6  # address on bus as client ( 6 is the first perfect number (1+2+3 = 6))

rx_led = Pin('PB15', Pin.OUT)
tx_led = Pin('PB0', Pin.OUT)
rx_led.off() # Start with LEDs off
tx_led.off() # Start with LEDs of

server = ModbusRTU(
    addr=slave_addr,  
    pins=rtu_pins,  
    baudrate=9600,  
    data_bits=8,  
    stop_bits=1, 
    parity=None,  
    ctrl_pin=Pin("PA4"),  
    uart_id=uart_id,
    rx_led_pin=rx_led, # New argument for RX LED
    tx_led_pin=tx_led  # New argument for TX LED
)

# --- Init SHT30 sensor ---
try:
    sht30 = sht30_sensor.SHT30Sensor()
except Exception as e:
    print(f"Error initializing SHT30: {e}")
    sht30 = None

analog_module = analog_sensor.AnalogInput()

re = Pin("PA5", Pin.OUT)
tps_mode = Pin("PB14", Pin.OUT)
tps_en = Pin("PB13", Pin.OUT)
tps_mode.off()
tps_en.on()

ev0_in1 = Pin("PA7", Pin.OUT)
ev0_in2 = Pin("PA6", Pin.OUT)

ev1_in1 = Pin("PA8", Pin.OUT)
ev1_in2 = Pin("PA9", Pin.OUT)

ev2_in1 = Pin("PA10", Pin.OUT)
ev2_in2 = Pin("PA11", Pin.OUT)

ev3_in1 = Pin("PA12", Pin.OUT)
ev3_in2 = Pin("PA15", Pin.OUT)


digital_in_1 = Pin('PA0', Pin.IN, Pin.PULL_DOWN)
digital_in_2 = Pin('PA1', Pin.IN, Pin.PULL_DOWN)

# Turn off all DRV8871
ev0_in1.off()
ev0_in2.off()

ev1_in1.off()
ev1_in2.off()

ev2_in1.off()
ev2_in2.off()

ev3_in1.off()
ev3_in2.off()

# --- MODBUS MAP REGISTERS ---
# 4 analog sensors
for i in range(4):
    server.add_ireg(address=i, value=i)

server.add_ireg(address=4, value=0)  # Counter 1
server.add_ireg(address=5, value=0)  # Counter 2

server.add_ist(address=6, value=False) #State 1
server.add_ist(address=7, value=False) #State 2

# SHT30
server.add_ireg(address=8, value=0)  # Temperature 
server.add_ireg(address=9, value=0) #Humidity

# Command register
server.add_hreg(address=100, value=0)  # Write '1' to trigger ADC
server.add_hreg(address=101, value=0)  # Write '1' to trigger SHT30

# Valve outputs
for i in range(200, 208):
    server.add_hreg(address=i, value=0)

print("Registers set up complete.")

def power_fail_handler(pin):
    """
    Interrupt Service Routine (ISR) for power failure.
    This function will be executed when power_good pin goes low.
    """
    global last_interrupt_time

    current_time = time.ticks_ms()
    
    if time.ticks_diff(current_time, last_interrupt_time) < 1000:
        
        return
    
    if pin.value() == 0:
    
        print("External power failed, switching to internal supercapacitor")
        server._itf._ctrlPin.off()
        re.on()
        pin.irq(trigger=Pin.IRQ_RISING, handler=power_fail_handler)
        time.sleep_ms(100)
        lightsleep()
        
    else:
        
        re.off()
        print("Woke up: External power restored.")
        
def blinky_LED(timer):
    
    num_micro_pulses = 10
    pause_pulses_ms = 15
    for _ in range(num_micro_pulses):
        blinky.on()
        time.sleep_us(1)
        blinky.off()
        time.sleep_ms(pause_pulses_ms)


# --- Interrupt handler functions for the counters ---
def pulse_counter_1_handler(pin):
    """ISR to increment counter 1 with debounce."""
    global counter_1, last_pulse_time_1
    
    current_time = time.ticks_ms()
    # If the time since the last pulse is too short, it's a bounce. Ignore it.
    if time.ticks_diff(current_time, last_pulse_time_1) < DEBOUNCE_MS_COUNTERS:
        return
        
    # If enough time has passed, it's a valid pulse.
    last_pulse_time_1 = current_time
    counter_1 += 1

def pulse_counter_2_handler(pin):
    """ISR to increment counter 2 with debounce."""
    global counter_2, last_pulse_time_2

    current_time = time.ticks_ms()
    # If the time since the last pulse is too short, it's a bounce. Ignore it.
    if time.ticks_diff(current_time, last_pulse_time_2) < DEBOUNCE_MS_COUNTERS:
        return

    # If enough time has passed, it's a valid pulse.
    last_pulse_time_2 = current_time
    counter_2 += 1
    
    
#Power good pin indicator with interrupt
power_good = Pin('PB2', Pin.IN, Pin.PULL_UP)
blinky = Pin('PB12', Pin.OUT)
#power_good.irq(trigger=Pin.IRQ_FALLING, handler=power_fail_handler)

# --- Setup pins and interrupts for the counters ---
print("Setting up pulse counters...")
# We use PULL_DOWN to ensure the state is 0 if nothing is connected.
pin_counter_1 = Pin('PB1', Pin.IN, Pin.PULL_DOWN)
pin_counter_2 = Pin('PB5', Pin.IN, Pin.PULL_DOWN)

# Every time the pin rises from 0V to 3.3V (rising edge), the handler is called.
pin_counter_1.irq(trigger=Pin.IRQ_RISING, handler=pulse_counter_1_handler)
pin_counter_2.irq(trigger=Pin.IRQ_RISING, handler=pulse_counter_2_handler)
print("Pulse counters ready.")

#Set Blinky blinking.
tim = Timer(-1)
tim.init(period=5000, mode=Timer.PERIODIC, callback=blinky_LED)

# --- Pulse generator helper ---
def pulse_ev(pin1, pin2, duration_ms=100):
    """Generates a pulse in driver."""
    print(f"Enabling pulse {pin1} y {pin2} for {duration_ms}ms...")
    pin1.on()
    pin2.off()
    time.sleep_ms(duration_ms)
    pin1.off()
    pin2.off()
    print("Pulse finished.")


# --- MAIN LOOP ---
while True:
        
    server.set_ireg(address=4, value=counter_1)
    server.set_ireg(address=5, value=counter_2)
    
    state_1 = bool(digital_in_1.value())
    server.set_ist(address=6, value=state_1)
    state_2 = bool(digital_in_2.value())
    server.set_ist(address=7, value=state_2)
            
    server.process()
    
    read_adc = server.get_hreg(100)
    read_sht = server.get_hreg(101)
    open_ev0 = server.get_hreg(200)
    close_ev0 = server.get_hreg(201)
    open_ev1 = server.get_hreg(202)
    close_ev1 = server.get_hreg(203)
    open_ev2 = server.get_hreg(204)
    close_ev2 = server.get_hreg(205)
    open_ev3 = server.get_hreg(206)
    close_ev3 = server.get_hreg(207)
    
    if open_ev0 == 1:
        print("Pulse open EV0")
        pulse_ev(ev0_in1, ev0_in2)
        server.set_hreg(address=200, value=0)
        server._itf._uart.read()  # Clears buffer

    if close_ev0 == 1:
        print("Pulse close EV0")
        pulse_ev(ev0_in2, ev0_in1)
        server.set_hreg(address=201, value=0)
        server._itf._uart.read()  # Clears buffer

    if open_ev1 == 1:
        print("Pulse open EV1")
        pulse_ev(ev1_in1, ev1_in2)
        server.set_hreg(address=202, value=0)
        server._itf._uart.read()  # Clears buffer
        
    if close_ev1 == 1:
        print("Pulse close EV1")
        pulse_ev(ev1_in2, ev1_in1)
        server.set_hreg(address=203, value=0)
        server._itf._uart.read()  # Clears buffer

    if open_ev2 == 1:
        print("Pulse open EV2")
        pulse_ev(ev2_in1, ev2_in2)
        server.set_hreg(address=204, value=0)
        server._itf._uart.read()  # Clears buffer

    if close_ev2 == 1:
        print("Pulse close EV2")
        pulse_ev(ev2_in2, ev2_in1)
        server.set_hreg(address=205, value=0)
        server._itf._uart.read()  # Clears buffer
        
    if open_ev3 == 1:
        print("Pulse open EV3")
        pulse_ev(ev3_in1, ev3_in2)
        server.set_hreg(address=206, value=0)
        server._itf._uart.read()  # Clears buffer

    if close_ev3 == 1:
        print("Pulse close EV3")
        pulse_ev(ev3_in2, ev3_in1)
        server.set_hreg(address=207, value=0)
        server._itf._uart.read()  # Clears buffer

    if read_adc == 1:

        for i in range(4):
            # Read ADC value in mV 
            adc_mV = int(analog_module.read_analog(i)*1000)

            # Update input registers
            server.set_ireg(address=i, value=adc_mV)
            print(f"  ADC[{i}] = {adc_mV}")

        server.set_hreg(address=100, value=0)
        server._itf._uart.read()

    if read_sht == 1:

        try:
            #Read SHT30 data
            sht30_data = sht30.read_data()
            temp_int = int(sht30_data['temperature'] * 100)
            hum_int = int(sht30_data['humidity'] * 100)

            # Update input registers
            server.set_ireg(address=8, value=temp_int)
            server.set_ireg(address=9, value=hum_int)
            print(f"  SHT30: Temp={sht30_data['temperature']:.2f}C , Hum={sht30_data['humidity']:.2f}% ")
            server.set_hreg(address=101, value=0)
            
        except Exception as e:
            
            print(f"Error reading SHT30 sensor: {e}")

        server._itf._uart.read()  # Clears buffer

    time.sleep_ms(100)





