import transmission
from jerial import JSONSerialReader
import time

'''
TODO: Check to see if the usb ports on the Raspberry Pi are still not working with tty.
'''

pico = JSONSerialReader("/dev/pico")
arduino = JSONSerialReader("/dev/arduino")


if __name__ == "__main__":
    print("Booting up system.")