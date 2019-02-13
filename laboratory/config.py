"""
This is a configuration file for setting up the users laboratory. It contains settings for experiment name, sample dimensions, instrument addresses and physical constants. Experiment name and sample dimensions should be modified with each new experiment. Everything else can remain as is unless the physical setup of the lab has changed.
"""

email = 'samuel.jennings@adelaide.edu.au'

#-------------------Experiment settings-------------------
name = 'High-T test run'
sample_thickness = 2.6 #in mm
sample_diameter = 12.7 #in mm

#-------------------DAQ settings-------------------
daq_address = 'USB0::0x0957::0x2007::MY49021284::INSTR'
#daq channels
tref = '101'
te1 = '104'
te2 = '105'
volt = '103'
switch = '205,206'
thermistor = 10000
temp_integration_time = 10   #in cycles
volt_integration_time = 1   #in cycles

#-------------------LCR settings-------------------
lcr_address = 'USB0::0x0957::0x0909::MY46312484::INSTR'
min_freq = 20       #in Hz
max_freq = 2000000  #in Hz (20MHz)

#-------------------Furnace settings-------------------
furnace_address = 'COM4'
default_temp = 40       #temperature the furnace resets to

#-------------------Motor settings-------------------
motor_address = 'COM9'
subdivision = 2  #from back of motion controller
step_angle = 0.9  #from the side of the motor
pitch = 4        #in mm - from the optics focus website
max_xpos = 10000

#-------------------Mass Flow settings-------------------
mfc_address = 'COM8'    #for windows
# mfc_address = '/dev/tty.SLAB_USBtoUART'   #for mac
