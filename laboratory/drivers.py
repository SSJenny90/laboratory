"""
Contains the drivers for each instrument in the laboratory.
"""

import math
import os
import pickle
from functools import wraps
import numpy as np
from datetime import timedelta
import time


from serial.tools import list_ports
import minimalmodbus
import visa
from alicat import FlowController, FlowMeter
from laboratory import config, processing
from laboratory.utils import loggers
from laboratory.utils.exceptions import (CalibrationError,
                                         InstrumentConnectionError,
                                         InstrumentReadError,
                                         InstrumentWriteError)

logger = loggers.lab(__name__)

def instrument_command(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        for i in range(config.GLOBAL_MAXTRY):
            try:
                return func(*args,**kwargs)
            except Exception as e:
                if i == config.GLOBAL_MAXTRY-1:
                    logger.error('Error: Communication with the {} failed! Check log for details'.format(args[0].__class__.__name__))
                    logger.error(InstrumentReadError(e))
                    if kwargs.get('message'):
                        logger.error(kwargs['message'])
                    return False
    return wrapper


class USBSerialInstrument():
    """Base class for instruments that connect via USB"""

    def __init__(self, port):
        try:
            self.device = visa.ResourceManager().open_resource(port)
        except visa.VisaIOError as e:
            self.status = False
            logger.error(InstrumentConnectionError(
                'Could not connect to the {}!'.format(self.__class__.__name__)))
            logger.debug(e)
        else:
            logger.info('{} connected at {}'.format(
                self.__class__.__name__, port))
            self.status = True

        self.errors = []

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key, val in self.__dict__.items()])

    @instrument_command
    def read(self, command, message=''):
        logger.debug('\t{}...'.format(message))
        return self.device.query_ascii_values(command)

    @instrument_command
    def write(self, command, message='', val='\b\b\b  '):
        logger.debug('\t{} to {}'.format(message, val))
        self.device.write(command)  # sets format to ascii

    def read_string(self, command, message=''):
        for i in range(config.GLOBAL_MAXTRY):
            if message:
                logger.debug('{}...'.format(message))
            try:

                return self.device.query(command).rstrip()
            except Exception as e:
                if i == config.GLOBAL_MAXTRY-1:
                    logger.error(
                        'Error: "{}" failed! Check log for details'.format(message))
                    logger.debug(InstrumentReadError(e))
                    return False

    def reset(self):
        """Resets the LCR meter"""
        return self.write('*RST;*CLS', 'Resetting device')

    def shutdown(self):
        """Shuts down the DAQ"""
        self.reset()
        self.device.close()  # close port to the DAQ
        logger.critical('The {} has been shutdown'.format(
            self.__class__.__name__))


