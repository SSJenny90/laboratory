#!/usr/bin/env python
from laboratory import config
import numpy as np
from datetime import datetime as dt
import pandas as pd
import pickle

class Data():
    """Storage for all data collected during experiments. Data file are loaded into this object for processing and plotting

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    freq            array of frequencies for use by the LCR meter
    filename        name of the file being used
    time            times for each measurement
    thermo          stroes thermopower data
    gas             stores gas and fugacity data
    temp            stores temperature data
    imp             stores impedance data
    xpos            stores stage x position at each measurement
    =============== ===========================================================

    :example:

    >>> lab = Laboratory.Setup('somefile.dat')
    >>> print(lab.data.temp.indicated)
    [100,105,110,115,120]
    """

    def __init__(self,freq=None,filename=None):

        # self.thermo = Thermo()
        self.thermo = pd.DataFrame(columns=['tref','te1','te2','voltage'])
        self.gas = Gas()
        self.temp =  pd.DataFrame(columns=['indicated','target'])
        self.imp = pd.DataFrame(columns=['z','theta'])
        self._freq = freq
        self.filename = filename
        self.time = []
        self.xpos = []
        self.step_time = []

    # --freq-------------------------------------------
    @property
    def freq(self):
        return self._freq

    @freq.setter
    def freq(self,freq_arr):
        """
        Set the freq values

        :param freq_arr: array of frequencies (Hz)
        :type freq_arr: np.ndarray
        """
        if freq_arr is not None:
            for f in freq_arr:
                if not isinstance(f,(float,int)):
                    raise TypeError('data.freq must be a list of floats or ints')
            self._freq = np.array(freq_arr)
        else:
            return None

        if np.max(freq_arr) > config.MAXIMUM_FREQ:
            raise ValueError('Frequencies may not exceed {} MHz'.format(config.MAXIMUM_FREQ/10**6))
        elif np.min(freq_arr) < config.MINIMUM_FREQ:
            raise ValueError('Frequencies may not be less than {} Hz'.format(config.MINIMUM_FREQ))

    # --filename---------------------------------------
    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self,fname):
        if fname is not None:
            if not isinstance(fname,str):
                raise TypeError('data.filename must be a string')
        self._filename = fname

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}:\n\nfilename: {}\nfreq: {}\b ...] (n={})\ntime: {}\b, ...] (n={})\nxpos: {}\b, ...] (n={})\nstep_time: {}\b, ...] (n={})\n\nThermopower:\n\n{}\n\nFurnace:\n\n{}\n\nImpedance:\n\n{}\n\nGas: {}".format(
            self.__class__.__name__,
            self.filename,
            self.freq[:5], len(self.freq),
            self.time[:2], len(self.time),
            self.xpos[:5], len(self.xpos),
            self.step_time[:2], len(self.step_time),
            self.thermo.tail(),
            self.temp.tail(),
            self.imp.tail(1).to_string(),
            self.gas
            )

    def __add__(self,other):
        if not np.array_equal(self.freq,other.freq):
            raise Exception('Data object must use the same frequency values')
            return

        self.thermo = self.thermo + other.thermo
        self.gas = self.gas + other.gas
        self.temp = self.temp + other.temp
        self.imp = self.imp + other.imp
        self.filename = self.filename + '_a'
        self.time.extend(other.time)
        # self.xpos = self.time.extend(other.time)
        # self.step_time = self.time.extend(other.time)
        return self


class Gas():
    """Stores the seperate gas data under one roof

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    h2              hydrogen flow rate
    co2             carbon dioxide flow rate
    co_a            carbon monoxide corase flow rate
    co_b            carbon monoxide corase flow rate
    =============== ===========================================================
    """
    def __init__(self):

        self.h2 = pd.DataFrame(columns=['massflow','pressure','temperature','volumetric_flow','setpoint'])
        self.co2 = pd.DataFrame(columns=['massflow','pressure','temperature','volumetric_flow','setpoint'])
        self.co_a = pd.DataFrame(columns=['massflow','pressure','temperature','volumetric_flow','setpoint'])
        self.co_b = pd.DataFrame(columns=['massflow','pressure','temperature','volumetric_flow','setpoint'])

