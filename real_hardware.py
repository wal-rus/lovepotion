# Real hardware implementation for talking to GPIO and Pigpio libraries.

import RPi.GPIO as GPIO
import pigpio

import hardware
import time

# Sample wiegand decoder from the pigpio sample library
# Eventually replace this with a custom extension so we don't
# need pigpio
class decoder:
   def __init__(self, pi, gpio_0, gpio_1, callback, bit_timeout=5):

      """
      Instantiate with the pi, gpio for 0 (green wire), the gpio for 1
      (white wire), the callback function, and the bit timeout in
      milliseconds which indicates the end of a code.

      The callback is passed the code length in bits and the value.
      """

      self.pi = pi
      self.gpio_0 = gpio_0
      self.gpio_1 = gpio_1

      self.callback = callback

      self.bit_timeout = bit_timeout

      self.in_code = False

      self.pi.set_mode(gpio_0, pigpio.INPUT)
      self.pi.set_mode(gpio_1, pigpio.INPUT)

      self.pi.set_pull_up_down(gpio_0, pigpio.PUD_UP)
      self.pi.set_pull_up_down(gpio_1, pigpio.PUD_UP)

      self.cb_0 = self.pi.callback(gpio_0, pigpio.FALLING_EDGE, self._cb)
      self.cb_1 = self.pi.callback(gpio_1, pigpio.FALLING_EDGE, self._cb)

   def _cb(self, gpio, level, tick):

      """
      Accumulate bits until both gpios 0 and 1 timeout.
      """

      if level < pigpio.TIMEOUT:

         if self.in_code == False:
            self.bits = 1
            self.num = 0

            self.in_code = True
            self.code_timeout = 0
            self.pi.set_watchdog(self.gpio_0, self.bit_timeout)
            self.pi.set_watchdog(self.gpio_1, self.bit_timeout)
         else:
            self.bits += 1
            self.num = self.num << 1

         if gpio == self.gpio_0:
            self.code_timeout = self.code_timeout & 2 # clear gpio 0 timeout
         else:
            self.code_timeout = self.code_timeout & 1 # clear gpio 1 timeout
            self.num = self.num | 1

      else:

         if self.in_code:

            if gpio == self.gpio_0:
               self.code_timeout = self.code_timeout | 1 # timeout gpio 0
            else:
               self.code_timeout = self.code_timeout | 2 # timeout gpio 1

            if self.code_timeout == 3: # both gpios timed out
               self.pi.set_watchdog(self.gpio_0, 0)
               self.pi.set_watchdog(self.gpio_1, 0)
               self.in_code = False
               self.callback(self.bits, self.num)

   def cancel(self):

      """
      Cancel the Wiegand decoder.
      """

      self.cb_0.cancel()
      self.cb_1.cancel()
      

# GPIO4 is NOT 4...
# To know what number to use here see:
# http://openmicros.org/index.php/articles/94-ciseco-product-documentation/raspberry-pi/217-getting-started-with-raspberry-pi-gpio-and-python
OPEN_PORT = 4
DL_PORT = 17
DH_PORT = 18

class RealHardware(hardware.Hardware):

    def __init__(self, *args, **kwargs):
        super(RealHardware, self).__init__(*args, **kwargs)
        self.rfid = None

    def _RfidTagScanned(self, bits, value):
        self.tag_seen_handler("%s" % value)

    def Initialize(self):
        # Set up GPIO pins.
        # Refer to pin using Broadcom SOC numbering.
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(OPEN_PORT, GPIO.OUT)

        # Create an RFID object.
        self.pi = pigpio.pi()
        self.rfid = decoder(self.pi, DL_PORT, DH_PORT, self._RfidTagScanned)

    def UnlockDoor(self):
        GPIO.output(OPEN_PORT, True)
        time.sleep(self.open_time)
        GPIO.output(OPEN_PORT, False)

    def ShutDown(self):    
        print("Closing...")
        self.rfid.cancel()
        self.pi.stop()
    