class LCR(USBSerialInstrument):
    """Driver for the E4980A Precision LCR Meter, 20 Hz to 2 MHz

        =============== ===========================================================
        Attribute       Description
        =============== ===========================================================
        status          whether the instrument is connected
        device          port name
        =============== ===========================================================

        """

    def __init__(self):
        self.address = config.LCR['address']
        super().__init__(port=self.address)

    def get_complex_impedance(self):
        """Collects complex impedance from the LCR meter"""
        self.trigger()
        line = self.read('FETCh?')
        return {key: np.nan if value == 9.9e+37 else value for key, value in zip(['z', 'theta'], line)}

    def configure(self, freq=None):
        """Appropriately configures the LCR meter for measurements"""
        logger.debug('Configuring LCR meter...')
        self.reset()
        self._set_format()
        self.display('list')
        self.function()
        if freq is not None:
            freq = np.around(np.geomspace(20, 2*10**6, 50))
        self.write_freq(freq)
        self.list_mode('step')
        self._set_source()
        self._set_continuous()

    def trigger(self):
        """Triggers the next measurement"""
        return self.write('TRIG:IMM')

    def write_freq(self, freq):
        """Writes the desired frequencies to the LCR meter

        :param freq: array of frequencies
        :type freq: array like
        """
        freq_str = ','.join('{}'.format(n) for n in freq)
        return self.write(':LIST:FREQ ' + freq_str, message='Loading frequencies')

    def _set_format(self, mode='ascii'):
        """Sets the format type of the LCR meter. Defaults to ascii. TODO - allow for other format types"""
        return self.write('FORM:ASC:LONG ON', "Setting format", mode)

    def function(self, mode='impedance'):
        """Sets up the LCR meter for complex impedance measurements"""
        return self.write('FUNC:IMP ZTR', "Setting measurement type", mode)

    def _set_continuous(self, mode='ON'):
        """Allows the LCR meter to auto change state from idle to 'wait for trigger'"""
        return self.write('INIT:CONT ON', 'Setting continuous', mode)

    def list_mode(self, mode=None):
        """Instructs LCR meter to take a single measurement per trigger"""
        # return self.write('LIST:MODE STEP',"Setting measurement",mode)
        mode_options = {'step': 'STEP', 'sequence': 'SEQ'}
        if mode:
            if mode in mode_options:
                return self.write('LIST:MODE {}'.format(mode_options[mode]), 'Setting list mode', mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self.read_string('LIST:MODE?', 'Getting list mode')
            for key, value in mode_options.items():
                if value == mode:
                    return key

    def display(self, mode=None):
        """Sets the LCR meter to display frequencies as a list"""
        mode_options = {'measurement': 'MEAS', 'list': 'LIST'}
        if mode:
            if mode in mode_options:
                return self.write('DISP:PAGE {}'.format(mode_options[mode]), 'Setting page display', mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self.read_string('DISP:PAGE?', 'Getting page display')
            for key, value in mode_options.items():
                if value == mode:
                    return key

    def _set_source(self, mode='remote'):
        """Sets up the LCR meter to expect a trigger from a remote source"""
        return self.write('TRIG:SOUR BUS', 'Setting trigger', mode)


class DAQ(USBSerialInstrument):
    """Driver for the 34970A Data Acquisition / Data Logger Switch Unit

        ============== ======================================================
        Attributes      message
        ============== ======================================================
        maxtry          max number to attempt command
        status          whether the instrument is connected
        therm           specifies type of thermistor
        tref            '101' - channel for thermistor
        te1             '104' - channel for electrode 1
        te2             '105' - channel for electrode 2
        volt            '103' - channel for voltage measurements
        switch          '205','206' - channels for switch between LCR and temp measurements
        address         computer port address
        ============== ======================================================

        .. note::

            do not change class attributes unless the physical wiring has been changed within the DAQ
        """
    # these attributes must only be changed if the physical wiring has been changed. if required, change values in the config.py file
    tref = str(config.DAQ['channels']['reference_temperature'])
    te1 = str(config.DAQ['channels']['electrode_a'])
    te2 = str(config.DAQ['channels']['electrode_b'])
    volt = str(config.DAQ['channels']['voltage'])
    switch = ','.join([str(x) for x in config.DAQ['channels']['switch']])

    def __init__(self):
        self.address = config.DAQ['address']
        super().__init__(port=self.address)
        self.configure()

    @property
    def mean_temp(self):
        vals = self.get_temp()
        return round((vals['thermo_1'] + vals['thermo_2']) / 2, 2)

    def configure(self):
        """Configures the DAQ according to the current wiring"""

        logger.debug('Configuring DAQ...')
        self.reset()

        self._config_temp()
        self._config_volt()

        # close the channels connecting the actuator to the lcr
        self.close_channels('203,204,207,208')

        # switch to thermopower measurements. these generally occur first
        self.toggle_switch('thermo')

        if self.status:
            logger.debug('DAQ configured correctly')
        else:
            logger.info('Could not correctly configure DAQ')

    def get_temp(self):
        """Scans the thermistor and thermocouples for temperature readings

        :returns: [tref,te1,te2]
        :rtype: list of floats (degrees Celsius)
        """
        channels = [self.tref,self.te1, self.te2]
        command = 'ROUT:SCAN (@{})'.format(','.join(channels))
        self.write('TRIG:COUNT 1')
        self.write(command)

        data = self.read('READ?', 'Getting temperature data')
        if data:
            return {k: v for k, v in zip(['reference', 'thermo_1', 'thermo_2'], data)}
        else:
            return [np.nan]*3
            
    def get_voltage(self,count=20,seconds=None):
        """Gets voltage across the sample from the DAQ

        :returns: voltage [microvolts]
        :rtype: float
        """
        self.write('ROUT:SCAN (@{})'.format(self.volt))

        if seconds:
            self.write('TRIG:COUNT INFINITY')
            self.write('INIT')
            time.sleep(seconds)
            self.write('ABORt')
        else:
            self.write('TRIG:COUNT {}'.format(count))
            self.write('INIT')


        time.sleep(10)
        x = self.read('FETCh?')
        if x:
            x = np.array(x[1:]) * 10e3
            result = {'voltage':x.mean().round(3), 'volt_stderr': x.std(ddof=1).round(3)}
            if seconds:
                result.update(volt_count=len(x))

        return result

    def get_thermopower(self):
        """Collects both temperature and voltage data and returns a dict"""
        return {**self.get_temp(), **self.get_voltage()}

    def toggle_switch(self, command):
        """Opens or closes the switch to the lcr. Must be closed for impedance measurements and open for thermopower measurements.

        :param command: either 'thermo' to make thermopower measurements or 'impedance' for impedance measurements
        :type command: str
        """
        command_list = {
            'thermo': 'OPEN',
            'impedance': 'CLOS'
        }

        if command_list.get(command):
            inst_command = 'ROUT:{} (@{})'.format(
                command_list[command], self.switch)
        else:
            raise ValueError('Unkown command for DAQ')
        return self.write(inst_command, 'Flipping switch', command)

    def has_errors(self):
        """Reads errors from the DAQ (unsure if working or not)"""
        errors = self.write('SYST:ERR?')
        logger.error(errors)

    def open_channels(self, channels):

        if isinstance(channels, list):
            channels = ','.join(channels)

        command = 'ROUT:OPEN (@{})'.format(channels)
        return self.write(command, 'Opening channels', command)

    def close_channels(self, channels):

        if isinstance(channels, list):
            channels = ','.join(channels)

        command = 'ROUT:CLOS (@{})'.format(channels)
        return self.write(command, 'Closing channels', command)

    def _config_temp(self):
        """Configures the thermistor ('tref') as 10,000 Ohm
        Configures both electrodes ('te1' and 'te2') as S-type thermocouples
        Sets units to degrees celsius
        """
        # configure thermocouples on channel 104 and 105 to type S
        self.write('CONF:TEMP TC,S,(@{},{})'.format(self.te1,
                                                    self.te2), 'Setting thermocouples', 'S-type')

        # configure 10,000 ohm thermistor
        self.write('CONF:TEMP THER,{},(@{})'.format(config.DAQ['thermistor']*1000,
                                                    self.tref), 'Setting thermistor', '{} k.Ohm'.format(config.DAQ['thermistor']))

        # set units to degrees C
        self.write('UNIT:TEMP C,(@{},{},{})'.format(self.tref,
                                                    self.te1, self.te2), 'Setting temperature units', 'Celsius')

        # set thermocouples to use external reference junction
        self.write('SENS:TEMP:TRAN:TC:RJUN:TYPE EXT,(@{},{})'.format(self.te1,
                                                                     self.te2), 'Setting reference junction', 'external')

        # sets integration time to 10 cycles. affects measurement resolution
        self.write('SENS:TEMP:NPLC {},(@{},{},{})'.format(config.DAQ['temp_integration_time'], self.tref, self.te1,
                                                          self.te2), 'Setting temperature integration time', '{} cycle/s'.format(config.DAQ['temp_integration_time']))

    def _config_volt(self):
        """Configures the voltage measurements"""
        self.write('CONF:VOLT:DC (@{})'.format(self.volt),
                   'Setting voltage', 'DC')
        self.write('SENS:VOLT:DC:NPLC {},(@{})'.format(config.DAQ['volt_integration_time'], self.volt),
                   'Setting voltage integration time', '{} cycle/s'.format(config.DAQ['volt_integration_time']))


class Furnace(minimalmodbus.Instrument):
    """Driver for the Eurotherm 3216 Temperature Controller

        .. note::
        units are in °C

        =============== ===========================================================
        Attributes      message
        =============== ===========================================================
        default_temp     revert to this temperature when resetting
        status           whether the instrument is connected
        address         computer port address
        =============== ===========================================================

        """

    default_temp = config.RESET_TEMPERATURE

    def __init__(self):
        self.port = config.FURNACE_ADDRESS
        # self.target = self.default_temp
        try:
            super().__init__(self.port, 1)
        except Exception as e:
            logger.error(InstrumentConnectionError(
                'Could not connect to the {}!'.format(self.__class__.__name__)))
            logger.debug(e)
        else:
            logger.info('{} connected at {}'.format(
                self.__class__.__name__, self.port))
            # self.close_port_after_each_call = True
            self.serial.baudrate = 9600
            # self.command(276,1) #set to remote setpoint
            self.status = True
            self.configure()

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key, val in self.__dict__.items()])

    def configure(self):
        """Configures the furnace based on settings specified in the configuration file"""
        logger.debug('Configuring furnace...')
        # self.setpoint_2()
        self.setpoint_select('setpoint_1')
        self.display(1)
        self.timer_type('dwell')
        self.timer_end_type('current')
        self.timer_resolution('M:S')
        self.timer_status('reset')

    def display(self, display_type=0, address=106):
        """
        Select the display mode for the furnace.

        options:
            0 : Standard PV and SP
            1 : PV and output power
            2 : PV and time remaining
            3 : PV and timer elapsed
            4 : PV and alarm 1 setpoint
            5 : PV and load current
            6 : PV only
            7 : PV and composite SP/time remaining

        :param display_type: any display type options as above
        :type display_type: int

        :returns: True if succesful, False if not
        """
        display_options = [0, 1, 2, 3, 4, 5, 6, 7]
        return self.command(address, 
            value = display_type,
            message = 'display type', 
            options = {str(v): v for v in display_options})


        # if display_type in display_options:
        #     return self.command(address, display_type, message='Setting display type')
        # else:
        #     logger.info('Incorrect argument for variable "display_type". Must be one of {}'.format(
        #         display_options))

    def heating_rate(self, heat_rate=None, address=35, decimals=1):
        """If heat_rate is specified, this method sets the heating rate of the furnace.
        If no argument is passed it queries the current heating rate

        :param heat_rate: heating rate in °C/min
        :type heat_rate: float, int

        :Example:

        >>> lab.furnace.heating_rate()
        10.0
        >>> lab.furnace.heating_rate(5)
        True
        >>> lab.furnace.heating_rate()
        5.0
        """
        return self.command(address, 
            value = heat_rate,
            message = 'heating rate',
            decimals=decimals)

    def indicated(self, address=1):
        """[Query only] Queries the current temperature of furnace.

        :returns: Temperature in °C if succesful, else False
        """
        return self.command(address, message='setpoint 1')

    def reset_timer(self):
        """Resets the current timer and immediately restarts. Used in for loops to reset the timer during every iteration. This is a safety measure should the program lose communication with the furnace.
        """
        if self.timer_status('reset'):
            return self.timer_status('run')

    def setpoint_1(self, temperature=None, address=24):
        """If temperature is specified, this method sets the target temperature of setpoint 1. If no argument is passed it queries the current target of setpoint 1.

        :param temperature: temperature in °C
        :type temperature: float, int

        :Example:

        >>> lab.furnace.setpoint_1()
        350.0
        >>> lab.furnace.setpoint_1(400)
        True
        >>> lab.furnace.setpoint_1()
        400
        """
        return self.command(address, temperature, message='setpoint 1')

    def setpoint_2(self, temperature=None, address=25):
        """If temperature is specified, this method sets the target temperature of setpoint 2. If no argument is passed it queries the current target of setpoint 2.

        .. note::
           Setpoint 2 is used as a 'safe' temperature for the furnace to reset to should something go wrong and communication is lost during high temperature experiments. The value is set during configuration of the instrument from the value RESET_TEMPERATURE in the config file. It is suggeseted to adjust the config file if a change is required rather than call this method directly.

        :param temperature: temperature in °C
        :type temperature: float, int

        :Example:

        >>> lab.furnace.setpoint_2()
        40.0
        >>> lab.furnace.setpoint_2(25.0)
        True
        >>> lab.furnace.setpoint_2()
        25.0
        """
        return self.command(address, temperature, message='setpoint 2')

    def remote_setpoint(self, temperature=None):
        """If temperature is specified, this method sets the target temperature of the remote setpoint. 

        :param temperature: temperature in °C
        :type temperature: float, int

        """
        return self.command(modbus_address=26, value=temperature, message='remote setpoint')

    def setpoint_select(self, selection=None, address=15):
        """If selection is specified, selects the current working setpoint. If no argument is passed, it returns the current working setpoint.

        options:
            'setpoint_1'
            'setpoint_2'

        :param selection: desired working setpoint
        :type selection: str

        """
        return self.command(address, 
            value = selection,
            message = 'current setpoint', 
            options = {'setpoint_1': 0, 'setpoint_2': 1})

    def timer_duration(self, hours=0, minutes=0, seconds=0, address=324):
        """Sets the length of the timer.

        :param minutes: number of minutes
        :type timer_type: int,float

        :param seconds: number of seconds
        :type timer_type: int,float (floats internally converted to int)
        """
        td = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        if td.total_seconds() >= 100*60:
            self.timer_resolution('H:M')
            value = td.total_seconds()/60
        else:
            self.timer_resolution('M:S')
            value = td.total_seconds()

        return self.command(address, 
            value = value,
            message = 'timer duration',)

    def timer_end_type(self, selection=None, address=328):
        """Determines the behavior of the timer. The default configuration in this program is to dwell. If selection is specified, the timer end type will be set accordingly. If no argument is passed, it returns the current end type of the timer.

        .. note::

            This method is only valid if the timer type is set to 'dwell'

        options:
            'off'       : do nothing
            'current'   : dwell at the current setpoint
            'transfer' : transfer to setpoint 2 and dwell

        :param selection: desired type
        :type selection: str

        :Example:

        >>> lab.furnace.timer_type()    #five minutes
        'off'
        >>> lab.furnace.timer_type('dwell')
        True
        >>> lab.furnace.timer_type()
        'dwell'
        """
        return self.command(address, 
            value = selection,
            message = 'timer end type', 
            options = {'off': 0, 'current': 1, 'transfer': 2})

    def timer_resolution(self, selection=None, address=320):
        """Determines whether the timer display is in Hours:Mins or Mins:Seconds

        options:
            'H:M'   : Hours:Minutes
            'M:S'   : Minutes:Seconds

        :param selection: desired configuration
        :type selection: str
        """
        return self.command(address, 
            value = selection,
            message = 'timer resolution', 
            options = {'H:M': 0, 'M:S': 1})

    def timer_status(self, status=None, address=23):
        """Controls the furnace timer. If status is specified, the timer status will be set accordingly. If no argument is passed, it returns the current status of the timer.

        options:
            'reset' : resets the timer back to zero
            'run'   : starts the timer
            'hold'  : stops the timer

        :param status: desired working setpoint
        :type status: str

        :Example:

        >>> lab.furnace.timer_duration(minutes=5)    #five minutes
        True
        >>> lab.furnace.timer_status()
        'reset'
        >>> lab.furnace.timer_status('run')
        True
        >>> lab.furnace.setpoint_1()
        400
        """
        return self.command(address, 
            value = status,
            message = 'timer status', 
            options = {'reset': 0, 'run': 1, 'hold': 2})

    def timer_type(self, selection=None, address=320):
        """Determines the behavior of the timer. The default configuration in this program is to dwell. If status is specified, the timer status will be set accordingly. If no argument is passed, it returns the current status of the timer.

        options:
            'off'       : no timer
            'dwell'     : dwell at a fixed temperature until the timer runs out
            'delay'     : delayed start time
            'soft_start': start a process at reduced power

        :param selection: desired type
        :type selection: str

        :Example:

        >>> lab.furnace.timer_type()    #five minutes
        'off'
        >>> lab.furnace.timer_type('dwell')
        True
        >>> lab.furnace.timer_type()
        'dwell'
        """
        return self.command(address, 
            value = selection,
            message = 'timer type', 
            options = {'off': 0, 'dwell': 1, 'delay': 2, 'soft_start': 3})

    def flush_input(self):
        logger.debug('Flushing furnace input')
        self.serial.reset_input_buffer()

    def flush_output(self):
        logger.debug('Flushing furnace output')
        self.serial.reset_output_buffer()

    def shutdown(self):
        self.setpoint_1(40)
        self.timer_status('reset')

    def reconnect(self):
        self.__init__()

    @instrument_command
    def command(self, modbus_address, value=None, options={}, message='', decimals=0):
        '''Set or read value at specified modbus address.

        :param modbus_address: see furnace manual for adresses
        :type modbus_address: float, int

        :param value: value to be sent to the furnace
        :type value: float, int

        If a value is supplied it will return True if the command was succesful. If a value is not supplied, it will return the output of the instrument at specified modbus address.
        '''
        if value is not None:
            # print(modbus_address, options.get(value,value), decimals)
            logger.debug('Setting {} of furnace.'.format(message))
            self.write_register(modbus_address, options.get(value,value), number_of_decimals=decimals)
            return True
        else:
            logger.debug('Getting {} from furnace.'.format(message))
            output = self.read_register(modbus_address, number_of_decimals=decimals)
            for k, v in options.items():
                if v == output:
                    return k
            return output


