import glob
import os
import time
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from matplotlib import colors, pyplot as plt

from laboratory import calibration, config, drivers, processing, plot
from laboratory.utils import loggers
from laboratory.utils.exceptions import SetupError
from laboratory.widgets import CountdownTimer

logger = loggers.lab(__name__)

import glob 
from tqdm import tqdm

class Laboratory():
    """This is some comment for the laboratory"""

    def __init__(self, project_name=None, debug=False):
        self._debug = debug
        self.debug = config.DEBUG
        if project_name:
            self.load_data(os.path.join(config.DATA_DIR, project_name))
        else:
            self.load_instruments()

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, val):
        if not type(val) is bool:
            raise ValueError('Debug must be either True of false')
        if val:
            logger.handlers[0].setLevel('DEBUG')
            self._debug = val
        else:
            logger.handlers[0].setLevel('INFO')
            self._debug = False

    def load_data(self, project_folder):
        """loads a previous experiment for processing and analysis

        :param project_folder: name of experiment
        :type project_folder: str
        """
        data = pd.read_pickle(
            glob.glob(os.path.join(project_folder, '*.pkl'))[0])
        self.data = self.process_data(data)

    def process_data(self, data):
        return processing.process_data(data, self.sample_area, self.sample_thickness)
        # return processing.process_data(data)

    def restart_from_backup(self):
        """
        TODO - reload an aborted experiment and pick up where it left off
        """
        # load the pickle file
        return

    def header(self, step, i):
        print('Estimated finish: {}'.format(datetime.strftime(
                datetime.now() + step.hold_length, '%H:%M %A, %b %d')))

        logger.info('Step {}:\n'.format(i+1))

        # print('======================')

        # print('Step {}\n',step[
        #     ['target_temp','hold_length','heating_rate','buffer']
        #     ])


        # print('======================')

        self.display_controlfile(self.controlfile.iloc[[i]])
        # logger.info(finish_time)

    def reconnect(self):
        """Attempts to reconnect to any instruments that have been disconnected"""
        drivers.reconnect(self)

    def load_instruments(self):
        """Loads the laboratory instruments. Called automatically when calling Setup() without a filename specified.

        :returns: lcr, daq, gas, furnace, stage
        :rtype: instrument objects
        """
        logger.info('Establishing connection with instruments...\n')
        self.lcr, self.daq, self.gas, self.furnace, self.stage = drivers.connect()
        print('')

    def shut_down(self):
        """Returns the furnace to a safe temperature and closes ports to both the DAQ and LCR. (TODO need to close ports to stage and furnace)
        """
        # TODO save some information about where to start the next file
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
    set_frequencies  loads a set of frequencies into Data object
    load_instruments  connects to all available instruments
    run               begins a new set of laboratory measurements
    ================= ===========================================================

    :Example:

    >>> import laboratory
    >>> lab = laboratory.Experiment()
    >>> lab.run('some_controlfile')
    """

    def __init__(self, debug=False):
        """Create a new Experiment instance.

        Args:
            debug (bool, optional): Displays all logging messages on the console. Defaults to False.
        """
        super().__init__(debug=debug)
        self.settings = {}
        self.project_name = ''
        self.control_file = ''
        self.sample_area = None
        self.sample_thickness = None

    def run(self, step=None):
        """Being a new experiment defined by the instructions in controlfile.

        Args:
            controlfile (str, optional): Path to controlfile containing step by step instructions for the experiment.
        """
        if not self.project_name:
            raise SetupError('You must specify a project name before beginning an experiment.')
        if not self.control_file:
            raise SetupError('No control file has been selected.')

        self.project_directory = self._create_directory()
        self.setup()
        self.data = pd.DataFrame()
        self.plot = plot.LivePlot1()
        self.plot2 = plot.LivePlot2(self.settings['freq'])

        print(self.settings['freq'])

        # iterate through control file until finished
        for i, step in self.controlfile.iterrows():
            # enter the main measurement loop
            data = self.measurement_cycle(step, i)
            if not data.empty:
                logger.info('Step {} complete!'.format(i))
            else:
                logger.critical('Something wen\'t wrong!')
                break

        self.shut_down()

    def measurement_cycle(self, step, i):
        """
        This is the main measurement loop of the program. All data is accessed and saved from within this loop

        :param step: a single row from the control file
        """
        self.plot2.draw_target_fugacity(step.buffer, [self.controlfile.target_temp.min(), self.controlfile.target_temp.max()])
        self.header(step, i)

        # adjust furnace settings
        self.furnace.heating_rate(step.heat_rate)
        self.furnace.setpoint_1(step.furnace_equivalent)
        self.furnace.timer_duration(minutes=3.5*step.interval)

        data = []
        start_time = datetime.now()
        while True:
            # get a suite of measurements
            self.prepare(i)
            self.get_stage_position()
            self.get_furnace()
            self.get_daq()
            self.set_fugacity(step)
            self.get_gas()
            self.get_impedance()
            data.append(self.measurement)
            self.update_progress_bar('Complete')
            self.update_plots(data)

            CountdownTimer(hide=self.debug,minutes=step.interval).start(
                start_time = self.measurement['time'], 
                message = 'Next measurement in...')
                
            # check to see if it's time to begin the next loop
            if self.break_cycle(step, self.measurement['indicated'], start_time):
                return self.save_and_export(data, start_time, step, i)

    def prepare(self,i):
        now = datetime.now()
        self.measurement = {'step': i}
        self.measurement['time'] = now
        self.progress_bar = tqdm(
            total = 6+len(self.settings['freq']),
            bar_format = '{l_bar}{bar}{postfix}',
            disable = self.debug,
            )
        self.furnace.reset_timer()
        self.mean_temp = self.daq.mean_temp
        logger.debug('Collecting data @ {:.1f}\N{DEGREE SIGN}C'.format(self.mean_temp))

        self.progress_bar.set_description_str(
            '{time} @ {temp:.1f}\N{DEGREE SIGN}C'.format(
                time=now.strftime('%H:%M'),
                temp=self.mean_temp,
                )
            )

    def set_fugacity(self, step):
        """Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.

            :param buffer: buffer type (see table for input options)
            :type buffer: str

            :param offset: percentage offset from specified buffer
            :type offset: float, int

            :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
            :type pressure: str
            """
        self.update_progress_bar('Calculating required gas mix')  
        log_fugacity, ratio = self.gas.set_to_buffer( buffer=step.buffer,
                                offset= step.offset,
                                temp=self.mean_temp, 
                                gas_type=step.fo2_gas)

        self.measurement.update({'fugacity': log_fugacity, 'ratio': ratio})

    def get_stage_position(self):
        self.update_progress_bar('Getting stage position')  
        self.measurement['x_position'] = self.stage.position

    def get_gas(self):
        """Gets data from the mass flow controllers and saves to the current measurement run.
        """
        self.update_progress_bar('Getting gas readings')  
        self.measurement['h2'] = self.gas.h2.mass_flow()
        self.measurement['co2'] = self.gas.co2.mass_flow()
        self.measurement['co'] = self.gas.co_a.mass_flow() + self.gas.co_b.mass_flow()

    def get_furnace(self):
        """Retrieves the indicated temperature of the furnace and saves to Data structure and file

        .. note::

            this is the temperature indicated by the furnace, not the temperature of the sample

        :param target: target temperature of current step
        :type target: float
        """
        self.update_progress_bar('Getting temperature data')
        self.measurement['target'] = self.furnace.setpoint_1()
        self.measurement['indicated'] = self.furnace.indicated()

    def get_daq(self):
        """Retrieves thermopower data from the DAQ and saves to Data structure and file

        :returns: [thermistor, te1, te2, voltage]
        :rtype: list
        """
        self.update_progress_bar('Getting thermopower data')
        self.measurement = self.measurement.update(**self.daq.get_thermopower())

    def get_impedance(self):
        """Sets up the lcr meter and retrieves complex impedance data at all frequencies specified by Data.freq. Data is saved in Data.imp.z and Data.imp.theta as a list of length Data.freq. Values are also saved to the data file.
        """
        self.daq.toggle_switch('impedance')
        self.update_progress_bar('Collecting impedance data')
        freq = self.settings['freq']

        z, theta = [], []
        for _ in self.settings['freq']:
            self.progress_bar.update(1)

            # return a single line for each frequency value
            line = self.lcr.get_complex_impedance()
            z.append(line['z'])
            theta.append(line['theta'])

            # Don't want a dodgy plot call to ruin the experiment
            try:
                self.plot2.update_right(z, theta)
            except Exception:
                pass

        results = {'z':z,'theta':theta}
        self.measurement.update(results)
        self.daq.toggle_switch('thermo')

    def update_progress_bar(self,message=None):
        self.progress_bar.set_postfix_str(message)
        logger.debug(message)
        if message == 'Complete':
            self.progress_bar.close()
        else:
            self.progress_bar.update(1)

    def update_plots(self, data):
        # dont want plot calls to halt the experiment
        try:
            self.plot.update(data, self.sample_area, self.sample_thickness)
            self.plot2.update_left(data, self.sample_area, self.sample_thickness)
        except Exception:
            pass

    def setup(self):
        """Conducts necessary checks before running an experiment abs

        :param controlfile: name of control file for the experiment
        :type controlfile: string
        """
        controlfile = pd.read_excel(self.control_file, header=1)

        if not self.check_controlfile(controlfile):
            raise SetupError('Incorrect control file format!')
        
        if self.settings.get('freq') is None:
            print(1)
            self.set_frequencies()

        # set up logging file handler
        loggers.file_handler(logger, self.project_name)

        # configure instruments
        print(self.settings['freq'])
        self.lcr.configure(self.settings['freq'])
        # self.daq.configure()

        # add some useful columns to control file
        controlfile['hold_length'] = pd.to_timedelta(
            controlfile['hold_length'], unit='H').dt.round('s')
        # column of furnace temperatures required to reach target
        controlfile['furnace_equivalent'] = calibration.find_indicated(
            controlfile['target_temp'])
        controlfile['previous_target'] = controlfile.target_temp.shift()
        controlfile.loc[0, 'previous_target'] = self.furnace.setpoint_1()
        controlfile['previous_heat_rate'] = controlfile.heat_rate.shift()
        controlfile.loc[0, 'previous_heat_rate'] = self.furnace.heating_rate()

        # controlfile['est_total_mins'] = np.abs((controlfile.target_temp - controlfile.previous_target)/controlfile.heat_rate + controlfile.hold_length * 60).astype(int)

        deltaT = np.abs(controlfile.target_temp - controlfile.previous_target)
        total_mins = pd.to_timedelta(
            deltaT/controlfile.heat_rate, unit='m') + controlfile.hold_length
        controlfile['est_total_mins'] = total_mins.dt.round('s')

        self.display_controlfile(controlfile)
        self.controlfile = controlfile

    def set_frequencies(self, min_f=config.LCR['min_freq'], max_f=config.LCR['max_freq'], num_freq=50, log_scale=True):
        """Loads an np.array

        Args:
            min_f (int, optional): Minimum frequency to generate frequency list from. Defaults to :var:~`config.MINIMUM_FREQ`.
            max_f (int, optional): Minimum frequency to generate frequency list from. Defaults to config.MAXIMUM_FREQ.
            n (int, optional): Desired length to construct frequency list out of. Defaults to 50.
            log (bool, optional): Whether the frequency list should be linear from min to max or log scale. Defaults to config.FREQ_LOG_SCALE.

        ..example 
            >>> lab = Laboratory.Setup()
            >>> lab.set_frequencies(min=1000, max=10000, n=10)
            >>> print(lab.data.freq)
            [1000 2000 3000 4000 5000 6000 7000 8000 9000 10000]
            >>> lab.set_frequencies(min=1000, max=10000, n=10, log=True)
            >>> print(lab.data.freq)
            [1000 1291.55 1668.1 2154.43 2782.56 3593.81 4641.59 5994.84 7742.64 10000]

        """

        logger.debug('Creating frequency data...')

        if log_scale:
            self.settings['freq'] = np.around(np.geomspace(min_f, max_f, num_freq))
        else:
            self.settings['freq'] =  np.around(np.linspace(min_f, max_f, num_freq))

    def save_and_export(self, data, start_time, step, i):

        # convert step data to dataframe
        data = pd.DataFrame(data)
        data.set_index('time',inplace=True)

        # concatenate to project dataframe and save
        # this overwrites the previous so that only one copy exists of the .h5 file
        self.data = pd.concat([self.data,data],sort=False)
        fname = os.path.join(self.project_directory,'data.pkl')

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.data.to_pickle(fname)

            # data.to_hdf(fname,key='step_{}'.format(i))

        # save data from the present step into it's own csv file
        file_name = os.path.join(
            self.project_directory, 'Step {}.csv'.format(i))
        with open(file_name, 'w', newline="") as f:
            f.write('project_name: {}\n'.format(self.project_name))
            f.write('start: {}\n'.format(datetime.strftime(
                start_time, '%d %B %Y @ %H:%M:%S')))
            for i in ['target_temp', 'interval', 'buffer', 'offset', 'fo2_gas']:
                f.write('{}: {}\n'.format(i, step.get(i)))

            f.write('frequencies: {}\n\n'.format(
                ','.join(map(str, self.settings['freq']))))

            data.to_csv(
                path_or_buf=f,
                sep=',',
                )

        return data

    def _create_directory(self):
        project_folder = os.path.join(config.DATA_DIR, self.project_name)
        if not os.path.exists(project_folder):
            os.mkdir(project_folder)

        return project_folder

    def break_cycle(self, step, indicated, start_time):
        """Checks whether the main measurements loop should be broken in order to proceed to the next  If temperature is increasing the loop will break once T-indicated exceeds the target temperature. If temperature is decreasing, the loop will break when T-indicated is within 5 degrees of the target. If temperature is holding, the loop will break when the hold time specified by hold_length is exceeded.

        :param step: the current measurement step
        :type step: pandas series object

        :param indicated: current indicated temperature on furnace
        :type indicated: float
        """
        # avoid boolean expression if indicted is None, will cause exception otherwise
        if not indicated:
            return

        tolerance = 5

        if indicated-tolerance <= step.furnace_equivalent <= indicated+tolerance:
            if datetime.now()-start_time >= step.hold_length:
                return True

    def check_controlfile(self, controlfile):
        """Checks to make sure the specified controlfile is a valid file that can be used by this program

        :param controlfile: a loaded control file
        :type controlfile: pd.DataFrame
        """
        columns = set(list(controlfile.columns.values))
        exp_numeric = ['target_temp', 'heat_rate', 'interval', 'offset']
        exp_str = ['buffer', 'fo2_gas']
        # expected = set().union(exp_numeric, exp_str)
        expected = set([*exp_numeric, *exp_str, 'hold_length'])

        # check if the headers in controlfile are what is expected
        if not columns == expected:
            if len(columns) > len(expected):  # if controlfile has an additional column
                dif = columns.difference(expected)
                logger.error(
                    'Found an unexpected additional column/s {} in the control file'.format(dif))
            else:  # if controlfile is missing an expected column
                dif = expected.difference(columns)
                logger.error(
                    'Could not find {} in the control file'.format(dif))
            logger.debug('    Expected to find {}'.format(expected))
            return False

        # if controlfile starts at the temperature of the furnace but was not intended to hold, it can get stuck in a loop. therefore the first value must be a 0. Only matters if no hold_length value was input into the first step
        if np.isnan(controlfile.hold_length[0]):
            controlfile.loc[0, 'hold_length'] = 0

        # check that data types in numeric variables are correct
        for header in exp_numeric:
            if not is_numeric_dtype(controlfile[header]):
                logger.error(
                    'Encountered an unexpected data type in {} - must be numeric'.format(header))
                return False

        # check that buffer inputs are valid values
        buffer_types = ['qfm', 'fmq', 'fqm', 'iw',
                        'wm', 'mh', 'qif', 'nno', 'mmo', 'cco']
        for val in controlfile.buffer:
            if val not in buffer_types:
                logger.error(
                    "Found an unexpected buffer type:  '{}'".format(val))
                logger.debug('    Must be one of {}'.format(buffer_types))
                return False

        # check that fo2_gas inputs are valid values
        gas_types = ['h2', 'co']
        for val in controlfile.fo2_gas:
            if val not in gas_types:
                logger.error("Found an unexpected gas type:  '{}'".format(val))
                logger.debug('    Must be one of {}'.format(gas_types))
                return False

        return True

    def display_controlfile(self, controlfile):
        column_names = ['target_temp',  'hold_length', 'heat_rate', 'interval', 'buffer', 'offset', 'fo2_gas']
        column_alias = ['Target [C]',  'Hold Length', 'Heat rate [C/min]', 'Interval', 'Buffer', 'Offset', 'Gas']
        print(controlfile.to_string(columns=column_names,
                                    header=column_alias, index=False) + '\n')

    def _print_step(self, step):
        print('================')



        print('================')

        pass

