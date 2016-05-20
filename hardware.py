# Abstraction layer for interacting with hardware.

class Hardware(object):
    """Interface for the hardware abstraction.

    Extend and implement the methods.
    """

    def __init__(self, open_time, pin_config):
        # Handler to call when a tag is seen.
        self.tag_seen_handler = None
        self.open_time = open_time
        self.pin_config = pin_config

    def Initialize(self):
        """Initializes the hardware."""
        raise NotImplementedError('subclass and implement me!')

    def SetTagSeenHandler(self, handler):
        """Sets up handler for when RFID event is seen.

        Args:
          handler: function, called with one string argument - RFID tag serial number.
        """
        self.tag_seen_handler = handler

    def ShutDown(self):
        """Cleans up, closes open devices."""
        raise NotImplementedError('subclass and implement me!')

    def UnlockDoor(self):
        """Unlocks the door."""
        raise NotImplementedError('subclass and implement me!')


def Instantiate(use_mock, open_time, pin_config):
    if use_mock:
        import mock_hardware
        return mock_hardware.MockHardware(open_time, pin_config)
    else:
        import real_hardware
        return real_hardware.RealHardware(open_time, pin_config)