class Stage():
    """Driver for the linear stage

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry          max number to attempt command
    status          whether the instrument is connected
    home            approximate xpos where te1 == te2
    max_xpos        maximum x-position of the stage
    address         computer port address
    position        current position of the stage
    =============== ===========================================================
    """

    def __init__(self, ports=None):
        self.port = config.STAGE['address']
        self.pulse_equiv = config.STAGE['pitch'] * \
            config.STAGE['step_angle'] / (360*config.STAGE['subdivision'])
        self.max_xpos = config.STAGE['max_stage_position']
        self.profile = self.get_temp_profile()
        self.home = self.find_gradient_position(0)
        self._connect(ports)
        self.go_to(self.home)

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key, val in self.__dict__.items()])

    @property
    def position(self):
        return self.command('?X', 'Getting x-position')

    def find_gradient_position(self,target_gradient):
        data = self.profile
        m, b = np.polyfit(data.x_position,data.thermo_1 - data.thermo_2, 1)
        return int(round((target_gradient-b)/m))

    def get_temp_profile(self):
        calibration_file = os.path.join(config.CALIBRATION_DIR, 'furnace_profile.pkl')
        try:
            f = open(calibration_file, 'rb')  # Overwrites any existing file.
        except FileNotFoundError:
            logger.warning(
                'WARNING: The linear stage requires calibration in order to find the position where both thermocouples sit at the peak temperature.')
        else:
            data = pickle.load(f)
            f.close()
        return data

    def _connect(self, ports):
        """
        attempts connection to the stage

        :param ports: list of available ports
        :type ports: list, string
        """
        if not ports:
            ports = self.port

        if not isinstance(ports, list):
            ports = [ports]

        rm = visa.ResourceManager()
        for port in ports:
            logger.debug('Searching for stage at {}...'.format(port))

            for i in range(0, config.GLOBAL_MAXTRY):
                try:
                    self.Ins = rm.open_resource(port)
                    if not self.is_connected():
                        raise InstrumentConnectionError(
                            'Not at port {}'.format(port))
                except Exception as e:
                    if i == config.GLOBAL_MAXTRY-1:
                        logger.debug('{} {}'.format(e, port))
                        logger.info('{} {}'.format(e, port))
                        self.status = False
                else:
                    logger.info('{} connected at {}'.format(
                        self.__class__.__name__, port))
                    self.status = True
                    return

    def is_connected(self):
        return self.command('?R')

    def center(self):
        """Moves stage to the absolute center"""
        return self.go_to(self.max_xpos/2)

    def get_settings(self):
        output = {'baudrate': self.Ins.baud_rate,
                  'bytesize': self.Ins.data_bits,
                  'parity': self.Ins.parity._name_,
                  'stopbits': int(self.Ins.stop_bits._value_/10),
                  'timeout': self.Ins.timeout, }
        return output

    def move(self, displacement):
        """Moves the stage in the positive or negative direction

        :param displacement: positive or negative displacement [in mm]
        :type displacement: float, int
        """
        command = self._convertdisplacement(displacement)
        return self.command(command, 'Moving stage {}mm'.format(displacement))

    def go_to(self, position):
        """Go to an absolute position on the linear stage

        :param position: absolute position of stage in controller pulse units - see manual
        :type position: float, int
        """
        if not position or position == 'start':
            return self.reset()

        if isinstance(position, str):
            if position == 'center':
                position = self.max_xpos/2
            elif position == 'end':
                position = self.max_xpos
            else:
                raise ValueError(
                    '{} is not a valid command for the lineaer stage'.format(position))

        
        if position > self.max_xpos:
            position = self.max_xpos
        elif position <= 0:
            return self.reset()

        current_position = self.position
        if current_position is not None:
            displacement = int(position - self.position)
            if not displacement:
                return True
        else:
            return False

        return self.command('X{0:+}'.format(displacement), 'Setting x-position')

    def speed(self, stage_speed=None):
        """Get or set the speed of the stage

        :param stage_speed: speed of the stage in mm/s
        :type stage_speed: float, int
        """
        # this is a get request
        if stage_speed is None:
            speed = self.command('?V', 'Getting stage speed')
            return self._convertspeed(speed, False)
        # this is a set request
        else:
            command = self._convertspeed(stage_speed)
            return self.command(command, 'Setting stage speed')

    def go_home(self):
        """Moves furnace to the center of the stage (x = 5000)
        """
        return self.go_to(self.home)

    def reset(self):
        """Resets the stage position so that the absolute position = 0"""
        return self.command('HX0', 'Resetting stage...')

    def _convertdisplacement(self, displacement):
        """Converts a positive or negative displacement (in mm) into a command recognisable by the stage"""

        direction = '+' if displacement > 0 else '-'
        # convert from mm to steps for motioncontroller
        magnitude = str(int(abs(displacement)/self.pulse_equiv))
        return 'X'+direction+magnitude  # command for motion controller

    def _convertspeed(self, speed, default=True):
        """Converts a speed given in mm/s into a command recognisable by the stage"""
        if default:
            Vspeed = (speed*0.03/self.pulse_equiv) - \
                1  # convert from mm/s to Vspeed
            # command for motion controller
            return 'V' + str(int(round(Vspeed)))
        else:
            return round((speed+1)*self.pulse_equiv/0.03, 2)  # output speed

    @instrument_command
    def command(self,command,message=''):
        self.Ins.clear()
        response = self.Ins.query_ascii_values(command, converter='s')[0]
        if 'OK' in response:
            return True
        elif not 'ERR' in response:
            return int(''.join(x for x in response if x.isdigit()))
        else:
            raise InstrumentReadError("Something wen't wrong")


