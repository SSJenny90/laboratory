import config
import time
import logging
import sys
import os
import serial
import glob
import pickle
import random
import matplotlib.pyplot as plt
from pandas.api.types import is_string_dtype, is_numeric_dtype
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import smtplib
from datetime import datetime, timedelta

def lab_logger(name):
    """Sets up logging messages for the laboratory. Sends to both a file and the console by default. Levels for both the file and console can be set to anything defined by the
    python logging package (DEBUG,INFO,WARNING,ERROR,CRITICAL). Specified log level AND GREATER will be included. Logfiles can be found in /logfiles/ """

    logger = logging.getLogger(name)    #define the logger
    logger.setLevel('DEBUG') #define root loger level

    #clear any handlers already present. Prevents duplicate messages
    if logger.hasHandlers(): logger.handlers.clear()

    #create a folder for the log files if none exists
    folder = 'logfiles'
    if not os.path.exists(folder): os.mkdir(folder)
    filepath = os.path.join(folder, '{}_{}.log'.format(config.name,time.strftime('%d-%m-%Y_%H%M')))

    def sorted_ls(path):
        """Removes all but the 10 most recent logfiles -- prevent clutter during testing"""
        mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
        files = list(sorted(os.listdir(path), key=mtime))
        for f in files[1:-10]: os.remove(os.path.join(folder,f))
    sorted_ls(folder)

    #setup file handler
    fh = logging.FileHandler(filepath)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s - %(name)s (line %(lineno)s)','%d-%m-%y %H:%M.%S')
    fh.setFormatter(formatter)
    fh.setLevel('DEBUG')
    logger.addHandler(fh)

    #set up console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(message)s'))
    ch.setLevel('INFO')
    logger.addHandler(ch)
    return logger

def data_logger():
    """Sets up the data file in much the same way as the log file.
    Data cannot be output to the console. Data file can be found in
    /datafiles/"""

    dlogger = logging.getLogger("data_logger")
    dlogger.setLevel('DEBUG')
    if dlogger.hasHandlers(): dlogger.handlers.clear()

    folder = 'datafiles'
    if not os.path.exists(folder): os.mkdir(folder)
    filename = os.path.join(folder,'{}_{}.txt'.format(config.name,time.strftime('%d-%B-%y-%H%M')))

    #set up file handler
    fh = logging.FileHandler(filename)
    fh.setFormatter(logging.Formatter('%(message)s'))
    fh.setLevel('DEBUG')
    dlogger.addHandler(fh)

    #add header lines to data file
    dlogger.critical('start_date: {}'.format(time.strftime('%A %d-%B %Y')))
    dlogger.critical('start_time: {}'.format(time.strftime('%H:%M:%S')))
    return dlogger

