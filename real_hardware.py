# Real hardware implementation for talking to GPIO and Phidgets libraries.

from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Events.Events import AttachEventArgs, DetachEventArgs, ErrorEventArgs, OutputChangeEventArgs, TagEventArgs
from Phidgets.Devices.RFID import RFID, RFIDTagProtocol
import RPi.GPIO as GPIO

import hardware
import time

# GPIO4 is NOT 4...
# To know what number to use here see:
# http://openmicros.org/index.php/articles/94-ciseco-product-documentation/raspberry-pi/217-getting-started-with-raspberry-pi-gpio-and-python
OPEN_PORT = 7   # 7 => GPIO4


class RealHardware(hardware.Hardware):

    def __init__(self, *args, **kwargs):
        super(RealHardware, self).__init__(*args, **kwargs)
        self.rfid = None

    # Event Handler Callback Functions.
    def _RfidAttached(self, e):
        attached = e.device
        print("RFID %i Attached!" % (attached.getSerialNum()))

    def _RfidDetached(self, e):
        detached = e.device
        print("RFID %i Detached!" % (detached.getSerialNum()))

    def _RfidError(self, e):
        try:
            source = e.device
            print("RFID %i: Phidget Error %i: %s" % (source.getSerialNum(), e.eCode, e.description))
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))

    def _RfidOutputChanged(self, e):
        source = e.device
        print("RFID %i: Output %i State: %s" % (source.getSerialNum(), e.index, e.state))

    def _RfidTagGained(self, e):
        self.rfid.setLEDOn(1)
        self.tag_seen_handler(e.tag)

    def _RfidTagLost(self, e):
        source = e.device
        self.rfid.setLEDOn(0)
        print("RFID %i: Tag Lost: %s" % (source.getSerialNum(), e.tag))

    def Initialize(self):
        # Set up GPIO pins.
        # Refer to pin using Broadcom SOC numbering.
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(OPEN_PORT, GPIO.OUT)

        # Create an RFID object.
        self.rfid = RFID()

        # Set up the event handlers.
        try:
            self.rfid.setOnAttachHandler(self._RfidAttached)
            self.rfid.setOnDetachHandler(self._RfidDetached)
            self.rfid.setOnErrorhandler(self._RfidError)
            self.rfid.setOnOutputChangeHandler(self._RfidOutputChanged)
            self.rfid.setOnTagHandler(self._RfidTagGained)
            self.rfid.setOnTagLostHandler(self._RfidTagLost)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            print("Exiting....")
            exit(1)

        print("Opening phidget object....")

        try:
            self.rfid.openPhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            print("Exiting....")
            exit(1)

        print("Waiting for attach....")

        try:
            self.rfid.waitForAttach(10000)
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            try:
                self.rfid.closePhidget()
            except PhidgetException as e:
                print("Phidget Exception %i: %s" % (e.code, e.details))
                print("Exiting....")
                exit(1)
            print("Exiting....")
            exit(1)

        print("Turning on the RFID antenna....")
        self.rfid.setAntennaOn(True)


    def UnlockDoor(self):
        GPIO.output(OPEN_PORT, True)
        self.rfid.setOutputState(0, True)
        time.sleep(self.open_time)
        GPIO.output(OPEN_PORT, False)
        self.rfid.setOutputState(0, False)

    def ShutDown(self):
        try:
            lastTag = self.rfid.getLastTag()
            print("Last Tag: %s" % (lastTag))
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))

        print("Closing...")

        try:
            self.rfid.closePhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))
            print("Exiting....")
            exit(1)