class AlicatController(FlowController):
    """Base driver for each individual Mass Flow Controller.

        .. note::

            no need to instantiate directly - access these methods and attributes from within :class:`~Drivers.GasControllers`

        Attributes
        ----------
        name : str
            The gas type of the flow controller
        precision : int
            The precision of the flow controller
        upper_limit : int
            The maximum flow rate of the controller

        :Example:

        >>> from laboratory.drivers import instruments
        >>> gas = instruments.connect()

        """

    def __init__(self, port, address, name, upper_limit, precision):
        super().__init__(port, address)
        self.name = name
        self.precision = precision
        self.upper_limit = upper_limit

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key, val in self.__dict__.items() if key not in ['keys', 'gases', 'connection']])

    @instrument_command
    def data(self):
        self.flush()
        return super().get(retries=config.GLOBAL_MAXTRY)

    def mass_flow(self):
        """
        Returns
        -------
        float
            Mass flow in ccm
        """
        return self.data().get('mass_flow',None)

    def pressure(self):
        """
        Returns
        -------
        float
            Pressure in psia.
        """
        return self.data.get('pressure',None)

    def temperature(self):
        """
        Returns
        -------
        float
            Temperature of the gas in degrees C
        """
        return self.data.get('temperature',None)

    def volumetric_flow(self):
        """
        Returns
        -------
        float
            Volumetric flow in CCM.
        """
        return self.data.get('volumetric_flow',None)

    def setpoint(self, setpoint=None):
        """Get or set the current setpoint of the flowmeter

        Parameters
        ----------
        setpoint : float, optional
            The desired setpoint.

        Returns
        -------
        float
            The current setpoint
        """
        self.flush()
        if setpoint is None:
            return self.data.get('setpoint',None)

        elif setpoint > self.upper_limit:
            raise ValueError('{setpoint} is an invalid flow rate. {name} has an upper limit of {limit} SCCM'.format(
                setpoint=setpoint, name=self.name, limit=self.upper_limit))
        else:
            self._test_controller_open()
            logger.debug('Setting {name} to {setpoint} SCCM'.format(
                name=self.name, setpoint=setpoint))
            return self._command('{addr}S{setpoint}\r'.format(addr=self.address,                                                       setpoint=setpoint))

    def reset(self):
        """Sets the massflow to 0 on the current controller"""
        return self.setpoint(0)

    @instrument_command
    def _command(self, command):
        self._write_and_read(command)