def save_obj(obj, filename):
    """Saves an object instance as a .pkl file for later retrieval. Can be loaded again using :meth:'Utils.load_obj'

    :param obj: the object instance to be saved
    :type obj: class

    :param filename: name of file
    :type filename: str
    """
    filename = filename.split('.')[0]
    with open(filename + '.pkl', 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_obj(filename):
    """Loads a .pkl file

    :param filename: full path to file. must be a .pkl
    :type filename: str
    """
    if not filename.endswith('.pkl'):
        filename = filename + '.pkl'

    # for f in filenames:
    with open(filename, 'rb') as input:  # Overwrites any existing file.
        return pickle.load(input)

def send_email(toaddr,message,cc=False,logfile=False,datafile=False):
    """Sends an email to the specified email address. logfile or datafile can
    be attached if desired. used mainly for email updates on progress during
    long measurement cycles. mailer is geophysicslabnotifications@gmail.com.

    :param toaddr: full email address of intended recipient
    :type toaddr: str

    :param message: message to include in email
    :type message: str

    :param cc: email can be carbon copied to additional adresses in cc
    :type cc: str,list

    :param logfile: whether to attach the current logfile
    :type logfile: boolean

    :param datafile: whether to attach the current datafile
    :type datafile: boolean
    """
    fromaddr = "geophysicslabnotifications@gmail.com"
    pw = 'Laboratory123!'

    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    if cc:
        msg['Cc'] = cc
    msg['Subject'] = "Lab Notification"
    body = 'Hi,\n\n{}\n\nCheers,\nYour Friendly Lab Assistant'.format(message)
    msg.attach(MIMEText(body, 'plain'))

    if logfile:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(logfile, "rb").read())
        part.add_header('Content-Disposition', 'attachment', filename='controlLog.txt')
        msg.attach(part)

    if datafile:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(datafile, "rb").read())
        part.add_header('Content-Disposition', 'attachment', filename='labData.txt')
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.connect("smtp.gmail.com",587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(fromaddr, pw)
    text = msg.as_string()
    if cc:
        server.sendmail(fromaddr, [toaddr,cc], text)
    else:
        server.sendmail(fromaddr, toaddr, text)
    server.quit

def furnace_profile(self):
    """Records the temperature of both electrodes (te1 and te2) as the sample is moved
    from one end of the stage to the other. Used to find the center of the stage or the xpos of a desired temperature gradient when taking thermopower measurements.
    """
    self.daq.configure()
    # self.furnace.set_temp(300)   #this is best done at a reasonably high temperature
    # self.motor.reset()
    self.motor.set_xpos(4000)
    Utils.save_obj(self.data,'furnace_profile')
    xpos = 4000
    while xpos < 6000:
        xpos = self.motor.get_pos()
        self.data.xpos.append(xpos)
        vals = self.daq.get_temp()
        self.data.thermo.tref.append(vals[0])
        self.data.thermo.te1.append(vals[1])
        self.data.thermo.te2.append(vals[2])

        self.motor.move_mm(.1)

        Utils.save_obj(self.data,'furnace_profile')
        time.sleep(600)

def find_center(self):
    """TODO - Attempts to place the sample at the center of the heat source such that
    te1 = te2. untested.
    """
    self.daq.reset()
    self.daq.toggle_switch('thermo')
    self.daq._config_temp()

    while True:
        temp = self.daq.get_temp()

        if temp is None:
            self.logger.error('No temperature data collected')
        te1 = temp[1]
        te2 = temp[2]

        print(te1,te2)

        delta = abs(te1-te2)

        if delta < 0.1:
            print('Found center at' + self.motor.get_pos())
            break

        if te1 < te2:
            self.motor.move_mm(-0.05)
        elif te2 < te1:
            self.motor.move_mm(0.05)
        print(self.motor.get_pos())

        time.sleep(600)

def check_controlfile(controlfile):
    """Checks to make sure the specified controlfile is a valid file that can be used by this program

    :param controlfile: a loaded control file
    :type controlfile: pd.DataFrame
    """
    logger = logging.getLogger(__name__)
    columns = set(list(controlfile.columns.values))
    exp_numeric = ['target_temp','hold_length','heat_rate','interval','offset']
    exp_str = ['buffer','fo2_gas']
    expected = set().union(exp_numeric, exp_str)

    #check if the headers in controlfile are what is expected
    if not columns == expected:
        if len(columns) > len(expected):   #if controlfile has an additional column
            dif = columns.difference(expected)
            logger.debug('Found an unexpected additional column/s {} in the control file'.format(dif))
        else:       #if controlfile is missing an expected column
            dif = expected.difference(columns)
            logger.debug('Could not find {} in the control file'.format(dif))
        logger.debug('    Expected to find {}'.format(expected))
        return False

    #if controlfile starts at the temperature of the furnace but was not intended to hold, it can get stuck in a loop. therefore the first value must be a 0. Only matters if no hold_length value was input into the first step
    if np.isnan(controlfile.hold_length[0]):
        controlfile.loc[0,'hold_length'] = 0

    #check that data types in numeric variables are correct
    for header in exp_numeric:
        if not is_numeric_dtype(controlfile[header]):
            logger.debug('Encountered an unexpected data type in {} - must be numeric'.format(header))
            return False

    #check that buffer inputs are valid values
    buffer_types = ['qfm','fmq','fqm','iw','wm','mh','qif','nno','mmo','cco']
    for val in controlfile.buffer:
        if val not in buffer_types:
            logger.debug("Found an unexpected buffer type:  '{}'".format(val))
            logger.debug('    Must be one of {}'.format(buffer_types))
            return False

    #check that fo2_gas inputs are valid values
    gas_types = ['h2','co']
    for val in controlfile.fo2_gas:
        if val not in gas_types:
            logger.debug("Found an unexpected gas type:  '{}'".format(val))
            logger.debug('    Must be one of {}'.format(gas_types))
            return False

    return True

def load_frequencies(min,max,n,log,filename):
    """Creates an np.array of frequency values specified by either min, max and n or a file containing a list of frequencies specified by filename"""
    if filename is not None:
        with open(filename) as file:
            freq = [line.rstrip() for line in file]
        return np.around(np.array([float(f) for f in freq]))
    elif log is True: return np.around(np.geomspace(min,max,n))
    elif log is False: return np.around(np.linspace(min,max,n))
    else:
        return False

def find_indicated(temperature,normal=True):
    #from calibration experiment
    furnace = np.array([400,500,600,700,800,900,1000])
    daq = np.array([253.46,335.82,422.67,512,604.5,698.7,795.3])
    A = np.vstack([daq,np.ones(len(daq))]).T
    m,c = np.linalg.lstsq(A,furnace,rcond=None)[0]

    if normal: return np.around(np.multiply(m,temperature)+c,2) #return a furnace value for given temperature
    else: return np.around(np.divide(temperature-c,m),2)    #return a daq value for given temperature

class Messages():
    device_error = 'I\'ve got some bad news! The {} is no longer sending or receiving messages so I\'m going to shut down the lab until you can come take a look.'
    delayed_start = 'It just ticked over to {} so I\'m going to set up the instruments and get things underway.'
    step_complete = "Just letting you know that step {} is now complete! I\'m going to set the temperature to {}C and get started on step {}.\n\nEstimated completion time for step {} is: {}."

if __name__ == '__main__':
    m = Messages()
    print(m.delayed_start.format('0900'))
