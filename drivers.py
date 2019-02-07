#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contains drivers for each instrument in use in the laboratory.
"""
import utils
import serial.tools.list_ports
import minimalmodbus
minimalmodbus.BAUDRATE = 9600
minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = True
import visa
import sys
import glob
from alicat import FlowController
import time
import numpy as np
import math
import config
import json

logger = utils.lab_logger(__name__)

def get_ports():
    '''Returns a list of available serial ports for connecting to the furnace and motor

    :returns: list of available ports
    :rtype: list, str
    '''

    if sys.platform.startswith('win'):
        usbports = [comport.device for comport in serial.tools.list_ports.comports()]
        # usbports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        usbports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        usbports = glob.glob('/dev/tty.usb*')
    else:
        raise EnvironmentError('Unsupported platform')

    ports = []

    for port in usbports:
        try:
            s = serial.Serial(port)
            s.close()
            ports.append(port)
        except (OSError, serial.SerialException):
            pass

    if not ports:
        logger.critical('Could not open any serial ports. Check your connections and try again.')
    else:
        logger.debug('Found {} serial ports: {}'.format(len(ports),ports))
    return ports

def _load_instruments():

    lcr = LCR()
    mfc = MFC()
    daq = DAQ()
    # ports = get_ports()
    # furnace = Furnace()
    motor = Motor()

    return lcr, daq, mfc, furnace, motor

def _reconnect(lab_obj):

    ports = get_ports()

    if not ports: return
    if not lab_obj.lcr.status: lab_obj.lcr = LCR()
    if not lab_obj.daq.status: lab_obj.daq = DAQ()
    if not lab_obj.mfc.status: lab_obj.mfc = MFC()
    if not lab_obj.furnace.status: lab_obj.furnace = Furnace()
    if not lab_obj.motor.status: lab_obj.motor = Motor()

class LCR():
    """
    Driver for the E4980A Precision LCR Meter, 20 Hz to 2 MHz

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry          max number to attempt command
    status          whether the instrument is connected
    address         port name
    =============== ===========================================================

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    connect         attempt to connect to the LCR meter
    configure       configures device for measurements
    write_freq      transfers desired frequencies to the LCR meter
    trigger         gets impedance for one specified frequency
    get_complexZ    retrieves complex impedance from the device
    reset           resets the device
    =============== ===========================================================
    """

    def __init__(self):

        self.address = config.lcr_address
        self.maxtry = 5
        self.status = False

        self._connect()

    def __str__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\n{}\nstatus = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status
            )

    def _connect(self):
        """Connects to the LCR meter"""
        try:
            rm = visa.ResourceManager() #used by pyvisa to connect to LCR and DAQ. Leave.
            self.Ins = rm.open_resource(self.address)
        except Exception as e:
            logger.error('    LCR - FAILED (check log for details)')
            logger.debug(e)
            self.status = False
        else:
            logger.info('    LCR - CONNECTED!')
            self.status = True

    def get_complexZ(self):
        """Collects complex impedance from the LCR meter"""
        self.trigger()
        return self._read('FETCh?','Collecting impedance data',to_file=False)

    def configure(self,freq):
        """Appropriately configures the LCR meter for measurements"""
        print('')
        logger.info('Configuring LCR meter...')
        self.reset()
        self._set_format()
        self.display('list')
        self.function()
        self.write_freq(freq)
        self.list_mode('step')
        self._set_source()
        self._set_continuous()

    def trigger(self):
        """Triggers the next measurement"""
        return self._write('TRIG:IMM','Trigger next measurement',to_file=False)

    def write_freq(self,freq):
        """Writes the desired frequencies to the LCR meter

        :param freq: array of frequencies
        :type freq: np.ndarray
        """
        freq_str = ','.join('{}'.format(n) for n in freq)
        return self._write(':LIST:FREQ ' + freq_str,'Loading frequencies')

    def reset(self):
        """Resets the LCR meter"""
        return self._write('*RST;*CLS','Resetting device')

    def _set_format(self,mode='ascii'):
        """Sets the format type of the LCR meter. Defaults to ascii. TODO - allow for other format types"""
        return self._write('FORM:ASC:LONG ON',"Setting format",mode)

    def function(self,mode='impedance'):
        """Sets up the LCR meter for complex impedance measurements"""
        return self._write('FUNC:IMP ZTR',"Setting measurement type",mode)

    def _set_continuous(self,mode='ON'):
        """Allows the LCR meter to auto change state from idle to 'wait for trigger'"""
        return self._write('INIT:CONT ON','Setting continuous',mode)

    def list_mode(self,mode=None):
        """Instructs LCR meter to take a single measurement per trigger"""
        # return self._write('LIST:MODE STEP',"Setting measurement",mode)
        mode_options = {'step':'STEP','sequence':'SEQ'}
        if mode:
            if mode in mode_options:
                return self._write('LIST:MODE {}'.format(mode_options[mode]),'Setting list mode',mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self._read_string('LIST:MODE?','Getting list mode')
            for key,value in mode_options.items():
                if value == mode: return key

    def display(self,mode=None):
        """Sets the LCR meter to display frequencies as a list"""
        mode_options = {'measurement':'MEAS','list':'LIST'}
        if mode:
            if mode in mode_options:
                return self._write('DISP:PAGE {}'.format(mode_options[mode]),'Setting page display',mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self._read_string('DISP:PAGE?','Getting page display')
            for key,value in mode_options.items():
                if value == mode: return key

    def _set_source(self,mode='remote'):
        """Sets up the LCR meter to expect a trigger from a remote source"""
        return self._write('TRIG:SOUR BUS','Setting trigger',mode)

    def _write(self,command,message,val='\b\b\b  ',to_file=True):
        c=0
        while c <= self.maxtry:
            try:
                if to_file: logger.debug('\t{} to {}'.format(message,val))
                self.Ins.write(command)         #sets format to ascii
                return True
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

    def _read(self,command,message,to_file=True):
        c=0
        while c <= self.maxtry:
            try:
                if to_file: logger.debug('\t{}...'.format(message))
                vals = self.Ins.query_ascii_values(command)
                return vals
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False

            c=c+1

    def _read_string(self,command,message,to_file=True):
        c=0
        while c <= self.maxtry:
            try:
                if to_file: logger.debug('\t{}...'.format(message))
                vals = self.Ins.query(command).rstrip()
                return vals
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

    def shutdown(self):
        """Resets the LCR meter and closes the serial port"""
        self.reset()
        # self.Ins.close()
        logger.critical('The LCR meter has been shutdown and port closed')

class DAQ():
    """
    Driver for the 34970A Data Acquisition / Data Logger Switch Unit

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

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    connect         attempt to connect to the LCR meter
    configure       configures device for measurements
    get_temp        gets temperature from te1,te2 and tref
    get voltage     gets voltage measurement
    read_errors     reads errors stored in the DAQ
    reset           resets the device
    shut_down       shuts down the device
    toggle_switch   switches configuration between temp and voltage
    =============== ===========================================================

    .. note::

        do not change class attributes unless the physical wiring has been changed within the DAQ
    """
    def __init__(self):
        #these attributes must only be changed if the physical wiring has been changed. if required, change values in the config.py file
        self.tref = config.tref
        self.te1 = config.te1
        self.te2 = config.te2
        self.volt = config.volt
        self.switch = config.switch
        self.therm = config.thermistor
        self.address = config.daq_address
        self.temp_integration = config.temp_integration_time
        self.volt_integration = config.volt_integration_time

        self.maxtry = 5
        self.status = False
        self.connect()

    def __str__(self):
        """String representation of the :class:`Drivers.LCR` object."""

        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\nstatus = {}\ntref   = {}\nte1    = {}\nte2    = {}\nvolt   = {}\nswitch = {}\ntherm  = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status,
            self.tref,
            self.te1,
            self.te2,
            self.volt,
            self.switch,
            self.therm
            )

    def connect(self):
        """Connects to the DAQ"""
        try:
            rm = visa.ResourceManager() #used by pyvisa to connect to LCR and DAQ. Leave.
            self.Ins = rm.open_resource(self.address)
        except Exception as e:
            logger.error('    DAQ - FAILED (check log for details)')
            logger.debug(e)
            self.status = False
        else:
            logger.info('    DAQ - CONNECTED!')
            self.status = True

    def configure(self):
        """Configures the DAQ according to the current wiring"""
        print('')
        logger.info('Configuring DAQ...')
        self.reset()
        self._config_temp()
        self._config_volt()
        self.toggle_switch('thermo')

        if self.status: logger.debug('DAQ configured correctly')
        else: logger.info('Could not correctly configure DAQ')

    def get_temp(self):
        """Scans the thermistor and thermocouples for temperature readings

        :returns: [tref,te1,te2]
        :rtype: list of floats (degrees Celsius)
        """
        command = 'ROUT:SCAN (@{},{},{})'.format(self.tref,self.te1,self.te2)
        return self._read(command,'Getting temperature data')

    def get_voltage(self):
        """Gets voltage across the sample from the DAQ

        :returns: voltage
        :rtype: float
        """
        command = 'ROUT:SCAN (@{})'.format(self.volt)
        return self._read(command,'Getting voltage data')

    def get_thermopower(self):
        """Collects both temperature and voltage data and returns a list"""
        thermo = self.get_temp()
        thermo.append(self.get_voltage()[0])
        return thermo

    def reset(self):
        '''Resets the device'''
        self._write('*RST','Resetting DAQ')
        self._write('*CLS','Clearing DAQ')
        self._write('ROUT:CLOS (@203,204,207,208)','Closing channels')

    def toggle_switch(self,command):
        """Opens or closes the switch to the lcr. Must be closed for impedance measurements and open for thermopower measurements.

        :param command: either 'thermo' to make thermopower measurements or 'impedance' for impedance measurements
        :type command: str
        """
        if command is 'thermo': inst_command = 'OPEN'
        elif command is 'impedance': inst_command = 'CLOS'
        else: raise ValueError('Unknown command for DAQ')

        inst_command = 'ROUT:{} (@{})'.format(inst_command,self.switch)
        return self._write(inst_command,'Flipping switch',command)

    def read_errors(self):
        """Reads errors from the DAQ (unsure if working or not)"""
        errors = self.Ins.write('SYST:ERR?')
        logger.error(errors)

    def _config_temp(self):
        """Configures the thermistor ('tref') as 10,000 Ohm
        Configures both electrodes ('te1' and 'te2') as S-type thermocouples
        Sets units to degrees celsius
        """
        #configure thermocouples on channel 104 and 105 to type S
        self._write('CONF:TEMP TC,S,(@{},{})'.format(self.te1,self.te2),'Setting thermocouples','S-type')

        #configure 10,000 ohm thermistor
        self._write('CONF:TEMP THER,{},(@{})'.format(self.therm,self.tref),'Setting thermistor','{} k.Ohm'.format(self.therm/1000))

        #set units to degrees C
        self._write('UNIT:TEMP C,(@{},{},{})'.format(self.tref,self.te1,self.te2),'Setting temperature units','Celsius')

        #set thermocouples to use external reference junction
        self._write('SENS:TEMP:TRAN:TC:RJUN:TYPE EXT,(@{},{})'.format(self.te1,self.te2), 'Setting reference junction','external')

        #sets integration time to 10 cycles. affects measurement resolution
        self._write('SENS:TEMP:NPLC {},(@{},{},{})'.format(self.temp_integration,self.tref,self.te1,self.te2), 'Setting temperature integration time','{} cycle/s'.format(self.temp_integration))

    def _config_volt(self):
        """Configures the voltage measurements"""
        self._write('CONF:VOLT:DC (@{})'.format(self.volt),'Setting voltage','DC')
        self._write('SENS:VOLT:DC:NPLC {},(@{})'.format(self.volt_integration,self.volt),'Setting voltage integration time','{} cycle/s'.format(self.volt_integration))

    def _write(self,command,message,val='\b\b\b  '):
        c=0
        while c <= self.maxtry:
            try:
                logger.debug('\t{} to {}'.format(message,val))
                self.Ins.write(command)         #sets format to ascii
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    self.status = False
                    return False
            else:
                self.status = True
                return True
            c=c+1

    def _read(self,command,message):
        c=0
        while c <= self.maxtry:
            try:
                self.Ins.write(command) #tells the DAQ what to measure
                logger.debug('\t{}...'.format(message))
                return self.Ins.query_ascii_values('READ?') #gets the data
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False



            c=c+1

    def shutdown(self):
        """Shuts down the DAQ"""
        self.reset()
        self.Ins.close()    #close port to the DAQ
        logger.critical('The DAQ has been shutdown and port closed')

class AlicatController(FlowController):
    """
    Driver for an individual Mass Flow Controller.

    .. note::

        not called directly - access is from within :class:'~Drivers.MFC'

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    get_massflow    gets massflow from controller
    set_massflow    sets massflow on controller
    get_pressure    gets pressure from controller
    set_pressure    sets massflow on controller
    get_temp        gets pressure from controller
    get_vol_flow    gets volumetric flow from controller
    get_setpoint    gets current set point from controller
    reset           resets the device
    =============== ===========================================================

    \*see FlowController for more methods
    """
    def __init__(self,port,address):
        super(AlicatController,self).__init__(port,address)

    def get_all(self):
        vals = [(self.massflow)]
        vals.append(self.pressure)
        vals.append(self.temperature)
        vals.append(self.volumetric_flow)
        vals.append(self.setpoint)
        return vals

    def massflow(self,value=None):
        """Get or set the massflow of the appropriate flowmeter

        :param value: desired massflow value
        :type value: float
        """
        self.control_point = 'flow'
        if value: self.set_flow_rate(value)
        else: return self.get()['mass_flow']

    def pressure(self,value=None):
        """Get or set pressure of the appropriate flowmeter

        :param value: desired massflow value
        :type value: float
        """
        self.control_point = 'pressure'
        if value: self.set_gas_pressure(value)
        else: return self.get()['pressure']

    def temperature(self):
        """Gets the temperature of the appropriate flowmeter
        :returns: gas temperature
        :rtype: float
        """
        self.flush()
        return self.get()['temperature']

    def volume_flow(self):
        """Gets the volumetric flow of the appropriate flowmeter"""
        return self.get()['volumetric_flow']

    def setpoint(self):
        """Gets the current set point of the appropriate flowmeter"""
        return self.get()['setpoint']

    def reset(self):
        """
        sets the massflow to 0
        """
        self.set_massflow(0)

class MFC(AlicatController):
    """
    Global driver for the Mass Flow Controllers

    .. note::

        see AlicatController for methods to control individual gases

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry          max number to attempt command
    status          whether the instrument is connected
    co2             controls for the Carbon Dioxide (CO2) controller
    co_a            controls for the coarse Carbon Monoxide (CO) controller
    co_b            controls for the fine Carbon Monoxide (CO) controller
    h2              controls for the Hydrogen (H2) controller
    address         computer port address
    =============== ===========================================================

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    close_all       closes all controllers
    connect         attempt to connect to the LCR meter
    flush_all       flushes data from the input/output buffer of all devices
    fugacity_co     returns a ratio of CO2/CO to achieve desired oxygen fugacity
    fugacity_h2     returns a ratio of H2/CO2 to achieve desired oxugen fugacity
    reset           resets the device
    =============== ===========================================================

    :Example:

    >>> import Drivers
    >>> mfc = Drivers.MFC()
    >>> mfc.co2.get_massflow()
    """
    def __init__(self):
        self.maxtry = 5
        self.status = False
        self.address = config.mfc_address

        self._connect()

    def __str__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\nstatus = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status
            )

    def _connect(self):
        """
        Connects to the mass flow controllers
        """
        try:
            self.co2 = AlicatController(self.address,address='A')
            self.co_a = AlicatController(self.address,address='B')
            self.co_b = AlicatController(self.address,address='C')
            self.h2 = AlicatController(self.address,address='D')
        except Exception as e:
            logger.error('    MFC - FAILED (check log for details)')
            logger.debug(e)
            self.status = False
        else:
            logger.info('    MFC - CONNECTED!')
            self.all = [self.co2,self.co_a,self.co_b,self.h2]
            self.status = True

    def reset(self):
        """Resets all connected flow controllers to 0 massflow"""
        for controller in self.all: controller.set_massflow(0)

    def flush_all(self):
        """Flushes the input? buffer of all flow controllers"""
        for controller in self.all: controller.flush()

    def close_all(self):
        """Closes all flow controllers"""
        for controller in self.all: controller.close()

    # def set_fugacity(self):
    #     """
    #     Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.
    #
    #     :param buffer: buffer type (see table for input options)
    #     :type buffer: str
    #
    #     :param offset: percentage offset from specified buffer
    #     :type offset: float, int
    #
    #     :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
    #     :type pressure: str
    #     """
    #     logger.debug('Recalculating required co2:{:s} mix...'.format(gas_type))
    #     vals = self.daq.get_temp()
    #     temp = np.mean(vals[1:2])
    #     fo2p = self.mfc.fo2_buffer(temp,buffer)
    #
    #     if gas_type == 'h2':
    #         ratio = self.mfc.fugacity_h2(fo2p,temp)
    #         h2 = 10
    #         co2 = round(h2*ratio,2)
    #
    #         logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))
    #         logger.debug('    Setting CO2 to {}'.format(co2))
    #         self.save_data('delete_me',co2,gastype='co2')
    #         # self.mfc.co2.set_massflow()
    #         logger.debug('    Setting H2 to {:.2f}'.format(h2))
    #         self.save_data('delete_me',h2,gastype='h2')
    #         # self.mfc.h2.set_massflow()
    #
    #     elif gas_type == 'co':
    #
    #         ratio = self.mfc.fugacity_co(fo2p,temp)
    #         logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))
    #
    #         co2 = 50    #sets 50 sccm as the optimal co2 flow rate
    #         if co2/ratio >= 20:
    #             co2 = round(20*ratio,2)
    #
    #         co = round(co2/ratio,3)
    #         co_a = int(co2/ratio)
    #         co_b = co - co_a
    #         logger.debug('    Setting CO2 to {}'.format(co2))
    #         # self.mfc.co2.set_massflow(co2)
    #         self.save_data('delete_me',co2,gastype='co2')
    #         logger.debug('    Setting CO_a = {0:.3f}'.format(co_a))
    #         # self.mfc.co_a.set_massflow(co_a)
    #         self.save_data('delete_me',co_a,gastype='co_a')
    #         logger.debug('    Setting CO_b = {0:.3f}'.format(co_b))
    #         # self.mfc.co_b.set_massflow(co_b)
    #         self.save_data('delete_me',co_b,gastype='co_b')
    #     else:
    #         logger.error('Incorrect gas type specified!')

    def fugacity_co(self,fo2p, temp):
        """Calculates the ratio CO2/CO needed to maintain a constant oxygen fugacity at a given temperature.

        :param fo2p: desired oxygen fugacity (log Pa)
        :type fo2p: float, int

        :param temp: temperature (u'\N{DEGREE SIGN}C)
        :type temp: float, int

        :returns: CO2/CO ratio
        :rtype: float
        """

        a10 = 62.110326
        a11 = -2.144446e-2
        a12 = 4.720325e-7
        a13 = -4.5574288e-12
        a14 = -7.3430182e-15

        t0 = 273.18      # conversion C to K
        rgc = .00198726  # gas constant

        tk = temp + t0
        fo2 = 1.01325*(10**(fo2p-5)) # convert Pa to atm

        g1=(((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10;  # Gibbs free energy
        k1=math.exp(-g1/rgc/tk);  # equilibrium constant

        CO = k1 - 3*k1*fo2 - 2*fo2**1.5
        CO2 = 2*k1*fo2 + fo2 + fo2**1.5 + fo2**0.5

        return CO2/CO

    def fugacity_h2(self,fo2p, temp):
        """Calculates the ratio CO2/H2 needed to maintain a constant oxygen fugacity at a given temperature.

        :param fo2p: desired oxygen fugacity (log Pa)
        :type fo2p: float, int

        :param temp: temperature (u'\N{DEGREE SIGN}C)
        :type temp: float, int

        :returns: CO2/H2 ratio
        :rtype: float
        """
        a10 = 62.110326
        a11 = -2.144446e-2
        a12 = 4.720325e-7
        a13 = -4.5574288e-12
        a14 = -7.3430182e-15

        a30 = 55.025254
        a31 = -1.1212207e-2
        a32 = -2.0800406e-6
        a33 = 7.6484887e-10
        a34 = -1.1232833e-13

        t0 = 273.18      # conversion C to K
        rgc = .00198726  # gas constant

        tk = temp + t0
        fo2 = 1.01325*(10**(fo2p-5)) # convert Pa to atm

        g1=(((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10  # Gibbs free energy
        g3=(((a34*temp+a33)*temp+a32)*temp+a31)*temp+a30  # Gibbs free energy
        k1=math.exp(-g1/rgc/tk)  # equilibrium constant
        k3=math.exp(-g3/rgc/tk)  # equilibrium constant

        a = k1/(k1 + fo2**0.5)
        b = fo2**0.5/(k3 + fo2**0.5)

        H2 = a*(1-fo2) - 2*fo2
        CO2 = b*(1-fo2) + 2*fo2

        return CO2/H2

    def fo2_buffer(self,temp,buffer,pressure=1.01325):
        """
        Calculates oxygen fugacity at a given temperature and fo2 buffer

        =============== ===========================================================
        input options   type of fo2 buffer
        =============== ===========================================================
        'QFM'           quartz-fayalite-magnetite
        'IW'            iron-wustite
        'WM'            wustite-magnetite
        'MH'            magnetite-hematite
        'QIF'           quartz-iron-fayalite
        'NNO'           nickel-nickel oxide
        'MMO'           molyb
        'CCO'           cobalt-cobalt oxide
        =============== ===========================================================

        :param temp: Temperature in u'\N{DEGREE SIGN}C'
        :type temp: float, int

        :param buffer: buffer type (see table for input options)
        :type buffer: str

        :param pressure: pressure in bar (default: surface pressure)
        :type pressure: float, int

        :returns: log10 oxygen fugacity
        :rtype: float
        """

        def fug(a,temp,pressure):
            if len(a) is 2:
                fo2  =  10**(a[0]/temp + a[1])
            elif len(a) is 3:
                fo2  =  10**(a[0]/temp + a[1] + a[2]*(pressure - 1e5)/temp)
            return fo2

        # if isinstance(buffer,str):
        #     buffer = buffer.lower()
        # else:
        #     np.char.lower(buffer)

        Tc = 10000

        temp = temp+273 #convert Celsius to Kelvin

        #Many of these empirical relationships are determined fo2 in atm.
        #These relationships have been converted to Pa.
        if buffer == 'iw': # Iron-Wuestite
            # Myers and Eugster (1983)
            # a[1] = [-26834.7 11.477 5.2e-7]        # 833 to 1653 K
            # a[3] pressure term from Dai et al. (2008)
            # a = [-2.7215e4 11.57 5.2e-7] - O'Neill (1988)
            a1 = [-27538.2, 11.753]
        elif buffer in ['qfm','fmq','fqm']: # Fayalite-Quartz-Magnetite
            # Myers and Eugster (1983)
            a1 = [-27271.3, 16.636]        # 298 to 848 K
            a2 = [-24441.9, 13.296]        # 848 to 1413 K
            Tc = 848 # K

        elif buffer == 'wm': # Wuestite-Magnetite
            # # Myers and Eugster (1983)
            # a[1] = [-36951.3 21.098]        # 1273 to 1573 K
            # O'Neill (1988)
            a1 = [-32356.6, 17.560]
        elif buffer == 'mh': # Magnetite-Hematite
            # Myers and Eugster (1983)
            a1 = [-25839.1, 20.581]        # 298 to 950 K
            a2 = [-23847.6, 18.486]        # 943 to 1573 K
            Tc = 943 # K
        elif buffer == 'qif': # Quartz-Iron-Fayalite
            # Myers and Eugster (1983)
            a1 = [-30146.6, 14.501]        # 298 to 848 K
            a2 = [-27517.5, 11.402]        # 848 to 1413 K
            Tc = 848 # K
        elif buffer == 'osi': # Olivine-Quartz-Iron
            # Nitsan (1974)
            Xfa = 0.10
            gamma = (1 - Xfa)**2*((1 - 1690/temp)*Xfa - 0.24 + 730/temp)
            afa = gamma*Xfa
            fo2 = 10**(-26524/temp + 5.54 + 2*math.log10(afa) + 5.006)
            return fo2
        elif buffer == 'oqm': # Olivine-Quartz-Magnetite
            # Nitsan (1974)
            Xfa = 0.10
            Xmt = 0.01
            gamma = (1 - Xfa)**2*((1 - 1690/temp)*Xfa - 0.24 + 730/temp)
            afa = gamma*Xfa
            fo2 = 10**(-25738/temp + 9 - 6*math.log10(afa) + 2*math.log10(Xmt) + 5.006)
            return fo2
        elif buffer == 'nno': # Ni-NiO
            #a = [-24930 14.37] # Huebner and Sato (1970)
            #a = [-24920 14.352] # Myers and Gunter (1979)
            a1 = [-24920, 14.352, 4.6e-7]
            # a[3] from Dai et al. (2008)
        elif buffer == 'mmo': # Mo-MoO2
            a1 = [-30650, 13.92, 5.4e-7]
            # a[3] from Dai et al. (2008)
        elif buffer == 'cco': # Co-CoO
            # Myers and Gunter (1979)
            a1 = [-25070, 12.942]
        elif buffer == 'g': # Graphite, CO-CO2
            # French & Eugster (1965)
            fo2 = 10**(-20586/temp - 0.044 + math.log10(pressure) - 2.8e-7*(pressure - 1e5)/temp)
            return
        elif buffer == 'fsqm': # Ferrosilite-Quartz-Magnetite
            # Seifert (1982)
            # Kuestner (1979)
            a1 = [-25865, 14.1456]
        elif buffer == 'fsqi': # Ferrosilite-Quartz-Iron
            # Seifert et al. (1982)
            # Kuestner 1979
            a1 = [-29123, 12.4161]
        else:
            raise ValueError('(fugacityO2): Unknown buffer.')

        if temp < Tc:
            fo2 = fug(a1,temp,pressure)
        else:
            fo2 = fug(a2,temp,pressure)

        return math.log10(fo2)

class Furnace():
    #minimalmodbus.Instrument - copy this into Furnace class if using Super()
    """
    Driver for the Eurotherm 3216 Temperature Controller

    .. note::
       units are in °C

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry           max number to attempt command
    default_temp     revert to this temperature when resetting
    status           whether the instrument is connected
    address         computer port address
    =============== ===========================================================

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    connect          attempt to connect to the LCR meter
    set_temp         set temperature of furnace
    get_temp         get temperature from furnace
    set_heatrate     set heatrate of furnace
    get_heatrate     get heatrate from furnace
    set_other        set another parameter on furnace
    get_other        get another parameter from furnace
    reset            resets the device
    =============== ===========================================================
    """

    def __init__(self,ports=None):

        self.address = config.furnace_address
        self.maxtry = 10
        self.default_temp = config.default_temp
        self.status = False

        self._connect(ports)

    def __str__(self):
        """String representation of the :class:`Drivers.Furnace` object."""
        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\nstatus = {}\ndefault_temp = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status,
            self.default_temp,
            )

    def _connect(self,ports):
        """
        Attempts connection to the furnace through each port in ports. Stops searching when connection is successful

        :param ports: names of available serial ports
        :type ports: list
        """
        if not ports: ports = self.address

        if not isinstance(ports,list): ports = [ports]

        logger.debug('Attempting to connect to the furnace...')
        for port in ports:  #loop through available ports
            if self.status:      #stop search if device is already found
                break
            c=0
            while c <= self.maxtry:
                try:
                    logger.debug('    Trying {}...'.format(port))
                    self.Ins = minimalmodbus.Instrument(port,1)
                    tmp = self.Ins.read_register(107) #try connect to furnace
                    if tmp == 531:
                        logger.info('    FUR - CONNECTED!')
                        self.status = True
                        break
                except Exception as e:
                    if c >= self.maxtry:
                        logger.debug('    Error: {}'.format(e))
                c=c+1

        if not self.status:
            logger.error('    FUR - FAILED (check log for details)')

    def configure(self):
        self.setpoint_2(config.default_temp)
        self.timer_status('dwell')
        self.timer_end_type('alternate')

    def indicated(self,address=1):
        '''Query current temperature of furnace.
        Modbus address - 1

        :returns: Temperature in °C if succesful, else False
        :rtype: float/boolean
        '''
        return self._read(address,'Getting temperature')

    def heating_rate(self,heat_rate=None,address=35):
        """Sets the desired heating rate of furnace.
        Modbus address - 35

        :param heat_rate: heating rate in °C/min
        :type heat_rate: float, int

        :returns: True if succesful, False if not
        :rtype: Boolean
        """
        if heat_rate: return self._write(address,heat_rate,'Setting heating rate',decimals=1)
        else: return self._read(address,'Getting heating rate',decimals=1)

    def setpoint_1(self,temperature=None,address=24):
        """Sets target temperature of furnace.
        Modbus address - 24

        :param temp: temperature in °C
        :type temp: float, int

        :returns: True if succesful, False if not
        :rtype: Boolean
        """
        if temperature: return self._write(address,temperature,'Setting target temperature')
        else: return self._read(address,'Getting target temperature')

    def setpoint_2(self,temperature=None,address=25):
        """Sets target temperature of furnace.
        Modbus address - 24

        :param temp: temperature in °C
        :type temp: float, int

        :returns: True if succesful, False if not
        :rtype: Boolean
        """
        if temperature: return self._write(address,temperature,'Setting target temperature')
        else: return self._read(address,'Getting target temperature')

    def timer_status(self,status=None,address=23):
        status_options = {'reset':0,'run':1,'hold':2,'end':3}
        if status:
            if status in status_options:
                return self._write(address,status_options[status],'Setting timer status')
            else:
                logger.info('Incorrect argument for variable "status"')
        else:
            status = self._read(address,'Getting timer status')
            for key,value in status_options.items():
                if value == status: return key

    def timer_type(self,input=None,address=320):
        type_options = {'off':0,'dwell':1,'delay':2,'soft start':3}
        if input:
            if input in type_options:
                return self._write(address,type_options[type],'Setting timer type')
            else:
                output = self._read(address,'Getting timer type')
                for key,value in type_options.items():
                    if value == output: return key

    def timer_end_type(self,input=None,address=328):
        type_options = {'off':0,'current':1,'alternate':2}
        if input:
            if input in type_options:
                return self._write(address,type_options[type],'Setting timer end type')
            else:
                logger.info('Incorrect argument for variable "type"')
        else:
            output = self._read(address,'Getting timer end type')
            for key,value in type_options.items():
                if value == output: return key

    def timer_resolution(self,val=None,address=320):
        if val: return self._write(address,val,'Setting timer resolution')
        else: return self._read(address,'Getting timer resolution')

    def other(self,address,value=None):
        '''set value at specified modbus address.

        :param modbus_address: see furnace manual for adresses
        :type modbus_address: float, int

        :param val: value to be sent to the furnace
        :type val: float, int

        :returns: True if succesful, False if not
        :rtype: Boolean
        '''
        if value: return self._write(address,val,'Setting address {}'.format(address))
        else: self._read(address,'Getting address {}'.format(address))

    def settings(self):
        return self.Ins.serial.get_settings()

    def flush_input(self):
        logger.debug('Flushing furnace input')
        self.Ins.serial.reset_input_buffer()

    def flush_output(self):
        logger.debug('Flushing furnace output')
        self.Ins.serial.reset_output_buffer()





    def _write(self,modbus_address,val,message,decimals=0):

        c=0
        while c <= self.maxtry:
            try:
                logger.debug('\t{} to {}'.format(message,val))
                self.Ins.write_register(modbus_address,val,numberOfDecimals=decimals)
                return True
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            # self.flush_output()
            # self.flush_input()
            time.sleep(0.1)
            c=c+1

    def _read(self,modbus_address,message,decimals=0):

        c=0
        while c <= self.maxtry:
            try:
                logger.debug('\t{}...'.format(message))
                return self.Ins.read_register(modbus_address,numberOfDecimals=decimals)
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\t"{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            # self.flush_output()
            # self.flush_input()
            time.sleep(0.1)
            c=c+1

    def reset(self):
        '''
        resets the furnace to default temperature
        '''
        self._write(24,self.default_temp,'Furnace reset to {}'.format(default_temp))
        self.flush_input()
        self.flush_output()

class Motor():
    """
    Driver for the motor controlling the linear stage

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry          max number to attempt command
    status          whether the instrument is connected
    home            approximate xpos where te1 == te2
    max_xpos        maximum x-position of the stage
    address         computer port address
    =============== ===========================================================

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    home            move to the center of the stage
    connect         attempt to connect to the LCR meter
    move            moves the stage the desired amount in mm
    get_xpos        get the absolute position of the stage
    set_xpos        moves the stage the desired amount in steps
    get_speed       get the current speed of the stage
    set_speed       sets the movement speed of the stage
    reset           resets the device
    test            sends stage on a test run
    =============== ===========================================================
    """

    def __init__(self,ports=None):
        self.maxtry = 5
        self.status = False
        self.home = 4800
        self.address = config.motor_address
        self.pulse_equiv = config.pitch * config.step_angle / (360*config.subdivision)
        self.max_xpos = config.max_xpos

        self._connect(ports)

    def __str__(self):
        """String representation of the :class:`Drivers.Motor` object."""
        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\n{}\nstatus = {}\nhome = {}\nmax_xpos = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status,
            self.home,
            self.max_xpos
            )

    def _connect(self,ports):
        """
        attempts connection to the motor

        :param ports: list of available ports
        :type ports: list, string
        """
        if not ports: ports = self.address

        if not isinstance(ports,list):
            ports = [ports]
        command = '?R'

        logger.debug('Attempting to connect to the motor...')
        for port in ports:
            if self.status:      #stop searching if the instrument has already been found
                break
            c=0
            while c <= self.maxtry:
                try:
                    logger.debug('    Trying {}...'.format(port))
                    rm = visa.ResourceManager()
                    self.Ins = rm.open_resource(port)
                    tmp = self.Ins.query_ascii_values(command,converter='s')
                except Exception as e:
                    if c >= self.maxtry:
                        logger.debug('    Trying {}... unsuccessful'.format(port))
                        logger.debug('    {}'.format(e))
                else:
                    if tmp[0] == '?R\rOK\n':
                        self.status = True
                        logger.info('    MOT - CONNECTED!')
                        break
                c=c+1
        if not self.status:
            logger.error('    MOT - FAILED (check log for details)')

    def center(self):
        """Moves stage to the absolute center"""
        return self.set_xpos(self.max_xpos/2)

    def move(self,displacement):
        """Moves the stage in the positive or negative direction

        :param displacement: positive or negative displacement [in mm]
        :type displacement: float, int
        """
        command = self._convertdisplacement(displacement)
        return self._write(command,'Moving stage {}mm'.format(displacement))

    def set_xpos(self,xpos):
        """Moves the linear stage to an absolute x position

        :param xpos: desired absolute position of stage in controller pulses
        :type xpos: float, int
        """
        if xpos > self.max_xpos: xpos = self.max_xpos
        elif xpos <= 0: return self.reset()

        displacement = (self.get_xpos() - xpos)
        if displacement == 0: return True

        direction = '-' if displacement > 0 else '+'
        command = 'X{}{}'.format(direction,int(abs(displacement)))  #format to readable string
        return self._write(command,'Setting x-position'.format(xpos))

    def set_speed(self,motor_speed):
        """Sets the speed of the motor

        :param motor_speed: speed of the motor in mm/s
        :type motor_speed: float, int
        """
        command = self._convertspeed(motor_speed)
        return self._write(command,'Setting motor speed')

    def get_speed(self):
        """Gets the current speed of the motor

        :returns: speed of motor
        :rtype: float
        """
        command = '?V'
        speed = self._read(command,'Getting motor speed...')
        speed = self._convertspeed(speed,False) #needs to be converted to mm/s
        return speed

    def get_xpos(self):
        """Gets the current position of the stage

        :returns: x-position of stage
        :rtype: str
        """
        return self._read('?X','Getting x-position')

    def home(self):
        """Moves furnace to the center of the stage (x = 5000)
        """
        return self.set_xpos(self.home)

    def reset(self):
        """Resets the stage position so that xPos=0"""
        return self._write('HX0','Resetting stage...')

    def test(self):
        """Sends the motorised stage on a test run to ensure everything is working
        """

        self.set_speed(10)
        self.reset()
        self.move(30)
        self.set_speed(6)
        self.move(-20)
        self.set_speed(3)
        self.move(10)
        self.set_speed(10)
        self.move(10)
        self.reset()

    def _convertdisplacement(self,displacement):
        """Converts a positive or negative displacement (in mm) into a command recognisable by the motor"""

        direction = '+' if displacement > 0 else '-'
        magnitude =  str(int(abs(displacement)/self.pulse_equiv))   #convert from mm to steps for motioncontroller
        return 'X'+direction+magnitude #command for motion controller

    def _convertspeed(self,speed,default=True):
        """Converts a speed given in mm/s into a command recognisable by the motor"""
        if default:
            Vspeed = (speed*0.03/self.pulseEquiv)-1        #convert from mm/s to Vspeed
            return 'V' + str(int(round(Vspeed)))        #command for motion controller
        else:
            return round((speed+1)*self.pulseEquiv/0.03,2)   #output speed

    def _write(self,command,message):
        c=0
        while c <= self.maxtry:
            try:
                self.Ins.clear()
                tmp = self.Ins.query_ascii_values(command,converter='s')
                if 'OK' in tmp[0]:
                    logger.debug('\t{}...'.format(message))
                    return True
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

    def _read(self,command,message):
        c=0
        while c <= self.maxtry:
            try:
                self.Ins.clear()
                tmp = self.Ins.query_ascii_values(command,converter='s')
                if not 'ERR' in tmp[0]:
                    logger.debug('\t{}...'.format(message))
                    return int(''.join(x for x in tmp[0] if x.isdigit()))
            except Exception as e:
                if c >= self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

if __name__ == '__main__':
    mfc = MFC()
    print(mfc.fo2_buffer(800,'iw'))