class GasControllers():
    """Global driver for all Mass Flow Controllers

        .. note::

            see AlicatController for methods to control individual gases

        Attributes
        ----------
        maxtry (int): Maximum number of attempts to perform a command.
        status : boolean
            connection status of the instrument
        co2 : :class:~`drivers.AlicatController`
            Access to methods controlling the CO2 controller.

        address : str
            The COM port that the device is connected to.


        Example:
            >>> from laboratory.drivers import instruments
            >>> gas = instruments.connect()
            >>> gas_input = {'co2':20,'co_a':15,'co_b':1.2,'h2':7.67}
            >>> gas.set_all(**gas_input)
            True
            >>> gas.get_all()
            {'co2': { 'pressure': 14.86,
                    'temperature': 24.83,
                    'volumetric_flow': 19.8,
                    'mass_flow': 20.0,
                    'setpoint': 20.0},
            'co_a': {'pressure': 14.78,
                    'temperature': 24.69,
                    'volumetric_flow': 14.89,
                    'mass_flow': 15.0,
                    'setpoint': 15.0},
            'co_b': {'pressure': 14.89,
                    'temperature': 24.34,
                    'volumetric_flow': 1.181,
                    'mass_flow': 1.2,
                    'setpoint': 1.2},
            'h2': {  'pressure': 14.8,
                    'temperature': 23.9,
                    'volumetric_flow': 7.59,
                    'mass_flow': 7.67,
                    'setpoint': 7.67}}
            >>> gas.co2.setpoint(12.57)
            >>> gas.co2.get()   #return results from an individual controller
            {'pressure': 14.83,
            'temperature': 24.86,
            'volumetric_flow': 12.57,
            'mass_flow': 12.57,
            'setpoint': 12.57}
        """
    all = ['co2', 'co_a', 'co_b', 'h2']

    def __init__(self):
        self.status = False
        self.port = config.MFC_ADDRESS
        self._connect()

    def __str__(self):
        return '\n\n'.join([gas + ':\n\n' + getattr(self, gas).__str__() for gas in ['co2', 'co_a', 'co_b', 'h2']])

    def _connect(self):
        """Connects to the mass flow controllers"""
        controllers = {
            'co2':  config.CO2,
            'co_a': config.CO_A,
            'co_b': config.CO_B,
            'h2':   config.H2}

        self.status = True
        for controller, settings in controllers.items():
            try:
                logger.debug('Connecting {}'.format(controller))
                setattr(self, controller, AlicatController(port=self.port,
                                                           address=settings['address'],
                                                           name=controller,
                                                           upper_limit=settings['upper_limit'],
                                                           precision=settings['precision']))
            except Exception as e:
                logger.error('Gas - FAILED (check log for details)')
                logger.debug(InstrumentConnectionError(e))
                self.status = False

        if self.status:
            logger.info('Gas connected at {}'.format(self.port))

    def get_all(self):
        return {gas: getattr(self, gas).mass_flow() for gas in self.all}

    def set_all(self, gases):
        assert isinstance(gases, dict)
        for gas, setpoint in gases.items():
            gas = getattr(self, gas)
            gas.flush()
            try:
                gas.setpoint(setpoint)
            except ValueError as e:
                logger.error(e)
                raise e

    def reset_all(self):
        """Resets all connected flow controllers to 0 massflow"""
        for gas in self.all:
            getattr(self, gas).reset()

    def flush_all(self):
        """Flushes the input? buffer of all flow controllers"""
        for gas in self.all:
            getattr(self, gas).flush()

    def close_all(self):
        """Closes all flow controllers"""
        for gas in self.all:
            getattr(self, gas).close()

    def shutdown(self):
        self.reset_all()
        self.close_all()

    def set_to_buffer(self, buffer, offset, temp, gas_type):

        log_fugacity = processing.fo2_buffer(temp, buffer) + offset

        if gas_type == 'h2':
            ratio = processing.fugacity_h2(log_fugacity, temp)

            if ratio < 0.5:
                h2 = 50
                co2 = h2*ratio
            elif ratio < 4:
                h2 = 25
                co2 = h2*ratio
            else:
                co2 = 200
                h2 = co2/ratio

            self.set_all({'h2': h2,
                          'co2': co2,
                          'co_a': 0,
                          'co_b': 0, })

        elif gas_type == 'co':
            ratio = processing.fugacity_co(log_fugacity, temp)

            # set the optimal co2 flow rate
            # higher ratios require higher co2 mass flow for greater precision
            if ratio > 1000:
                # co2 = 200
                co2 = 100
            elif ratio > 100:
                # co2 = 100
                co2 = 50
            else:
                # co2 = 50
                co2 = 25

            if co2/ratio >= 20:
                co2 = 20*ratio

            co = round(co2/ratio, 3)

            # sometimes if co is rounded up it pushes co2 over it's limit
            if co*ratio > 200:
                co = co-0.001

            co2 = round(co*ratio, 1)

            if co:
                logger.debug('Desired ratio: {} Actual: {}'.format(ratio, co2/co))

            self.set_all({'co2': co2,
                          'co_a': int(co),
                          'co_b': round(co - int(co), 3),
                          'h2': 0,
                          })
        else:
            logger.error('Incorrect gas type specified!')
            return False

        return [log_fugacity, ratio]
 
    
def get_ports():
    '''Returns a list of available serial ports for connecting to the furnace and stage

    :returns: list of available ports
    :rtype: list, str
    '''
    return {comport.manufacturer: comport.device for comport in list_ports.comports()}


def connect():
    # return LCR(), DAQ(), GasControllers(), Furnace()
    return LCR(), DAQ(), GasControllers(), Furnace(), Stage()


def reconnect(lab_obj):

    # ports = get_ports()

    # if not ports: return
    if not lab_obj.lcr.status:
        lab_obj.lcr = LCR()
    if not lab_obj.daq.status:
        lab_obj.daq = DAQ()
    if not lab_obj.gas.status:
        lab_obj.gas = GasControllers()
    if not lab_obj.furnace.status:
        lab_obj.furnace = Furnace()
    if not lab_obj.stage.status:
        lab_obj.stage = Stage()
    else:
        print('All instruments are connected!')
