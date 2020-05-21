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
        self.duration = timedelta(days=0, seconds=0, microseconds=0,
                milliseconds=0, minutes=0, hours=0, weeks=0)
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
        if self.hide:
            return

        if not start_time:
            start_time = datetime.now()

        end_time = start_time + timedelta(**self.duration)
        while (end_time-datetime.now()).total_seconds() > 0:
            sys.stdout.write('\r{} {}'.format(
                message, str(end_time-datetime.now())[:7]))
            sys.stdout.flush()

        self.stop(stop_message)

    def stop(self, stop_message):
        if not self.hold:
            sys.stdout.write('\r                                          \r'),

        if stop_message:
            sys.stdout.write(stop_message)

        sys.stdout.flush()
