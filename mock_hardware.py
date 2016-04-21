# Mock hardware implementation.

import hardware

class MockHardware(hardware.Hardware):

    def Initialize(self):
        print 'Initialize()'

    def UnlockDoor(self):
        print 'UnlockDoor()'

    def ShutDown(self):
        print 'ShutDown()'
