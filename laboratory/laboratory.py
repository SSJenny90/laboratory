from laboratory import config
from laboratory.utils import loggers, notifications, plotting, data, utils
logger = loggers.lab(__name__)
from laboratory.drivers import instruments
import os
import time
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pprint import pprint

plt.ion()


class Setup():
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

    >>> import Laboratory
    >>> lab = Laboratory.Setup()
    >>> lab.run('some_controlfile')
    """
    def __init__(self,filename=None,debug=False):
        logger.debug('-------------------------------------------')
        # self.plot = LabPlots()
        self._debug = debug
        self.dlogger=None
        self._delayed_start = None
        if filename is None:
            self.data = data.Data()
            self.load_instruments()
        else:
            self.load_data(filename)
            self.plot = plotting.LabPlots(self.data)

    def __str__(self):

        data = '\nData: {} data points\n'.format(len(self.data.time))
        furnace = '\nFurnace: {}\n'.format(self.furnace)
        lcr = '\nLCR: {}\n'.format(self.lcr)
        daq = '\nDAQ: {}\n'.format(self.daq)
        motor = '\nMotor: {}\n'.format(self.motor)
        gas = '\nGas: {}\n'.format(self.gas)
        return data + lcr + daq + furnace + motor + gas

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self,bool):
        if bool:
            logger.handlers[1].setLevel('DEBUG')
        else:
            logger.handlers[1].setLevel('INFO')

    @property
    def delayed_start(self):
        """Starts the experiment at a given time the next day. Can be set to any 24 hour time in string format.

        :Example:

        >>> import Laboratory
        >>> lab = Laboratory.Setup()
        >>> lab.delayed_start = '0900' #start at 9am the following day
        >>> lab.run('some_controlfile')


        """
        return self._delayed_start

    @delayed_start.setter
    def delayed_start(self,start_time):
        self._delayed_start = datetime.now().replace(
                            hour=int(start_time[:2]),
                            minute=int(start_time[2:]),
                            second=0,microsecond=0) + timedelta(
                            days=1)

    def load_data(self,filename):
        """loads a previous data file for processing and analysis

        :param filename: path to data file
        :type filename: str
        """
        self.data = data.load_data(filename)

    def append_data(self,filename):
        self.data = data.append_data(filename,self.data)

    def load_frequencies(self,min,max,n,log=True,filename=None):
        """Loads an np.array of frequency values specified by either min, max and n or a file containing a list of frequencies specified by filename.

        :param filename: name of file containing frequencies
        :type filename: str

        :param n: number of desired frequencies
        :type n: int

        :param min: minimum frequency (Hz) - may not be below default value of 20 Hz
        :type min: int,float

        :param max: maximum frequency (Hz) - may not exceed default value of 2*10^6 Hz
        :type max: int,float

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
        self.data.load_frequencies(min,max,n,log,filename)

    def run(self,controlfile=False):
        """
        starts a new set of measurements. requires a control file that contains
        specific instruction for the instruments to follow. see the tutorial section
        for help setting up a control file.

        :param controlfile: path to control file
        :type controlfile: str
        """
        #make sure we have a fresh data object before starting
        self.data = data.Data()

        if not self._preflight_checklist(controlfile): return 'Couldn\'t start the experiment'

        if self.delayed_start:
            logger.info('Experiment will start at {}'.format(datetime.strftime(self.delayed_start,'%H:%M on %b %d ')))
            time.sleep((self.delayed_start-datetime.now()).total_seconds())
            notifications.send_email(notifications.Messages.delayed_start.format(self.delayed_start,'%H:%M'))
            logger.info('Resuming...')

        # iterate through control file until finished
        for i,step in self.controlfile.iterrows():
            logger.info('============================')

            logger.info('Step {}:'.format(i+1))
            finish_time = datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')
            logger.info('Estimated finish: {}'.format(finish_time))

            logger.info('============================')

            #set the required heating rate if a change is needed
            if step.heat_rate - step.previous_heat_rate is not 0:
                self.furnace.heating_rate(step.heat_rate)
            #set the required temperature if a change is needed
            if step.target_temp - step.previous_target is not 0:
                self.furnace.setpoint_1(utils.find_indicated(step.target_temp))
            print('')

            #save the start time of this step
            self.save_time('S')

            #enter the main measurement loop
            if self._measurement_cycle(step):
                logger.info('Step {} complete!'.format(i+1))
                print('')
                if i < self.controlfile.shape[0]-1:
                    est_completion = datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')
                    notifications.send_email(notifications.Messages.step_complete.format(i+1,self.controlfile.loc[i+1,'target_temp'],i+2,i+2,est_completion))
            else:
                logger.critical('Something wen\'t wrong!')
                break

        self.shut_down()

    def _measurement_cycle(self,step):
        """
        This is the main measurement loop of the program. All data is accessed and saved from within this loop

        :param step: a single row from the control file
        """
        self.furnace.timer_duration(minutes=3.5*step.interval)
        while True:
            #required to reset progress bar
            self.count = 1

            #reset the timer at the start of each loop
            self.furnace.reset_timer()

            self.daq.get_temp()
            logger.debug('Collecting measurements @ {:.1f} degC...'.format( self.daq.mean_temp))

            #get a suite of measurements
            self.save_time()
            self.get_stage_position()
            self.get_thermopower(step.target_temp)
            self.get_gas()
            self.set_fugacity(step)
            self.get_impedance()
            self.backup()
            self._progress_bar('Complete!')

            #wait until the interval has expired before starting new measurements
            utils.count_down(self.data.time[-1],step.interval)

            #check to make sure everything is connected
            if not self.device_status():
                return False

            #check to see if it's time to begin the next loop
            if utils.break_measurement_cycle(step, self.furnace.indicated_temp, self.data.step_time[-1]):
                return True

    def device_status(self,email_alert=False):
        """Checks the status of all devices. If desired, this function can send an email when something has become disconnected

        :returns: True if all devices are connected and False if any are disconnected
        :rtype: Boolean
        """
        device_list = {'furnace':False, 'motor':False, 'daq':False, 'lcr':False, 'gas':False}

        for device in device_list.keys():
            device_list[device] = getattr(self,device).status

        dev_errors = [key for key,val in device_list.items() if val is False]

        if dev_errors and email_alert:
            notifications.send_email(notifications.Messages.device_error.format(','.join(dev_errors)))

        return device_list

    def reconnect(self):
        """Attempts to reconnect to any instruments that have been disconnected"""
        instruments.reconnect(self)

    def load_instruments(self):
        """Loads all the laboratory instruments. Called automatically when calling Setup() without a filename specified.

        :returns: lcr, daq, gas, furnace, motor
        :rtype: instrument objects
        """
        logger.info('Establishing connection with instruments...')
        self.lcr, self.daq, self.gas, self.furnace, self.motor = instruments.connect()
        print(' ')

    def backup(self):
        self._progress_bar('Saving backup file...')
        data.save_obj(self.data,self.data.filename)

    def set_fugacity(self,step):
        """Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.

        :param buffer: buffer type (see table for input options)
        :type buffer: str

        :param offset: percentage offset from specified buffer
        :type offset: float, int

        :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
        :type pressure: str
        """
        self._progress_bar('Calculating required co2:{} mix...'.format(step.fo2_gas))
        logger.debug('Calculating required co2:{} mix...'.format(step.fo2_gas))
        temp = self.daq.mean_temp
        log_fugacity = self.gas.fo2_buffer(temp,step.buffer) + step.offset
        gas = {'co2':0,'co_a':0,'co_b':0,'h2':0}

        if step.fo2_gas == 'h2':
            ratio = self.gas.fugacity_h2(log_fugacity,temp)
            gas['h2'] = 10
            gas['co2'] = round(gas['h2']*ratio,2)

        elif step.fo2_gas == 'co':
            ratio = self.gas.fugacity_co(log_fugacity,temp)
            co2 = 50    #set 50 sccm as the optimal co2 flow rate
            if co2/ratio >= 20:
                co2 = round(20*ratio,2)
            gas['co2'] = co2

            co = co2/ratio
            gas['co_a'] = int(co)
            gas['co_b'] = round(co - gas['co_a'],3)

        else:
            logger.error('Incorrect gas type specified!')
            return False

        self._log_data('F {} {} {}'.format(log_fugacity,ratio, step.offset))
        self.data.fugacity = self.data.fugacity.append( {'fugacity':log_fugacity,'ratio':ratio, 'offset':step.offset}, ignore_index=True)
        self.gas.set_all(**gas)

    def get_stage_position(self):
        self.data.stage_position.append(self.motor.position())
        self._log_data('M {}'.format(self.data.stage_position[-1]))

    def get_gas(self):
        """Gets data from the mass flow controller specified by gas_type and saves to Data structure and file

        :param gas_type: type of gas to use when calculating ratio (either 'h2' or 'co')
        :type gas_type: str

        :returns: [mass_flow, pressure, temperature, volumetric_flow, setpoint]
        :rtype: list
        """
        self._progress_bar('Collecting gas data...')
        logger.debug('Collecting gas data...')
        vals = self.gas.get_all()

        #save data to object and file
        for key in vals.keys():
            data_obj = getattr(self.data.gas,key)
            data_obj = data_obj.append(vals[key],ignore_index=True)
            setattr(self.data.gas,key,data_obj)
            self._log_data(
                 'G {} {mass_flow} {pressure} {temperature} {volumetric_flow} {setpoint} '.format(key, **vals[key]))

    def get_temp(self,target):
        """Retrieves the indicated temperature of the furnace and saves to Data structure and file

        .. note::

            this is the temperature indicated by the furnace, not the temperature of the sample

        :param target: target temperature of current step
        :type target: float
        """
        logger.debug('Collecting temperature data from furnace...')
        self._progress_bar('Collecting furnace data...')
        temp = self.furnace.indicated()
        return {'target':target,'indicated':temp}

    def get_thermopower(self,target):
        """Retrieves thermopower data from the DAQ and saves to Data structure and file

        :returns: [thermistor, te1, te2, voltage]
        :rtype: list
        """
        self._progress_bar('Collecting thermopower data...')
        logger.debug('Collecting thermopower data...')
        thermo = self.daq.get_thermopower()

        #get furnace data as well and add to one dictionary
        temp = self.get_temp(target)
        vals = {**temp,**thermo}

        #save data to object and file
        self.data.thermo = self.data.thermo.append(vals,ignore_index=True)
        self._log_data(
            'T {indicated} {target} {tref} {te1} {te2} {voltage}'.format(**vals))

    def get_impedance(self):
        """Sets up the lcr meter and retrieves complex impedance data at all frequencies specified by Data.freq. Data is saved in Data.imp.z and Data.imp.theta as a list of length Data.freq. Values are also saved to the data file.
        """
        self._progress_bar('Collecting impedance data...')
        logger.debug('Collecting impedance data from LCR meter...')
        self.daq.toggle_switch('impedance')
        z,theta = [],[]

        for i,f in enumerate(self.data.freq):
            self._progress_bar('Collecting impedance data...')

            #return a single line for each frequency value
            line = self.lcr.get_complexZ()

            self._log_data('Z {z} {theta}'.format(**line),i)
            z.append(line['z'])
            theta.append(line['theta'])

        self.daq.toggle_switch('thermo')
        self.data.imp = self.data.imp.append({'z':np.array(z),
                                              'theta':np.array(theta)},
                                              ignore_index=True)

        if self.lcr.status:
            logger.debug('\tSuccessfully collected impedance data')

    def save_time(self,prefix='D'):
        """Takes input values and saves to both the current Data object and an external file

        :param vals: the values to be saved
        :type vals: dictionary

        :param gastype: [optional] required when saving gas data
        :type gastype: str
        """
        value = datetime.now()
        if prefix == 'D':
            self.data.time.append(value)
        elif prefix == 'S':
            self.data.step_time.append(value)

        self._log_data('{} {}'.format(prefix,
            datetime.strftime(value,'%H:%M.%S_%d-%m-%Y')))

    def shut_down(self):
        """Returns the furnace to a safe temperature and closes ports to both the DAQ and LCR. (TODO need to close ports to motor and furnace)
        """
        #TODO save some information about where to start the next file
        logger.critical("Shutting down the lab...")
        # self.furnace.shutdown()
        self.daq.shutdown()
        self.lcr.shutdown()
        logger.critical("success")

    def restart_from_backup(self):
        """
        TODO - reload an aborted experiment and pick up where it left off
        """
        #load the pickle file
        return

    def _progress_bar(self, message=None, decimals=0, bar_length=25):
        """Creates a terminal progress bar

        :param iteration: iteration number
        :type controlfile: int/float

        :param message: message to be displayed on the right of the progress bar
        :type message: str
        """
        iteration=self.count
        n = 7+len(self.data.freq)

        if self.debug: return   #don't display progress bar when in debugging mode

        str_format = "{0:." + str(decimals) + "f}"
        percentage = str_format.format(100 * (iteration / float(n)))
        filled_length = int(round(bar_length * iteration / float(n)))
        bar = '#' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write('\r@{:0.1f}C |{}| {}{} - {}             '.format(self.daq.mean_temp,bar, percentage, '%',message))

        if iteration == n:
            sys.stdout.write('')
        sys.stdout.flush()
        self.count += 1

    def _log_data(self,message,i=0):
        if not self.dlogger:
            return
        else:
            if i == 0:
                logger.debug('\tSaving data to file...')
            self.dlogger.critical(message)

    def _preflight_checklist(self,controlfile):
        """Conducts necessary checks before running an experiment abs

        :param controlfile: name of control file for the experiment
        :type controlfile: string
        """
        if not controlfile:  #check to make sure a control file has been specified
            logger.error('You must select a valid control file.')
            return False
        else:
            controlfile = pd.read_excel(controlfile,header=1)

        if not utils.check_controlfile(controlfile):
            logger.error('Incorrect control file format! Check log file for more details')
            return False

        if self.data.freq is None:
            logger.error('No frequencies have been selected for measurement')
            return False

        #set up the data logger
        self.dlogger = loggers.data()
        self.dlogger.critical('frequencies: {}\n'.format(self.data.freq.tolist()))
        self.data.filename = self.dlogger.handlers[0].baseFilename

        #configure instruments
        self.lcr.configure(self.data.freq)

        #add some useful columns to control file
        controlfile['previous_target'] = controlfile.target_temp.shift()
        controlfile.loc[0,'previous_target'] = utils.find_indicated(self.furnace.setpoint_1(),False)
        controlfile['previous_heat_rate'] = controlfile.heat_rate.shift()
        controlfile.loc[0,'previous_heat_rate'] = self.furnace.heating_rate()
        controlfile['est_total_mins'] = np.abs((controlfile.target_temp - controlfile.previous_target)/controlfile.heat_rate + controlfile.hold_length * 60).astype(int)

        utils.print_df(controlfile)

        self.controlfile = controlfile
        return True

if __name__ == '__main__':

    lab = Setup()
    lab.run('control2.xlsx')