def load_data(filename):
    if filename.endswith('.txt'):
         return _load_text('laboratory/datafiles/' + filename)
    elif filename.endswith('.pkl'):
         return _load_pkl('laboratory/datafiles/' + filename)
    else:
        raise ValueError('Unsupported filetype! Must be .txt or .pkl')

def _load_text(filename):
    """Parses a text file and stores the data in the Lab.Data object

    :param filename: name of the file to be parsed
    :type filename: str
    """
    data = Data()
    data.filename = filename

    with open(filename,'r') as file:
        datafile = file.readlines()

        Z,theta = [],[]
        for line in datafile:

            #skip empty or commented lines
            if line == '\n' or line.startswith('#'): continue

            #split line into space delimited tokens
            token = list(filter(None, line.split(' ')))

            if token[0] == 'frequencies:':
                line = line.replace(']','').replace('[','').replace(',','')
                token = list(filter(None, line.split(' ')))
                data.freq = np.array([float(f) for f in token[1:]])

            #for time measurements...
            if token[0] == 'D':                 #D == Datetime
                dt_obj = dt.strptime(token[1].rstrip(),'%H:%M.%S_%d-%m-%Y')
                data.time.append(dt_obj)

            #for gas measurements...
            elif token[0] == 'G':                 #G == Gas
                gas_type = token[1]
                gas = getattr(data.gas,gas_type)

                gas.mass_flow.append(float(token[2]))
                gas.pressure.append(float(token[3]))
                gas.temperature.append(float(token[4]))
                gas.vol_flow.append(float(token[5]))
                gas.setpoint.append(float(token[6]))

            #for furnace temperature measurements...
            elif token[0] == 'F':       #F = Furnace
                data.temp.target.append(float(token[1]))
                data.temp.indicated.append(float(token[2]))

            #for thermopower measurements...
            elif token[0] == 'T':               #T = thermopower
                data.thermo.tref.append(float(token[1]))
                data.thermo.te1.append(float(token[2]))
                data.thermo.te2.append(float(token[3]))
                data.thermo.volt.append(float(token[4]))

            #if the data line being read relates to impedance measurements...
            elif token[0] == 'Z':               #Z = impedance
                Z.append(float(token[1]))
                theta.append(float(token[2]))
                if len(Z) == len(data.freq):
                    data.imp.Z.append(Z)
                    data.imp.theta.append(theta)
                    Z, theta = [],[]

    return data

def _load_pkl(filename):
    """Loads a .pkl file

    :param filename: full path to file. must be a .pkl
    :type filename: str
    """
    if not filename.endswith('.pkl'):
        filename = filename + '.pkl'

    # for f in filenames:
    with open(filename, 'rb') as input:  # Overwrites any existing file.
        return pickle.load(input)

def append_data(filename,data):

    pass

def save_obj(obj, filename):
    """Saves an object instance as a .pkl file for later retrieval. Can be loaded again using :meth:'Utils.load_obj'

    :param obj: the object instance to be saved
    :type obj: class

    :param filename: name of file
    :type filename: str
    """
    filename = filename.split('.')[0]
    with open(filename + '.pkl', 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_frequencies(min,max,n,log,filename):
    """Creates an np.array of frequency values specified by either min, max and n or a file containing a list of frequencies specified by filename"""
    if filename is not None:
        with open(filename) as file:
            freq = [line.rstrip() for line in file]
        return np.around(np.array([float(f) for f in freq]))
    elif log is True: return np.around(np.geomspace(min,max,n))
    elif log is False: return np.around(np.linspace(min,max,n))
    else:
        return False

def find_indicated(temperature,default=True):
    #from calibration experiment
    furnace = np.array([400,500,600,700,800,900,1000])
    daq = np.array([253.46,335.82,422.67,512,604.5,698.7,795.3])
    A = np.vstack([daq,np.ones(len(daq))]).T
    m,c = np.linalg.lstsq(A,furnace,rcond=None)[0]

    if default: return np.around(np.multiply(m,temperature)+c,2) #return a furnace value for given temperature
    else: return np.around(np.divide(temperature-c,m),2)    #return a daq value for given temperature
