from machine import Pin, Timer, disable_irq, enable_irq
import time

# Initialize global variables
blink_timer = None  # Use a timer for blinking
blink_dict = {'L':'', 'R':''}  # Use a dictionary for blinking

pins_dict = {
    'L': {'R': Pin(16, Pin.OUT), 'Y': Pin(17, Pin.OUT), 'B': Pin(18, Pin.OUT), 'G': Pin(19, Pin.OUT)}, 
    'R': {'R': Pin(33, Pin.OUT), 'Y': Pin(25, Pin.OUT), 'B': Pin(26, Pin.OUT), 'G': Pin(27, Pin.OUT)}
}

# Synchronyze blinking
blink_pin_value = 0

# Initialize all light to off at startup
for side in pins_dict.keys():
    for pin in pins_dict[side].values():
        pin.value(1)

blinking_chars = ['r', 'b', 'y', 'g']

def blink(timer):
    global blink_dict, blink_pin_value
    blink_pin_value = not blink_pin_value
    for side, color_string in blink_dict.items():
        for color in color_string:
            pin = pins_dict[side][color]
            pin.value(blink_pin_value)  # Toggle the pin value

# Start the blink timer
blink_timer = Timer(-1)
blink_timer.init(period=500, mode=Timer.PERIODIC, callback=blink)

def light_control(side, color_string):
    global blink_dict  

    
    for blinking_char in blinking_chars:
        if blinking_char in color_string and blinking_char.upper() not in blink_dict[side]:
            blink_dict[side] += blinking_char.upper()
        elif blinking_char not in color_string:
            blink_dict[side] = blink_dict[side].replace(blinking_char.upper(), '')
    
    # Iterate and update LED states
    for color, pin in pins_dict[side].items():
        if color in color_string:
            print(f'{side}-{color} on')
            pin.value(0)
        else:
            print(f'{side}-{color} off')
            pin.value(1)


