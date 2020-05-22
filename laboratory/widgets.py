import sys
import time
from datetime import datetime, timedelta


class CountdownTimer():

    def __init__(self, days=0, seconds=0, microseconds=0,
                milliseconds=0, minutes=0, hours=0, weeks=0, hold=False, hide=True):
        """Controls the count down until next measurement cycle

        :param hold: whether to display timer after time has elapsed [default=False (removes timer)]
        :type hold: boolean
        """
        self.duration = timedelta(days=days, seconds=seconds, microseconds=microseconds,
                milliseconds=milliseconds, minutes=minutes, hours=hours, weeks=weeks)
        self.hold = hold
        self.hide = hide

    def start(self, start_time=None, message='Time remaining: ', stop_message=''):
        """Controls the count down until next measurement cycle

        :param start_time: [optional] denotes a desired start time. Default: datetime.now()
        :type start_time: datetime.datetime object

        :param message: message displayed in front of timer
        :type message: str

        :param stop_message: message displayed when time has elapsed
        :type stop_message: str
        """
        if not start_time:
            start_time = datetime.now()

        finish = start_time + self.duration
        # while (finish-datetime.now()).total_seconds() > 0:
        while finish > datetime.now():
            if not self.hide:
                sys.stdout.write('\r{} {}'.format(
                    message, str(finish-datetime.now()).split('.')[0]))
                sys.stdout.flush()

        self.stop(stop_message)

    def stop(self, stop_message):
        if not self.hold:
            sys.stdout.write('\r                                          \r'),

        if stop_message:
            sys.stdout.write(stop_message)

        sys.stdout.flush()
