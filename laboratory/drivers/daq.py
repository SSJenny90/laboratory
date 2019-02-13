from laboratory.utils import loggers
from laboratory import config
import visa
logger = loggers.lab(__name__)



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
