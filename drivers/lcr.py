from utils import loggers
logger = loggers.lab(__name__)
import visa
import config

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
