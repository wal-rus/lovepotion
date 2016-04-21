#!/usr/bin/env python

import os
import time

LINES = 100

class LogWriter(object):
    """Class to write a log of all RFID swipes."""

    def __init__(self, log_file):
        self._log_file = os.path.expanduser(log_file)
        # Read last lines if file exists.
        if os.path.exists(self._log_file):
            with open(self._log_file) as fh:
                self._last_lines = fh.readlines()[-LINES:]
        else:
            self._last_lines = []

    def GetLastLines(self):
        """Returns last LINES lines as a string."""
        return ''.join(self._last_lines)

    def Log(self, **kwargs):
        """Logs kwargs to log."""
        with open(self._log_file, 'a') as fh:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            line = '[%s]' % timestamp
            for k, v in kwargs.iteritems():
                if v is not None:
                    line += ' %s:%s' % (k, v)
            line += '\n'
            self._last_lines.append(line)
            # Keep last N lines.
            self._last_lines = self._last_lines[-LINES:]
            fh.write(line)


if __name__ == '__main__':
    # Hacky little test.
    log = LogWriter('/tmp/log.txt')
    print log.GetLastLines()
    log.Log(rfid='abcd', authorized=True, name='jimmy')
    log.Log(rfid='abcd', authorized=False, name=None)
    print log.GetLastLines()
