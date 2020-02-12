from laboratory import config
from laboratory import drivers
from laboratory.utils import loggers, notifications, data, utils
from laboratory.utils.exceptions import SetupError
from laboratory.widgets import CountdownTimer, ProgressBar 
logger = loggers.lab(__name__)
import os
import time
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from pprint import pprint

class Laboratory():

    def __init__(self,filename=None,debug=False):
        logger.debug('-------------------------------------------')
        self._debug = debug
        self.debug = config.DEBUG
        self._delayed_start = None
        if filename:
            self.load_data(filename)
        else:
            self.load_instruments()

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self,val):
        if not type(val) is bool:
            raise ValueError('Debug must be either True of false')
        if val:
            logger.handlers[1].setLevel('DEBUG')
            self._debug = val
        else:
            logger.handlers[1].setLevel('INFO')
            self._debug = False

    def load_data(self,filename):
        """loads a previous data file for processing and analysis

        :param filename: path to data file
        :type filename: str
        """
        self.data = data.load_data(filename)

    def delayed_start(self, start_time):
        if start_time:
            logger.info('Experiment will start at {}'.format(datetime.strftime(start_time,'%H:%M on %b %d, %Y ')))
            time.sleep((start_time-datetime.now()).total_seconds())
            notifications.send_email(notifications.Messages.delayed_start.format(start_time,'%H:%M'))
            logger.info('Resuming...')

    def restart_from_backup(self):
        """
        TODO - reload an aborted experiment and pick up where it left off
        """
        #load the pickle file
        return

    def header(self,step,i):
        finish_time = 'Estimated finish: '+ datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')

        logger.info('Step {}:\n'.format(i+1))
        utils.print_df(self.controlfile.iloc[[i]])
        logger.info(finish_time)





    def instrument_errors(self,email_alert=False):
        """Checks the status of all devices. If desired, this function can send an email when something has become disconnected

        :returns: True if all devices are connected and False if any are disconnected
        :rtype: Boolean
        """
        device_list = ['furnace','motor','daq','lcr','gas']
        errors = {device:getattr(self,device).status for device in device_list if not getattr(self,device).status}

        if errors:
            if email_alert:
                notifications.send_email(notifications.Messages.device_error.format(','.join(errors)))
            return errors

    def reconnect(self):
        """Attempts to reconnect to any instruments that have been disconnected"""
        drivers.reconnect(self)

    def load_instruments(self):
        """Loads the laboratory instruments. Called automatically when calling Setup() without a filename specified.

        :returns: lcr, daq, gas, furnace, motor
        :rtype: instrument objects
        """
        logger.info('Establishing connection with instruments...\n')
        self.lcr, self.daq, self.gas, self.furnace, self.motor = drivers.connect()
        print('')

    def shut_down(self):
        """Returns the furnace to a safe temperature and closes ports to both the DAQ and LCR. (TODO need to close ports to motor and furnace)
        """
        #TODO save some information about where to start the next file
        logger.critical("Shutting down the lab...")
        self.furnace.shutdown()
        self.daq.shutdown()
        self.lcr.shutdown()
        self.gas.reset_all()
        logger.critical("Shutdown successful")

