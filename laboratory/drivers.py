from laboratory.utils import loggers
from laboratory.utils.exceptions import InstrumentError,InstrumentConnectionError, InstrumentCommunicationError
logger = loggers.lab(__name__)
from laboratory import config
import visa
import pprint
import minimalmodbus
minimalmodbus.BAUDRATE = 9600
minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = True
pp = pprint.PrettyPrinter(width=1,indent=4)
from alicat import FlowMeter
import math

class USBSerialInstrument():
    """Base class for instruments that connect via USB"""

    def __init__(self, port):
        try:
            self.device = visa.ResourceManager().open_resource(port)
        except visa.VisaIOError as e:
            self.status = False
            logger.error(InstrumentConnectionError('Could not connect to the {}!'.format(self.__class__.__name__)))
            logger.debug(e)
        else:
            logger.info('{} connected at {}'.format(self.__class__.__name__, port))
            self.status = True

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key,val in self.__dict__.items()])

    def read(self,command,message='',to_file=True):
        for i in range(1,config.GLOBAL_MAXTRY):
            try:
                if message:
                    logger.debug('\t{}...'.format(message))
                return self.device.query_ascii_values(command)
            except Exception as e:
                if i >= config.GLOBAL_MAXTRY:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False

    def write(self,command,message='',val='\b\b\b  ',to_file=True):
        for i in range(1,config.GLOBAL_MAXTRY):
            try:
                if message:
                    logger.debug('\t{} to {}'.format(message,val))
                self.device.write(command)         #sets format to ascii
                return True
            except Exception as e:
                if i >= config.GLOBAL_MAXTRY:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False

    def read_string(self,command,message,to_file=True):
        for i in range(1,config.GLOBAL_MAXTRY):
            try:
                if to_file: logger.debug('\t{}...'.format(message))
                return self.device.query(command).rstrip()
            except Exception as e:
                if i >= config.GLOBAL_MAXTRY:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False

    def reset(self):
        """Resets the LCR meter"""
        return self.write('*RST;*CLS','Resetting device')

