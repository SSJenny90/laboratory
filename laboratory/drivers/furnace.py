from laboratory.utils import loggers
logger = loggers.lab(__name__)
from laboratory import config
import minimalmodbus
minimalmodbus.BAUDRATE = 9600
minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = True
import pprint

pp = pprint.PrettyPrinter(width=1,indent=4)

class Furnace():
    """Driver for the Eurotherm 3216 Temperature Controller

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

        self.port = config.FURNACE_ADDRESS
        self.maxtry = 10
        self.default_temp = config.RESET_TEMPERATURE
        self.status = False

        self._connect(ports)

    def __str__(self):
        modbus_settings = {key: value for key,value in self.Ins.__dict__.items() if key != 'serial'}
        output = {'furnace_settings':
                        {'port': self.port,
                         'maxtry': self.maxtry},
                  'modbus_settings': modbus_settings,
                  'serial_settings': self.Ins.serial.get_settings()}
        return "\n    'status': {}".format(self.status) + '\n ' + pprint.pformat(output, indent=4, width=1)[1:]

    def _connect(self,ports):
        """
        Attempts connection to the furnace through each port in ports. Stops searching when connection is successful

        :param ports: names of available serial ports
        :type ports: list
        """
        if not ports: ports = self.port

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
                        self.configure()
                        self.status = True
                        break
                except Exception as e:
                    if c >= self.maxtry:
                        logger.debug('    Error: {}'.format(e))
                c=c+1

        if not self.status:
            logger.error('    FUR - FAILED (check log for details)')

    def configure(self):
        """
        Configures the furnace based on settings specified in the configuration file
        """
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
        self.indicated_temp = self._read(address,'Getting temperature')
        return self.indicated_temp

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

        if temperature: return self._write(self.default_temp,address,'setpoint 2')
        else: return self._read(address,'Getting SP2 temperature')

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
            'end'   : the timer has ended (query only)

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
        return self._command(status,address,'timer status',{'reset':0,'run':1,'hold':2,'end':3})

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
        self.Ins.serial.reset_input_buffer()

    def flush_output(self):
        logger.debug('Flushing furnace output')
        self.Ins.serial.reset_output_buffer()

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

        for i in range(1,self.maxtry):
            try:
                logger.debug('\t{} to {}'.format(message,value))
                self.Ins.write_register(modbus_address,value,numberOfDecimals=decimals)
                return True
            except Exception as e:
                if i == self.maxtry:
                    logger.error('\tError: "{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False

    def _read(self,modbus_address,message,decimals=0):

        for i in range(1,self.maxtry):
            try:
                logger.debug('\t{}...'.format(message))
                return self.Ins.read_register(modbus_address,numberOfDecimals=decimals)
            except Exception as e:
                if i == self.maxtry:
                    logger.error('\t"{}" failed! Check log for details'.format(message))
                    logger.debug('Error message: {}'.format(e))
                    return False
