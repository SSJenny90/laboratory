from laboratory.utils import loggers
logger = loggers.lab(__name__)
from laboratory import config
import minimalmodbus
minimalmodbus.BAUDRATE = 9600
minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = True

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
            c=c+1

    def reset(self):
        '''
        resets the furnace to default temperature
        '''
        self._write(24,self.default_temp,'Furnace reset to {}'.format(default_temp))
        self.flush_input()
        self.flush_output()
