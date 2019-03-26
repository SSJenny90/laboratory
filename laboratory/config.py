"""
This is a configuration file for setting up the laboratory. It contains settings to set the name of the the experiment, sample dimensions, instrument addresses and physical constants. Experiment name and sample dimensions should be modified with each new experiment. Everything else can remain as is unless the physical setup of the lab has changed.
"""

EMAIL = 'samuel.jennings@adelaide.edu.au'

#-------------------Experiment settings-------------------
PROJECT_NAME = 'High-T test run'
SAMPLE_THICKNESS = 2.6 #in mm
SAMPLE_DIAMETER = 12.7 #in mm

#-------------------DAQ settings-------------------
DAQ_ADDRESS = 'USB0::0x0957::0x2007::MY49021284::INSTR'
#daq channels
REFERENCE_TEMPERATURE = '101'
ELECTRODE_1 = '104'
ELECTRODE_2 = '105'
VOLTAGE = '103'
SWITCH = '205,206'
THERMISTOR_OHMS = 10000
TEMPERATURE_INTEGRATION_TIME = 10   #in cycles
VOLTAGE_INTEGRATION_TIME = 1   #in cycles

#-------------------LCR settings-------------------
LCR_ADDRESS = 'USB0::0x0957::0x0909::MY46312484::INSTR'
MINIMUM_FREQ = 20       #in Hz
MAXIMUM_FREQ = 2000000  #in Hz (2MHz)

#-------------------Furnace settings-------------------
FURNACE_ADDRESS = 'COM5'
RESET_TEMPERATURE = 40       #temperature the furnace resets to

#-------------------Motor settings-------------------
MOTOR_ADDRESS = 'COM8'
SUBDIVISION = 2  #from back of motion controller
STEP_ANGLE = 0.9  #from the side of the motor
PITCH = 4        #in mm - from the optics focus website
MAXIMUM_STAGE_POSITION = 10000
TEMPERATURE_EQUILIBRIUM_POSITION = 5500

#-------------------Gas settings-------------------
MFC_ADDRESS = 'COM6'    #for windows
# MFC_ADDRESS = '/dev/tty.SLAB_USBtoUART'   #for mac
H2_UPPER_LIMIT = 50
H2_PRECISION = 2
CO2_UPPER_LIMIT = 200
CO2_PRECISION = 2
CO_A_UPPER_LIMIT = 50
CO_A_PRECISION = 2
CO_B_UPPER_LIMIT = 2
CO_B_PRECISION = 3