class LCR(USBSerialInstrument):
    """Driver for the E4980A Precision LCR Meter, 20 Hz to 2 MHz

        =============== ===========================================================
        Attribute       Description
        =============== ===========================================================
        status          whether the instrument is connected
        device          port name
        =============== ===========================================================

        =============== ===========================================================
        Method          Description
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
        self.address = config.LCR_ADDRESS
        super().__init__(port=self.address)

    def get_complex_impedance(self):
        """Collects complex impedance from the LCR meter"""
        self.trigger()
        line = self.read('FETCh?','Collecting impedance data',to_file=False)
        return {key: float('nan') if value == 9.9e+37 else value for key,value in zip(['z','theta'],line)}

    def configure(self,freq):
        """Appropriately configures the LCR meter for measurements"""
        logger.debug('Configuring LCR meter...')
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
        return self.write('TRIG:IMM','Trigger next measurement',to_file=False)

    def write_freq(self,freq):
        """Writes the desired frequencies to the LCR meter

        :param freq: array of frequencies
        :type freq: array like
        """
        freq_str = ','.join('{}'.format(n) for n in freq)
        return self.write(':LIST:FREQ ' + freq_str,'Loading frequencies')

    def _set_format(self,mode='ascii'):
        """Sets the format type of the LCR meter. Defaults to ascii. TODO - allow for other format types"""
        return self.write('FORM:ASC:LONG ON',"Setting format",mode)

    def function(self,mode='impedance'):
        """Sets up the LCR meter for complex impedance measurements"""
        return self.write('FUNC:IMP ZTR',"Setting measurement type",mode)

    def _set_continuous(self,mode='ON'):
        """Allows the LCR meter to auto change state from idle to 'wait for trigger'"""
        return self.write('INIT:CONT ON','Setting continuous',mode)

    def list_mode(self,mode=None):
        """Instructs LCR meter to take a single measurement per trigger"""
        # return self.write('LIST:MODE STEP',"Setting measurement",mode)
        mode_options = {'step':'STEP','sequence':'SEQ'}
        if mode:
            if mode in mode_options:
                return self.write('LIST:MODE {}'.format(mode_options[mode]),'Setting list mode',mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self.read_string('LIST:MODE?','Getting list mode')
            for key,value in mode_options.items():
                if value == mode: return key

    def display(self,mode=None):
        """Sets the LCR meter to display frequencies as a list"""
        mode_options = {'measurement':'MEAS','list':'LIST'}
        if mode:
            if mode in mode_options:
                return self.write('DISP:PAGE {}'.format(mode_options[mode]),'Setting page display',mode)
            else:
                logger.info('Unsupported argument for variable "mode"')
        else:
            mode = self.read_string('DISP:PAGE?','Getting page display')
            for key,value in mode_options.items():
                if value == mode: return key

    def _set_source(self,mode='remote'):
        """Sets up the LCR meter to expect a trigger from a remote source"""
        return self.write('TRIG:SOUR BUS','Setting trigger',mode)

    def shutdown(self):
        """Resets the LCR meter and closes the serial port"""
        self.reset()
        logger.critical('The LCR meter has been shutdown and port closed')
            
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
    #these attributes must only be changed if the physical wiring has been changed. if required, change values in the config.py file
    tref = config.REFERENCE_TEMPERATURE
    te1 = config.ELECTRODE_1
    te2 = config.ELECTRODE_2
    volt = config.VOLTAGE
    switch = config.SWITCH

    def __init__(self):
        self.address = config.DAQ_ADDRESS
        super().__init__(port=self.address)

    def configure(self):
        """Configures the DAQ according to the current wiring"""
        # print('')
        logger.debug('Configuring DAQ...')
        self.reset()
        self._config_temp()
        self._config_volt()
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
        command = 'ROUT:SCAN (@{},{},{})'.format(self.tref,self.te1,self.te2)
        self.write(command)
        vals = self.read('READ?','Getting temperature data')
        self.mean_temp = (vals[1]+vals[2])/2
        return {'reference':vals[0],'thermo_1':vals[1],'thermo_2':vals[2]}

    def get_voltage(self):
        """Gets voltage across the sample from the DAQ

        :returns: voltage
        :rtype: float
        """
        self.write('ROUT:SCAN (@{})'.format(self.volt))
        return {'voltage': self.read('READ?','Getting voltage data')[0]}

    def get_thermopower(self):
        """Collects both temperature and voltage data and returns a list"""
        return {**self.get_temp(), **self.get_voltage()}

    def toggle_switch(self,command):
        """Opens or closes the switch to the lcr. Must be closed for impedance measurements and open for thermopower measurements.

        :param command: either 'thermo' to make thermopower measurements or 'impedance' for impedance measurements
        :type command: str
        """
        if command is 'thermo': inst_command = 'OPEN'
        elif command is 'impedance': inst_command = 'CLOS'
        else: raise ValueError('Unknown command for DAQ')

        inst_command = 'ROUT:{} (@{})'.format(inst_command,self.switch)
        return self.write(inst_command,'Flipping switch',command)

    def has_errors(self):
        """Reads errors from the DAQ (unsure if working or not)"""
        errors = self.write('SYST:ERR?')
        logger.error(errors)

    def _config_temp(self):
        """Configures the thermistor ('tref') as 10,000 Ohm
        Configures both electrodes ('te1' and 'te2') as S-type thermocouples
        Sets units to degrees celsius
        """
        #configure thermocouples on channel 104 and 105 to type S
        self.write('CONF:TEMP TC,S,(@{},{})'.format(self.te1,self.te2),'Setting thermocouples','S-type')

        #configure 10,000 ohm thermistor
        self.write('CONF:TEMP THER,{},(@{})'.format(config.THERMISTOR_OHMS,self.tref),'Setting thermistor','{} k.Ohm'.format(config.THERMISTOR_OHMS/1000))

        #set units to degrees C
        self.write('UNIT:TEMP C,(@{},{},{})'.format(self.tref,self.te1,self.te2),'Setting temperature units','Celsius')

        #set thermocouples to use external reference junction
        self.write('SENS:TEMP:TRAN:TC:RJUN:TYPE EXT,(@{},{})'.format(self.te1,self.te2), 'Setting reference junction','external')

        #sets integration time to 10 cycles. affects measurement resolution
        self.write('SENS:TEMP:NPLC {},(@{},{},{})'.format(config.TEMPERATURE_INTEGRATION_TIME,self.tref,self.te1,self.te2), 'Setting temperature integration time','{} cycle/s'.format(config.TEMPERATURE_INTEGRATION_TIME))

    def _config_volt(self):
        """Configures the voltage measurements"""
        self.write('CONF:VOLT:DC (@{})'.format(self.volt),'Setting voltage','DC')
        self.write('SENS:VOLT:DC:NPLC {},(@{})'.format(config.VOLTAGE_INTEGRATION_TIME,self.volt),'Setting voltage integration time','{} cycle/s'.format(config.VOLTAGE_INTEGRATION_TIME))

    def shutdown(self):
        """Shuts down the DAQ"""
        self.reset()
        self.device.close()    #close port to the DAQ
        logger.critical('The DAQ has been shutdown and port closed')

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
    
    default_temp = config.RESET_TEMPERATURE
    def __init__(self):
        self.port = config.FURNACE_ADDRESS
        try:
            super().__init__(self.port,1)
        except Exception as e:
            logger.error(InstrumentConnectionError('Could not connect to the {}!'.format(self.__class__.__name__)))
            logger.debug(e)
        else:
            logger.info('{} connected at {}'.format(self.__class__.__name__, self.port))
            self.status = True

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key,val in self.__dict__.items()])

    def configure(self):
        """Configures the furnace based on settings specified in the configuration file"""
        logger.debug('Configuring furnace...')
        self.setpoint_2()
        self.setpoint_select('setpoint_1')
        self.display(2)
        self.timer_type('dwell')
        self.timer_end_type('transfer')
        self.timer_resolution('M:S')
        self.timer_status('reset')

    def display(self,display_type=0,address=106):
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
        display_options = [0,1,2,3,4,5,6,7]
        if display_type in display_options:
            return self._write(address,display_type,'Setting display type')
        else:
            logger.info('Incorrect argument for variable "display_type". Must be one of {}'.format(display_options))

    def heating_rate(self,heat_rate=None,address=35,decimals=1):
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
        return self._command(heat_rate,address,'heating rate',decimals=decimals)
        # if heat_rate: return self._write(address,heat_rate,'Setting heating rate',decimals=1)
        # else: return self._read(address,'Getting heating rate',decimals=1)

    def indicated(self,address=1):
        """[Query only] Queries the current temperature of furnace.

        :returns: Temperature in °C if succesful, else False
        """
        return {'indicated':self._read(address,'Getting temperature')}

    def reset_timer(self):
        """Resets the current timer and immediately restarts. Used in for loops to reset the timer during every iteration. This is a safety measure should the program lose communication with the furnace.
        """
        if self.timer_status('reset'):
            return self.timer_status('run')
        else:
            return False

    def setpoint_1(self,temperature=None,address=24):
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
        return self._command(temperature,address,'setpoint 1')
        # if temperature: return self._write(address,temperature,'Setting SP1')
        # else: return self._read(address,'Getting SP1 temperature')

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

        if temperature:
            return self._write(self.default_temp,address,'setpoint 2')
        else:
            return self._read(address,'Getting SP2 temperature')

    def setpoint_select(self,selection=None,address=15):
        """If selection is specified, selects the current working setpoint. If no argument is passed, it returns the current working setpoint.

        options:
            'setpoint_1'
            'setpoint_2'

        :param selection: desired working setpoint
        :type selection: str

        """
        return self._command(selection,address,'current setpoint',{'setpoint_1':0,'setpoint_2':1})

    def timer_duration(self,minutes=0,seconds=0,address=324):
        """Sets the length of the timer.

        :param minutes: number of minutes
        :type timer_type: int,float

        :param seconds: number of seconds
        :type timer_type: int,float (floats internally converted to int)
        """
        total_seconds = minutes*60+int(seconds)
        if total_seconds > 99*60+59:
            logger.info("Can't set timer to more than 100 minutes at the current resolution")
            return False
        else:
            return self._command(total_seconds,address,'timer duration')

    def timer_end_type(self,selection=None,address=328):
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
        return self._command(selection,address,'timer end type',{'off':0,'current':1,'transfer':2})

    def timer_resolution(self,selection=None,address=320):
        """Determines whether the timer display is in Hours:Mins or Mins:Seconds

        options:
            'H:M'   : Hours:Minutes
            'M:S'   : Minutes:Seconds

        :param selection: desired configuration
        :type selection: str
        """
        return self._command(selection,address,'timer resolution',{'H:M':0,'M:S':1})

    def timer_status(self,status=None,address=23):
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
        #TODO fix this ^^^^

        if status == 'end':
            raise ValueError('"end" is not a valid option for controlling the timer. Please refer to the furnace documentation.')
        return self._command(status,address,'timer status',{'reset':0,'run':1,'hold':2})

    def timer_type(self,selection=None,address=320):
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
        return self._command(selection,address,'timer type',{'off':0,'dwell':1,'delay':2,'soft_start':3})

    def other(self,address,value=None):
        '''Set value at specified modbus address.

        :param modbus_address: see furnace manual for adresses
        :type modbus_address: float, int

        :param val: value to be sent to the furnace
        :type val: float, int

        :returns: True if succesful, False if not
        :rtype: Boolean
        '''
        if value is not None:
            return self._write(address,value,'Setting address {}'.format(address))
        else:
            return self._read(address,'Getting address {}'.format(address))

    def flush_input(self):
        logger.debug('Flushing furnace input')
        self.serial.reset_input_buffer()

    def flush_output(self):
        logger.debug('Flushing furnace output')
        self.serial.reset_output_buffer()

    def shutdown(self):
        self.setpoint_1(40)
        self.timer_status('reset')

    def _command(self,value,address,message,options=None,decimals=0):
        if value:
            if options is None:
                return self._write(address,value,'Setting {}'.format(message),decimals=decimals)
            elif value in options:
                return self._write(address,options[value],'Setting {}'.format(message))
            else:
                logger.info('Incorrect argument. Must be one of {}'.format([key for key in options.keys()]))
        else:
            output = self._read(address,'Getting {}'.format(message),decimals=decimals)
            if options is None:
                return output
            else:
                for key, value in options.items():
                    if value == output:
                        return key

    def _write(self,modbus_address,value,message,decimals=0):

        for i in range(0,config.GLOBAL_MAXTRY):
            try:
                logger.debug('\t{} to {}'.format(message,value))
                self.write_register(modbus_address,value,numberOfDecimals=decimals)
                return True
            except Exception as e:
                if i == config.GLOBAL_MAXTRY-1:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))

    def _read(self,modbus_address,message,decimals=0):
        for i in range(0,config.GLOBAL_MAXTRY):
            try:
                logger.debug('\t{}...'.format(message))
                return self.read_register(modbus_address,numberOfDecimals=decimals)
            except Exception as e:
                if i == config.GLOBAL_MAXTRY-1:
                    logger.error('\t"{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    logger.error(InstrumentError(e))

class Motor():
    """Driver for the motor controlling the linear stage

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
    position        moves the stage the desired amount in steps
    get_speed       get the current speed of the stage
    set_speed       sets the movement speed of the stage
    reset           resets the device
    test            sends stage on a test run
    =============== ===========================================================
    """

    def __init__(self,ports=None):
        self.home = config.EQUILIBRIUM_POSITION
        self.port = config.MOTOR_ADDRESS
        self.pulse_equiv = config.PITCH * config.STEP_ANGLE / (360*config.SUBDIVISION)
        self.max_xpos = config.MAXIMUM_STAGE_POSITION

        self._connect(ports)

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key,val in self.__dict__.items()])

    def _connect(self,ports):
        """
        attempts connection to the motor

        :param ports: list of available ports
        :type ports: list, string
        """
        if not ports: 
            ports = self.port

        if not isinstance(ports,list):
            ports = [ports]

        rm = visa.ResourceManager()
        for port in ports:
            logger.debug('Searching for motor at {}...'.format(port))
                   
            for i in range(0,config.GLOBAL_MAXTRY):
                try:
                    self.Ins = rm.open_resource(port)
                    if not self.is_connected():
                        raise InstrumentConnectionError('Not at port {}'.format(port))
                except Exception as e:
                    if i == config.GLOBAL_MAXTRY-1:
                        logger.debug('{} {}'.format(e,port))
                        logger.info('{} {}'.format(e,port))
                        self.status = False
                else:
                    logger.info('{} connected at {}'.format(self.__class__.__name__,port))
                    self.status = True
                    return

    def is_connected(self):
        if self.Ins.query_ascii_values('?R',converter='s')[0] == '?R\rOK\n':
            return True 

    def center(self):
        """Moves stage to the absolute center"""
        return self.position(self.max_xpos/2)

    def get_settings(self):
        output = {'baudrate':self.Ins.baud_rate,
                  'bytesize':self.Ins.data_bits,
                  'parity':self.Ins.parity._name_,
                  'stopbits':int(self.Ins.stop_bits._value_/10),
                  'timeout':self.Ins.timeout,}
        return output

    def move(self,displacement):
        """Moves the stage in the positive or negative direction

        :param displacement: positive or negative displacement [in mm]
        :type displacement: float, int
        """
        command = self._convertdisplacement(displacement)
        return self._write(command,'Moving stage {}mm'.format(displacement))

    def position(self,requested_position=None):
        """Get or set the absolute position of the linear stage

        :param requested_position: requested absolute position of stage in controller pulse units
        :type requested_position: float, int
        """
        #this is a get request
        if requested_position is None:
            return self._read('?X','Getting x-position')
        #this is a set request
        else:
            current_position = self._read('?X','Getting x-position')
            if requested_position > self.max_xpos:
                requested_position = self.max_xpos
            elif requested_position <= 0:
                return self.reset()

            displacement = (current_position - requested_position)
            if displacement == 0:
                return True

            direction = '-' if displacement > 0 else '+'
            command = 'X{}{}'.format(direction,int(abs(displacement)))  #format to readable string
            return self._write(command,'Setting x-position'.format())

    def speed(self,motor_speed=None):
        """Get or set the speed of the motor

        :param motor_speed: speed of the motor in mm/s
        :type motor_speed: float, int
        """
        #this is a get request
        if motor_speed is None:
            speed = self._read('?V','Getting motor speed...')
            return self._convertspeed(speed,False) #needs to be converted to mm/s
        #this is a set request
        else:
            command = self._convertspeed(motor_speed)
            return self._write(command,'Setting motor speed')

    def return_home(self):
        """Moves furnace to the center of the stage (x = 5000)
        """
        return self.position(self.home)

    def reset(self):
        """Resets the stage position so that the absolute position = 0"""
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
            Vspeed = (speed*0.03/self.pulse_equiv)-1        #convert from mm/s to Vspeed
            return 'V' + str(int(round(Vspeed)))        #command for motion controller
        else:
            return round((speed+1)*self.pulse_equiv/0.03,2)   #output speed

    def _write(self,command,message):
        c=0
        while c <= config.GLOBAL_MAXTRY:
            try:
                self.Ins.clear()
                tmp = self.Ins.query_ascii_values(command,converter='s')
                if 'OK' in tmp[0]:
                    logger.debug('\t{}...'.format(message))
                    return True
            except Exception as e:
                if c >= config.GLOBAL_MAXTRY:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

    def _read(self,command,message):
        c=0
        while c <= config.GLOBAL_MAXTRY:
            try:
                self.Ins.clear()
                tmp = self.Ins.query_ascii_values(command,converter='s')
                if not 'ERR' in tmp[0]:
                    logger.debug('\t{}...'.format(message))
                    return int(''.join(x for x in tmp[0] if x.isdigit()))
            except Exception as e:
                if c >= config.GLOBAL_MAXTRY:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
            c=c+1

class AlicatController(FlowMeter):
    """Driver for an individual Mass Flow Controller.

        .. note::

            no need to instantiate directly - access is from within :class:'~Drivers.MFC'

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

        :Example:

        >>> from laboratory.drivers import instruments
        >>> gas = instruments.connect()

        """

    def __init__(self,port,address,name,upper_limit,precision):
        super(AlicatController,self).__init__(port,address)
        self.name = name
        self.precision = precision
        self.upper_limit = upper_limit

    def __str__(self):
        return '\n'.join([key+": "+str(val) for key,val in self.__dict__.items() if key not in ['keys','gases','connection']])

    def get(self):
        vals = FlowMeter.get(self)
        del vals['gas']
        return vals

    def mass_flow(self):
        """Get the massflow of the appropriate flowmeter
        """
        return self.get()['mass_flow']

    def pressure(self):
        """Get the pressure of the appropriate flowmeter
        """
        return self.get()['pressure']

    def temperature(self):
        """Gets the temperature of the appropriate flowmeter
        :returns: gas temperature
        :rtype: float
        """
        return self.get()['temperature']

    def volumetric_flow(self):
        """Gets the volumetric flow of the appropriate flowmeter"""
        return self.get()['volumetric_flow']

    def setpoint(self,setpoint=None):
        """Gets the current set point of the appropriate flowmeter

        :param setpoint: desired setpoint
        :type setpoint: float
        """
        if setpoint > self.upper_limit:
            return logger.error('The {name} gas controller has an upper limit of {limit} SCCM'.format(name=self.name,limit=self.upper_limit))

        if setpoint is not None:
            setpoint = round(setpoint,self.precision)
            return self._command('{addr}S{setpoint}\r'.format(addr=self.address,
                                                       setpoint=setpoint))
        else:
            return self.get()['setpoint']

    def reset(self):
        """Sets the massflow to 0 on the current controller"""
        return self.setpoint(0)

    def _command(self,command):

        for i in range(1,config.GLOBAL_MAXTRY):
            try:
                self._write_and_read(command)
                return True
            except Exception as e:
                if i == config.GLOBAL_MAXTRY:
                    logger.error('Error: {}{}'.format(self.name,e))

class GasControllers():
    """Global driver for all Mass Flow Controllers

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

    def __init__(self):
        self.status = False
        self.port = config.MFC_ADDRESS
        self._connect()

    def __str__(self):
        return '\n\n'.join([gas + ':\n\n' + getattr(self,gas).__str__() for gas in ['co2','co_a','co_b','h2']])

    def _connect(self):
        """
        Connects to the mass flow controllers
        """
        try:
            self.co2 = AlicatController(port=self.port, address='A', name='co2', upper_limit=config.CO2_UPPER_LIMIT, precision=config.CO2_PRECISION)
            self.co_a = AlicatController(port=self.port, address='B', name='co_a', upper_limit=config.CO_A_UPPER_LIMIT, precision=config.CO_A_PRECISION)
            self.co_b = AlicatController(port=self.port, address='C', name='co_b', upper_limit=config.CO_B_UPPER_LIMIT, precision=config.CO_B_PRECISION)
            self.h2 = AlicatController(port=self.port, address='D', name='h2', upper_limit=config.H2_UPPER_LIMIT, precision=config.H2_PRECISION)

        except Exception as e:
            logger.error('Gas - FAILED (check log for details)')
            logger.debug(e)
            self.status = False
        else:
            logger.info('Gas connected at {}'.format(self.port))
            self.all = [self.co2,self.co_a,self.co_b,self.h2]
            self.status = True

    def get_all(self):
        self.flush_all()
        return {gas.name: gas.get() for gas in self.all}

    def set_all(self,co2,co_a,co_b,h2):
        self.flush_all()
        self.co2.setpoint(co2)
        self.co_a.setpoint(co_a)
        self.co_b.setpoint(co_b)
        self.h2.setpoint(h2)

    def reset_all(self):
        """Resets all connected flow controllers to 0 massflow"""
        for controller in self.all:
            controller.reset()

    def flush_all(self):
        """Flushes the input? buffer of all flow controllers"""
        for controller in self.all: controller.flush()

    def close_all(self):
        """Closes all flow controllers"""
        for controller in self.all: controller.close()

    def shutdown(self):
        self.reset_all()
        self.close_all()


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

def get_ports():
    '''Returns a list of available serial ports for connecting to the furnace and motor

    :returns: list of available ports
    :rtype: list, str
    '''
    return [comport.device for comport in list_ports.comports()]

def connect():
    return LCR(), DAQ(), GasControllers(), Furnace(), Motor()

def reconnect(lab_obj):
    
    # ports = get_ports()

    # if not ports: return
    if not lab_obj.lcr.status: lab_obj.lcr = LCR()
    if not lab_obj.daq.status: lab_obj.daq = DAQ()
    if not lab_obj.gas.status: lab_obj.gas = GasControllers()
    if not lab_obj.furnace.status: lab_obj.furnace = Furnace()
    if not lab_obj.motor.status: lab_obj.motor = Motor()
    else:
        print('All instruments are connected!')

       