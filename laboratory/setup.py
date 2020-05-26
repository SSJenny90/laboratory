"""
This file contaings settings specific to this laboratory and shouldn't need to be changed.
Proceed with caution when changing these.
"""

import os

ROOT = os.getcwd()
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