class Experiment(Laboratory):
    """ 
    Sets up the laboratory
 
    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    data            houses lab data during measurements or after parseing
    plot            contains different plotting tools for data visualisation
    command         contains the drivers for controlling instrumentation
    =============== ===========================================================

    ================= ===========================================================
    Methods           Description
    ================= ===========================================================
    device_status     checks the status of all connected devices
    get_gas           retrieves and saves data from a single mass flow controller
    get_impedance     retrieves and saves complex impedance data from the LCR meter
    get_temp          retrieves and saves temperature data from the furnace
    get_thermo        retrieves and saves thermopower data from the DAQ
    load_data         will parse a datafile and store in 'data' structure for post-
                      processing and visualisation
    load_frequencies  loads a set of frequencies into Data object
    load_instruments  connects to all available instruments
    run               begins a new set of laboratory measurements
    ================= ===========================================================

    :Example:

    >>> import laboratory
    >>> lab = laboratory.Experiment()
    >>> lab.run('some_controlfile')
    """
    def __init__(self,filename=None,debug=False):
        super().__init__(filename,debug)
        self.settings = {}

    def get_empty_dataframe(self):
        column_names = ['time','indicated','target','reference','thermo_1','thermo_2','voltage','x_position','h2','co2','co','z','theta','fugacity','ratio']
        return pd.DataFrame(columns=column_names)

    def run(self,controlfile=False):
        """
        starts a new set of measurements. requires a control file that contains
        specific instruction for the instruments to follow. see the tutorial section
        for help setting up a control file.

        :param controlfile: path to control file
        :type controlfile: str
        """
        self.setup(controlfile)
        self.delayed_start(config.START_TIME)

        # iterate through control file until finished
        for i,step in self.controlfile.iterrows():
            self.data = self.get_empty_dataframe()


            self.header(step,i)

            #set the required heating rate if a change is needed
            self.furnace.heating_rate(step.heat_rate)

            #set the required temperature if a change is needed
            self.furnace.setpoint_1(utils.find_indicated(step.target_temp))
            print('')

            #save the start time of this step
            step['time'] = datetime.now()

            #enter the main measurement loop
            if self.measurement_cycle(step):
                logger.info('Step {} complete!'.format(i+1))
                self.export_data(i,step)



                # if i < self.controlfile.shape[0]-1:
                #     est_completion = datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')
                #     notifications.send_email(notifications.Messages.step_complete.format(i+1,self.controlfile.loc[i+1,'target_temp'],i+2,i+2,est_completion))
            else:
                logger.critical('Something wen\'t wrong!')
                break

        self.shut_down()

    def measurement_cycle(self,step):
        """
        This is the main measurement loop of the program. All data is accessed and saved from within this loop

        :param step: a single row from the control file
        """
 
        self.furnace.timer_duration(minutes=3.5*step.interval)
        while True:
            self.measurement = {}
            self.progress_bar = ProgressBar(length=6+len(self.settings['freq']), hide=self.debug)
            self.furnace.reset_timer()

            #get a suite of measurements
            self.begin()
            self.get_stage_position()
            self.get_furnace()
            self.get_daq()
            self.set_fugacity(step)
            self.get_gas()
            self.get_impedance()
            self.data = self.data.append(self.measurement,ignore_index=True)
            self.backup()

            CountdownTimer(hide=self.debug).start({'minutes':step.interval},self.measurement['time'], message='Next measurement in...')

            #check to make sure everything is connected
            if self.instrument_errors():
                return

            #check to see if it's time to begin the next loop
            if utils.break_measurement_cycle(step, self.measurement['indicated'], step['time']):
                return True

    def begin(self):

        self.mean_temp = self.daq.mean_temp
        logger.debug('Collecting measurements @ {} degC...'.format(str(self.mean_temp)))
        self.progress_bar.pre_message = '@{}C'.format(str(self.mean_temp))
        self.measurement['time'] = datetime.now()

    def backup(self):
        message = 'Saving backup file...'
        self.progress_bar.update(message)
        logger.debug(message)
        data.save_obj(self.data,config.PROJECT_NAME)

    def set_fugacity(self,step):
        """Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.

            :param buffer: buffer type (see table for input options)
            :type buffer: str

            :param offset: percentage offset from specified buffer
            :type offset: float, int

            :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
            :type pressure: str
            """
        self.progress_bar.update('Calculating required co2:{} mix...'.format(step.fo2_gas))
        logger.debug('Calculating required co2:{} mix...'.format(step.fo2_gas))
        log_fugacity, ratio = self.gas.set_to_buffer( buffer=step.buffer,
                                offset= step.offset,
                                temp=self.mean_temp, 
                                gas_type=step.fo2_gas)

        self.measurement = {**self.measurement,**{'fugacity':log_fugacity,'ratio':ratio}}

    def get_stage_position(self):
        message = 'Getting stage position...'
        self.progress_bar.update(message)
        logger.debug(message)
        self.measurement['x_position'] = self.motor.position()

    def get_gas(self):
        """Gets data from the mass flow controller specified by gas_type and saves to Data structure and file

        :param gas_type: type of gas to use when calculating ratio (either 'h2' or 'co')
        :type gas_type: str

        :returns: [mass_flow, pressure, temperature, volumetric_flow, setpoint]
        :rtype: list
        """
        message = 'Getting gas readings'
        self.progress_bar.update(message)
        logger.debug(message)      
        self.measurement['h2'] = self.gas.h2.mass_flow()
        self.measurement['co2'] = self.gas.co2.mass_flow()
        self.measurement['co'] = self.gas.co_a.mass_flow() + self.gas.co_b.mass_flow()

        # for gas in ['h2','co2','co_a','co_b']:
        #     self.measurement[gas] = getattr(self.gas,gas).mass_flow()

    def get_furnace(self):
        """Retrieves the indicated temperature of the furnace and saves to Data structure and file

        .. note::

            this is the temperature indicated by the furnace, not the temperature of the sample

        :param target: target temperature of current step
        :type target: float
        """
        message = 'Getting temperature data...'
        self.progress_bar.update(message)
        logger.debug(message)
        self.measurement['target'] = self.furnace.setpoint_1()
        self.measurement['indicated'] = self.furnace.indicated()

    def get_daq(self):
        """Retrieves thermopower data from the DAQ and saves to Data structure and file

        :returns: [thermistor, te1, te2, voltage]
        :rtype: list
        """
        message = 'Getting thermopower data'
        self.progress_bar.update(message)
        logger.debug(message)
        self.measurement = {**self.measurement, **self.daq.get_thermopower()}

    def get_impedance(self):
        """Sets up the lcr meter and retrieves complex impedance data at all frequencies specified by Data.freq. Data is saved in Data.imp.z and Data.imp.theta as a list of length Data.freq. Values are also saved to the data file.
        """
        self.daq.toggle_switch('impedance')
        logger.debug('Collecting impedance data from LCR meter...')
        self.measurement = {**self.measurement,'z':[],'theta':[]}
        for _ in range(0,len(self.settings['freq'])):
            self.progress_bar.update('Collecting impedance data...')

            #return a single line for each frequency value
            line = self.lcr.get_complex_impedance()

            [self.measurement[key].append(val) for key, val in line.items()] 

        self.daq.toggle_switch('thermo')

    def setup(self,controlfile):
        """Conducts necessary checks before running an experiment abs

        :param controlfile: name of control file for the experiment
        :type controlfile: string
        """
        if not controlfile:
            raise SetupError('You must specify a valid control file!')
        else:
            controlfile = pd.read_excel(controlfile,header=1)

        if not utils.check_controlfile(controlfile):
            raise SetupError('Incorrect control file format!')

        self.load_frequencies()
        if self.settings['freq'] is None:
            raise SetupError('No frequencies have been selected for measurement')

        #configure instruments
        self.lcr.configure(self.settings['freq'])
        # self.daq.configure()

        #add some useful columns to control file
        controlfile['previous_target'] = controlfile.target_temp.shift()
        controlfile.loc[0,'previous_target'] = self.furnace.setpoint_1()
        controlfile['previous_heat_rate'] = controlfile.heat_rate.shift()
        controlfile.loc[0,'previous_heat_rate'] = self.furnace.heating_rate()
        controlfile['est_total_mins'] = np.abs((controlfile.target_temp - controlfile.previous_target)/controlfile.heat_rate + controlfile.hold_length * 60).astype(int)

        utils.print_df(controlfile)

        self.controlfile = controlfile

    def load_frequencies(self,min_f=config.MINIMUM_FREQ,max_f=config.MAXIMUM_FREQ,n=50,log=config.FREQ_LOG_SCALE):
        """Loads an np.array of frequency values.

        :param n: number of desired frequencies
        :type n: int

        :param min_f: minimum frequency (Hz) - may not be below default value of 20 Hz
        :type min_f: int,float

        :param max_f: maximum frequency (Hz) - may not exceed default value of 2*10^6 Hz
        :type max_f: int,float

        :param log: specifies whether array is created in linear or log space. default to logspace
        :type log: boolean

        :Example:

        >>> lab = Laboratory.Setup()
        >>> lab.load_frequencies(min=1000, max=10000, n=10)
        >>> print(lab.data.freq)
        [1000 2000 3000 4000 5000 6000 7000 8000 9000 10000]
        >>> lab.load_frequencies(min=1000, max=10000, n=10, log=True)
        >>> print(lab.data.freq)
        [1000 1291.55 1668.1 2154.43 2782.56 3593.81 4641.59 5994.84 7742.64 10000]"""

        logger.debug('Creating frequency data...')

        if config.FREQUENCY_LIST:
            self.settings['freq'] = np.array(config.FREQUENCY_LIST)
        elif log:
            self.settings['freq'] = np.around(np.geomspace(min_f,max_f,n))
        else:
            self.settings['freq'] = np.around(np.linspace(min_f,max_f,n))

    def export_data(self,i,step):
        project_folder = os.path.join(config.DATA_DIR,config.PROJECT_NAME)
        if not os.path.exists(project_folder):
            os.mkdir(project_folder)

        file_name = os.path.join(project_folder,'Step {}.csv'.format(i))

        with open(file_name,'w',newline="") as f:
            f.write('project_name: {}\n'.format(config.PROJECT_NAME))
            f.write('start: {}\n'.format(datetime.strftime(step['time'],'%d %B %Y @ %H:%M:%S')))
            for i in ['target_temp','interval','buffer','offset','fo2_gas']:
                f.write('{}: {}\n'.format(i,step.get(i)))

            f.write('frequencies: {}\n\n'.format(','.join(map(str, self.settings['freq']))))

            self.data.to_csv(
                path_or_buf = f,
                sep= ',',
                index=False,
            )

