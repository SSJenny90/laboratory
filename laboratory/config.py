import os
from .setup import *

#-------------------Experiment settings-------------------
PROJECT_NAME = 'Test B'
SAMPLE_THICKNESS = 2.6 #in mm
SAMPLE_DIAMETER = 12.7 #in mm
SAMPLE_AREA = 97.686 #in mm^2 - ONLY SET IF SAMPLE IS NOT A COMPLETE DISK AND AREA MUST BE CALCULATED MANUALLY
"""Area of the sample in :math:`mm^{2}`. Useful if the sample is not a perfect disc."""

MINIMUM_FREQ = 20       #in Hz
MAXIMUM_FREQ = 2000000  #in Hz (2MHz)
FREQ_LOG_SCALE = True
# FREQUENCY_LIST = []

# uncomment if you want use predefined frequencies rather than a generated list
# FREQUENCY_LIST = []

# Setting this to true will send log messages to console and disable progress bars and countdown timers
DEBUG = False

#-------------------Folder defaults-------------------
# change these to specify a different directory to save data files and log files
DATA_DIR = os.path.join(ROOT,'data')
LOG_DIR = os.path.join(ROOT,'log')

# if you wish to receive email updates when the program completes each step
# emails will be received from geophysicslabnotifications@gmail.com
# emails will also include a .csv file of the data collected over the step.
# note: this is a beta feature and should work, however it depends on google security settings of the outgoing account
EMAIL = {
    'pw': os.environ.get('EMAIL_PW',''),
    'from': os.environ.get('EMAIL_FROM',''),
    'to': 'samuel.jennings@adelaide.edu.au',
}






