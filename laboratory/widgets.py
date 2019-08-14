from datetime import datetime, timedelta
import sys
import time

class ProgressBar():

    def __init__(self, length, display=True, bar_length=25, pre_message=''):
        self.iteration = 1
        self.length = length
        self.temp = ''
        self.display = display
        self.bar_length = bar_length
        self.pre_message = pre_message
    
    def update(self,post_message='', pre_message='',  decimals=0):
        """Creates a terminal progress bar

        :param pre_message: message to be displayed before the progress bar
        :type pre_message: str

        :param post_message: message to be displayed after the progress bar
        :type post_message: str
        """

        if not self.display:
            return   #don't display progress bar when in debugging mode

        if not pre_message:
            pre_message = self.pre_message

        str_format = "{0:." + str(decimals) + "f}"
        percentage = str_format.format(100 * (self.iteration / float(self.length)))
        filled_length = int(round(self.bar_length * self.iteration / float(self.length)))
        bar = '#' * filled_length + '-' * (self.bar_length - filled_length)

        sys.stdout.write('\r{}|{}| {}{} - {}             '.format(pre_message,bar, percentage, '%',post_message))

        if self.iteration == self.length:
            sys.stdout.write('\r@{:0.1f}C |{}| {}{} - {}             '.format(self.temp,bar, percentage, '%','Complete!'))
            sys.stdout.write('')

        sys.stdout.flush()
        self.iteration += 1

    def reset(self):
        self.iteration = 1

class CountdownTimer():

    def __init__(self, hold=False, display=True):
        """Controls the count down until next measurement cycle

        :param hold: whether to display timer after time has elapsed [default=False (removes timer)]
        :type hold: boolean
        """
        self.hold = hold
        self.display = display

    def start(self, wait_time, start_time=None, message='Time remaining: ', stop_message=''):
        """Controls the count down until next measurement cycle

        :param wait_time: time in minutes remaining until next measurement
        :type wait_time: float/int

        :param start_time: [optional] denotes a desired start time. Default: datetime.now()
        :type start_time: datetime.datetime object

        :param message: message displayed in front of timer
        :type message: str

        :param stop_message: message displayed when time has elapsed
        :type stop_message: str
        """
        if not self.display:
            return

        if not start_time:
            start_time = datetime.now()

        end_time = start_time + timedelta(**wait_time)

        while (end_time-datetime.now()).total_seconds() > 0:
            sys.stdout.write('\r{} {}'.format(message,str(end_time-datetime.now())[:7]))
            sys.stdout.flush()

        self.stop(stop_message)

    def stop(self, stop_message):
        if not self.hold:
            sys.stdout.write('\r                                          \r'),

        if stop_message:
            sys.stdout.write(stop_message)

        sys.stdout.flush()

