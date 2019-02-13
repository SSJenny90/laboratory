from . import config
from laboratory.utils import loggers, notifications, plotting, data
from laboratory.drivers import load_instruments
import os
import time
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.ion()
logger = loggers.lab(__name__)

class Setup():
    """
    Sets up the laboratory

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    data            houses lab data during measurements or after parseing
    logger          creates a logger for error reporting
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
        self.n = False
        self.dlogger=None
        self._delayed_start = None
        if filename is None:
            self.load_instruments()
            self.data = data.Data()
            self.load_frequencies()
        else:
            self.load_data(filename)
            self.plot = plotting.LabPlots(self.data)

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
        """
        loads a previous data file for processing and analysis

        :param filename: path to data file
        :type filename: str
        """
        if filename.split('.')[1] == 'txt': self.data = data.parse_datafile(filename)
        elif filename.split('.')[1] == 'pkl': self.data = utils.load_obj(filename)
        else: raise ValueError('Unsupported filetype! Must be .txt or .pkl')
        self.data.filename = filename

    def load_frequencies(self,min=config.min_freq,max=config.max_freq,n=50,log=True,filename=None):
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
        self.data.freq = utils.load_frequencies(min,max,n,log,filename)

    def run(self,controlfile=False):
        """
        starts a new set of measurements. requires a control file that contains
        specific instruction for the instruments to follow. see the tutorial section
        for help setting up a control file.

        :param controlfile: path to control file
        :type controlfile: str
        """

        if not self.preflight_checklist(controlfile): return 'Couldn\'t start the experiment'

        if self.delayed_start:
            logger.info('Experiment will start at {}'.format(datetime.strftime(self.delayed_start,'%H:%M on %b %d ')))
            time.sleep((self.delayed_start-datetime.now()).total_seconds())
            utils.send_email(config.email,utils.Messages.delayed_start.format(self.delayed_start,'%H:%M'))
            logger.info('Resuming...')

        # iterate through control file until finished
        for i,step in self.controlfile.iterrows():
            logger.debug('============================')
            logger.info('Step {}:'.format(i+1))
            logger.debug('============================')
            print('')
            # self._print_df(step)

            logger.info('Estimated completion time for current step: {}'.format(datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')))

            #set the required heating rate if a change is needed
            if step.heat_rate - step.previous_heat_rate is not 0:
                self.furnace.heating_rate(step.heat_rate)
            #set the required temperature if a change is needed
            if step.target_temp - step.previous_target is not 0:
                self.furnace.setpoint_1(utils.find_indicated(step.target_temp))
            print('')

            #start measurement cycle
            self.save_data('step',datetime.now())
            if self._measurement_loop(step):     #enter the main measurement loop
                logger.info('Step {} complete!'.format(i+1))
                print('')
                if i < self.controlfile.shape[0]-1:
                    est_completion = datetime.strftime(datetime.now() + timedelta(minutes=step.est_total_mins),'%H:%M %A, %b %d')
                    utils.send_email(config.email,utils.Messages.step_complete.format(i+1,self.controlfile.loc[i+1,'target_temp'],i+2,i+2,est_completion))
            else:
                logger.critical('Something wen\'t wrong!')
                break

        self.shut_down()

    def _measurement_loop(self,step):
        """
        This is the main measurement loop of the program. All data is accessed and saved from within this loop

        :param step: a single row from the control file
        """
        # step_start = time.time()
        step_start = datetime.now()
        self.n = 7+len(self.data.freq)/10
        while True:
            start = time.time()
            self.save_data('time',datetime.now())

            #get some measurements
            self.sample_temp = np.mean(self.daq.get_temp()[1:2])
            logger.debug('Collecting measurements @ {:.1f} degC...'.format(self.sample_temp))

            self._progress_bar(1,'Collecting furnace data...')
            self.get_temp(step.target_temp)

            self._progress_bar(2,'Collecting gas data...')
            for gas in ['h2','co2','co_a','co_b']: self.get_gas(gas)

            self._progress_bar(3,'Collecting thermopower data...')
            self.get_thermopower()

            self._progress_bar(4,'Collecting impedance data...')
            self.get_impedance()

            #setting the required gas mix
            self._progress_bar(5+len(self.data.freq)/10,'Setting required gas levels...')
            self.set_fugacity(step.buffer,step.offset,step.fo2_gas)

            #save a pickle object as backup
            self._progress_bar(6+len(self.data.freq)/10,'Saving backup file...')
            utils.save_obj(self.data,self.data.filename)
            self._progress_bar(7+len(self.data.freq)/10,'Complete!')

            #wait until the interval has expired before starting new measurements
            self._count_down(start,step.interval)

            if not self.device_status(): return False   #check to make sure everything is connected
            if self._break_loop(step,step_start): return True

    def device_status(self):
        """
        Checks the status of all devices. If desired, this function can send an email when something has become disconnected

        :returns: True if all devices are connected and False if any are disconnected
        :rtype: Boolean
        """
        device_list = {'furnace':False,'motor':False,'daq':False,'lcr':False,'mfc':False}
        for device in device_list.keys():
            device_list[device] = getattr(self,device).status

        dev_errors = [key for key,val in device_list.items() if val is False]

        if dev_errors:
            try:
                utils.send_email(config.email,utils.Messages.device_error.format(','.join(dev_errors)))
            except Exception:
                logger.debug('Could not send email')

        return device_list

    def reconnect(self):
        """Attempts to reconnect to any instruments that have been disconnected"""
        drivers.reconnect(self)

    def load_instruments(self):
        """Loads all the laboratory instruments. Called automatically when calling Setup() without a filename specified.

        :returns: lcr, daq, mfc, furnace, motor
        :rtype: instrument objects
        """
        logger.info('Establishing connection with instruments...')
        self.lcr,self.daq,self.mfc,self.furnace,self.motor = drivers.load_instruments()
        print(' ')

    def set_fugacity(self,buffer,offset,gas_type):
        """Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.

        :param buffer: buffer type (see table for input options)
        :type buffer: str

        :param offset: percentage offset from specified buffer
        :type offset: float, int

        :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
        :type pressure: str
        """
        logger.debug('Recalculating required co2:{:s} mix...'.format(gas_type))
        vals = self.daq.get_temp()
        temp = np.mean(vals[1:2])
        fo2p = self.mfc.fo2_buffer(temp,buffer)

        if gas_type == 'h2':
            ratio = self.mfc.fugacity_h2(fo2p,temp)
            h2 = 10
            co2 = round(h2*ratio,2)

            logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))
            logger.debug('    Setting CO2 to {}'.format(co2))
            self.save_data('delete_me',co2,gastype='co2')
            # self.mfc.co2.set_massflow()
            logger.debug('    Setting H2 to {:.2f}'.format(h2))
            self.save_data('delete_me',h2,gastype='h2')
            # self.mfc.h2.set_massflow()

        elif gas_type == 'co':

            ratio = self.mfc.fugacity_co(fo2p,temp)
            logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))

            co2 = 50    #sets 50 sccm as the optimal co2 flow rate
            if co2/ratio >= 20:
                co2 = round(20*ratio,2)

            co = round(co2/ratio,3)
            co_a = int(co2/ratio)
            co_b = co - co_a
            logger.debug('    Setting CO2 to {}'.format(co2))
            # self.mfc.co2.set_massflow(co2)
            self.save_data('delete_me',co2,gastype='co2')
            logger.debug('    Setting CO_a = {0:.3f}'.format(co_a))
            # self.mfc.co_a.set_massflow(co_a)
            self.save_data('delete_me',co_a,gastype='co_a')
            logger.debug('    Setting CO_b = {0:.3f}'.format(co_b))
            # self.mfc.co_b.set_massflow(co_b)
            self.save_data('delete_me',co_b,gastype='co_b')
        else:
            logger.error('Incorrect gas type specified!')

    def get_gas(self,gas_type):
        """Gets data from the mass flow controller specified by gas_type and saves to Data structure and file

        :param gas_type: type of gas to use when calculating ratio (either 'h2' or 'co')
        :type gas_type: str

        :returns: [mass_flow, pressure, temperature, volumetric_flow, setpoint]
        :rtype: list
        """
        logger.debug('Collecting {} data...'.format(gas_type))
        gas = getattr(self.mfc,gas_type)
        self.save_data('gas',vals=gas.get_all(),gastype=gas_type)

    def get_temp(self,target):
        """Retrieves the indicated temperature of the furnace and saves to Data structure and file

        .. note::

            this is the temperature indicated by the furnace, not the temperature of the sample

        :param target: target temperature of current step
        :type target: float
        """
        logger.debug('Collecting temperature data from furnace...')
        indicated_temp = self.furnace.indicated()
        if indicated_temp:
            self.indicated_temp = indicated_temp
            self.save_data('temperature',[target,self.indicated_temp])
            self.furnace.status = True
        else:
            self.furnace.status = False

    def get_thermopower(self):
        """Retrieves thermopower data from the DAQ and saves to Data structure and file

        :returns: [thermistor, te1, te2, voltage]
        :rtype: list
        """
        logger.debug('Collecting thermopower data from DAQ...')
        thermo =  self.daq.get_thermopower()
        if thermo: self.save_data('thermopower',thermo)

    def get_impedance(self):
        """Sets up the lcr meter and retrieves complex impedance data at all frequencies specified by Data.freq. Data is saved in Data.imp.z and Data.imp.theta as a list of length Data.freq. Values are also saved to the data file.
        """
        logger.debug('Collecting impedance data from LCR meter...')
        self.daq.toggle_switch('impedance')
        Z,theta = [],[]

        for i,f in enumerate(self.data.freq):
            if self.n: self._progress_bar(4+i/10,'Collecting impedance data...')

            complexZ = self.lcr.get_complexZ()    #returns one line for each frequency
            if complexZ[0] is 9.9e+37: complexZ[0] = float('nan')
            if complexZ[1] is 9.9e+37: complexZ[1] = float('nan')

            if self.dlogger: self.dlogger.critical('Z {} {}'.format(complexZ[0],complexZ[1]))
            Z.append(complexZ[0])
            theta.append(complexZ[1])

        self.save_data('impedance',[Z,theta])
        self.daq.toggle_switch('thermo')

        if self.lcr.status:
            logger.debug('\tSuccessfully collected impedance data')

    def save_data(self,val_type,vals,gastype=None):
        """Takes input values and saves to both the current Data object and an external file

        :param val_type: type of measurement being saved
        :type val_type: str

        :param vals: the required values suitable to that specified by val_type
        :type vals: list

        :param gastype: [optional] required when saving gas data
        :type gastype: str
        """
        logger.debug('\tSaving {} data to file'.format(val_type))
        if val_type == 'gas':
            gas = getattr(self.data.gas,gastype)
            gas.mass_flow.append(vals[0])
            gas.pressure.append(vals[1])
            gas.temperature.append(vals[2])
            gas.vol_flow.append(vals[3])
            gas.setpoint.append(vals[4])
            if self.dlogger: self.dlogger.critical('G {} {} {} {} {} {}'.format(gastype,vals[0],vals[1],vals[2],vals[3],vals[4]))
        elif val_type == 'temperature':
            self.data.temp.target.append(vals[0])
            self.data.temp.indicated.append(vals[1])
            if self.dlogger: self.dlogger.critical('F {} {}'.format(vals[0],vals[1]))
        elif val_type == 'impedance':
            self.data.imp.Z.append(vals[0])
            self.data.imp.theta.append(vals[1])
        elif val_type == 'thermopower':
            self.data.thermo.tref.append(vals[0])
            self.data.thermo.te1.append(vals[1])
            self.data.thermo.te2.append(vals[2])
            self.data.thermo.volt.append(vals[3])
            if self.dlogger: self.dlogger.critical('T {} {} {} {}'.format(vals[0],vals[1],vals[2],vals[3]))
        elif val_type == 'time':
            self.data.time.append(vals)
            if self.dlogger: self.dlogger.critical('D {}'.format(datetime.strftime(vals,'%H:%M.%S_%d-%m-%Y')))
        elif val_type == 'step':
            self.data.step_time.append(vals)
            if self.dlogger: self.dlogger.critical('S {}'.format(datetime.strftime(vals,'%H:%M.%S_%d-%m-%Y')))

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

    def _count_down(self,start,interval,time_remaining=1):
        """Controls the count down until next measurement cycle

        :param interval: time in seconds remaining until next measurement
        :type interval: float/int
        """
        print('')
        while time_remaining > 0:
            time_remaining = int(interval*60+start-time.time())
            mins = int(time_remaining/60)
            seconds = time_remaining%60
            time.sleep(1)
            sys.stdout.write('\rNext measurement in... {:02}m {:02}s'.format(mins,seconds))
            sys.stdout.flush()
            if time_remaining < 1:
                sys.stdout.write('\r                                          \r'),
                sys.stdout.flush()

    def _progress_bar(self,iteration, message,decimals=0, bar_length=25):
        """Creates a terminal progress bar

        :param iteration: iteration number
        :type controlfile: int/float

        :param message: message to be displayed on the right of the progress bar
        :type message: str
        """
        if self.debug: return   #don't display progress bar when in debugging mode

        str_format = "{0:." + str(decimals) + "f}"
        percentage = str_format.format(100 * (iteration / float(self.n)))
        filled_length = int(round(bar_length * iteration / float(self.n)))
        bar = '#' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write('\r@{:0.1f}C |{}| {}{} - {}             '.format(self.sample_temp,bar, percentage, '%',message))

        if iteration == self.n: sys.stdout.write('')
        sys.stdout.flush()

    def _break_loop(self,step,loop_start):
        """Checks whether the main measurements loop should be broken in order to proceed to the next step. If temperature is increasing the loop will break once T-indicated exceeds the target temperature. If temperature is decreasing, the loop will break when T-indicated is within 5 degrees of the target. If temperature is holding, the loop will break when the hold time specified by step.hold_length is exceeded.

        :param step: current measurement step
        :type param: pd.dataframe

        :param Tind: current indicated temperature on furnace
        :type Tind: float

        :param loop_start: start time of the current measurement cycle
        :type loop_start: datetime object
        """
        #if T is increasing, break when Tind exceeds target_temp
        if step.target_temp > step.previous_target:
            if self.indicated_temp >= step.target_temp:
                # if time.time()-loop_start >= step.hold_length*60*60:
                if (datetime.now()-loop_start).hours >= step.hold_length:
                    return True

        #if temperature is decreasing, Tind rarely drops below the target - hence the + 5
        elif step.target_temp < step.previous_target:
            if self.indicated_temp < step.target_temp + 5:
                if (datetime.now()-loop_start).hours >= step.hold_length:
                    return True
        elif step.hold_length == 0: return True
        elif (datetime.now()-loop_start).hours >= step.hold_length: return True

        return False

    def _print_df(self,df):
        # for ind,line in enumerate(step[:-2]):
        #     if len(step.index[ind]) > 7:
        #         logger.info('\t{}\t{}'.format(step.index[ind],line))
        #     else:
        #         logger.info('\t{}\t\t{}'.format(step.index[ind],line))
        # print('')
        column_names = ['target_temp', 'hold_length', 'heat_rate', 'interval', 'buffer', 'offset', 'fo2_gas', 'est_total_mins']
        column_alias = ['Target [C]', 'Hold length [hrs]', 'Heating rate [C/min]', 'Interval', 'Buffer', 'Offset', 'Gas', 'Estimated minutes']

        print(df.to_string(columns=column_names,header=column_alias,index=False,line_width=10))
        print(' ')

    def preflight_checklist(self,controlfile):
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
        self.dlogger = utils.data_logger()
        self.dlogger.critical('frequencies: {}\n'.format(self.data.freq.to_list()))
        self.data.filename = self.dlogger.handlers[0].baseFilename

        #configure instruments
        self.daq.configure()
        self.lcr.configure(self.data.freq)

        #add some useful columns to control file
        controlfile['previous_target'] = controlfile.target_temp.shift()
        controlfile.loc[0,'previous_target'] = utils.find_indicated(self.furnace.setpoint_1(),False)
        controlfile['previous_heat_rate'] = controlfile.heat_rate.shift()
        controlfile.loc[0,'previous_heat_rate'] = self.furnace.heating_rate()
        controlfile['est_total_mins'] = np.abs((controlfile.target_temp - controlfile.previous_target)/controlfile.heat_rate + controlfile.hold_length * 60)

        print('Controlfile:\n')
        column_names = ['target_temp','hold_length','heat_rate','interval','buffer','offset','fo2_gas','est_total_mins']
        column_alias = ['Target [C]','Hold length [hrs]','Heating rate [C/min]','Interval','Buffer','Offset','Gas','Estimated minutes']
        print(controlfile.to_string(columns=column_names,header=column_alias,index=False))
        print(' ')

        self.controlfile = controlfile
        return True

if __name__ == '__main__':

    lab = Setup()
    lab.run('control2.xlsx')
