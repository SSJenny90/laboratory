from laboratory.utils import loggers
logger = loggers.lab(__name__)
from laboratory import config
import visa


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
