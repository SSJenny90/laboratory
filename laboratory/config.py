"""
This is a configuration file for setting up the laboratory. It contains settings to set the name of the the experiment, sample dimensions, instrument addresses and physical constants. Experiment name and sample dimensions should be modified with each new experiment. Everything else can remain as is unless the physical setup of the lab has changed.
"""
import os
from datetime import datetime


#-------------------Experiment settings-------------------
PROJECT_NAME = '2 Week Test'
SAMPLE_THICKNESS = 2.6 #in mm
SAMPLE_DIAMETER = 12.7 #in mm
SAMPLE_AREA = 97.686 #in mm^2 - ONLY SET IF SAMPLE IS NOT A COMPLETE DISK AND AREA MUST BE CALCULATED MANUALLY
"""Area of the sample in :math:`mm^{2}`. Useful if the sample is not a perfect disc."""

MINIMUM_FREQ = 20       #in Hz
MAXIMUM_FREQ = 2000000  #in Hz (2MHz)
FREQ_LOG_SCALE = False
FREQUENCY_LIST = []

DEBUG = False

#if you wish to receive email updates when the program completes each step
EMAIL = {
    'pw': os.environ.get('EMAIL_PW',''),
    'from': os.environ.get('EMAIL_FROM',''),
    'to': 'samuel.jennings@adelaide.edu.au',
}

#-------------------Folder defaults-------------------
ROOT = os.getcwd()
DATA_DIR = os.path.join(ROOT,'data')
LOG_DIR = os.path.join(ROOT,'log')
CALIBRATION_DIR = os.path.join(ROOT,'laboratory','calibration')


GLOBAL_MAXTRY = 5
#-------------------DAQ settings-------------------
DAQ = {
    'address': 'USB0::0x0957::0x2007::MY49021284::INSTR',
    'channels': {
        'reference_temperature': 101,
        'electrode_a': 104,
        'electrode_b': 105,
        'voltage': 103,
        'switch': [205,206],
    },
    'thermistor': 10,
    'temp_integration_time':10,
    'volt_integration_time':1,
}

#-------------------LCR settings-------------------
LCR_ADDRESS = 'USB0::0x0957::0x0909::MY46312484::INSTR'

#-------------------Furnace settings-------------------
FURNACE_ADDRESS = 'COM8'
RESET_TEMPERATURE = 40       #temperature the furnace resets to

#-------------------Stage settings-------------------
STAGE = {
    'address': 'COM5',
    'subdivision': 2, #from back of motion controller
    'step_angle': 0.9, #from the side of the stage
    'pitch': 4, #in mm - from the optics focus website
    'max_stage_position': 10000,
}


#-------------------Gas settings-------------------
MFC_ADDRESS = 'COM6'    #for windows
CO2 = { 'address':'A',
        'upper_limit': 200,
        'precision':2}

CO_A = {'address':'B',
        'upper_limit': 50,
        'precision':2}

CO_B = {'address':'C',
        'upper_limit': 2,
        'precision':3}

H2 = {  'address':'D',
        'upper_limit': 50,
        'precision':2}




