#!/usr/bin/env python
from laboratory import config
import numpy as np
from datetime import datetime as dt
import pandas as pd
import pickle
import re

def data_dict():
    return {'furnace': {
                'indicated':[],
                'target':[],},
            'daq': {
                'reference':[],
                'thermo_1':[],
                'thermo_2':[],
                'voltage':[]},
            'motor': {
                'position': []},
            'gas': {
                'h2': [],
                'co_a': [],     # 0-50 SCCM
                'co_b': [],     # 0-2 SCCM
                'co2': []},
            'lcr': {
                'z': [],
                'theta': []},
            'file_name': '',
            'time': [],
            'step_time':[],
            'fugacity': {   'fugacity': [],
                            'ratio': [],
                            'offset': []},
            'freq':None}

class Data():
    """Storage for all data collected during experiments. Data file are loaded into this object for processing and plotting

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    freq            array of frequencies for use by the LCR meter
    filename        name of the file being used
    time            times for each measurement
    thermo          stores thermopower data
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

        self.thermo = pd.DataFrame(columns=['indicated','target','tref','te1','te2','voltage'])
        self.gas = Gas()
        self.imp = pd.DataFrame(columns=['z','theta'])
        self.filename = filename
        self.time = []
        self.stage_position = []
        self.step_time = []
        self.fugacity = pd.DataFrame(columns=['fugacity','ratio','offset'])
        self.load_frequencies()

    def __repr__(self):
        pd.set_option('display.max_rows', 5)
        """String representation of the :class:`Drivers.LCR` object."""
        return "\nFilename:\t{}\nFrequencies:\t{} (length={})\nTime:\t\t{} (length={})\nStage position:\t{} (length={})\nStep time:\t{} (length={})\n\nThermopower:\n\n{}\n\nCO2:\n\n{}\n\nCO_a:\n\n{}\n\nCO_b:\n\n{}\n\nH2:\n\n{}\n\nImpedance:\n\n{}\n\n".format(
            '/'.join(self.filename.split('\\')[-2:]),
            type(self.freq), len(self.freq),
            type(self.time), len(self.time),
            type(self.stage_position), len(self.stage_position),
            type(self.step_time), len(self.step_time),
            self.thermo,
            self.gas.co2,
            self.gas.co_a,
            self.gas.co_b,
            self.gas.h2,
            self.imp,
            )
            
    def load_frequencies(self,min=config.MINIMUM_FREQ,max=config.MAXIMUM_FREQ,n=50,log=True):
        """Creates an np.array of frequency values
        
            :param min: the minimum frequency value
            :type min: float, int
        
            :param max: the maximum frequency value
            :type max: float, int

            :param n: the desired number of frequency values to be populated between the min and max values
            :type min: int
            """
        if log:
            self.freq = np.around(np.geomspace(min,max,n))
        else:
            self.freq = np.around(np.linspace(min,max,n))


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
    data = data_dict()
    data['filename'] = filename

    with open(filename,'r') as f:
        datafile = f.readlines()

        Z,theta = [],[]
        for line in datafile:

            #split line into space delimited tokens
            # line = list(filter(None, line.split(' ')))

            if line.startswith('frequencies'):
                line = re.findall(r'(?<=\[).*?(?=\])', line)[0].split(',')
                data['freq'] = np.array([float(f) for f in line])
                continue

            line = line.split()

            #for time measurements...
            if line[0] == 'D':                 #D == Datetime
                dt_obj = dt.strptime(token[1].rstrip(),'%H:%M.%S_%d-%m-%Y')
                data.time.append(dt_obj)

            #for gas measurements...
            elif line[0] == 'G':                 #G == Gas
                gas_type = line[1]
                gas = getattr(data.gas,gas_type)

                gas.mass_flow.append(float(line[2]))
                gas.pressure.append(float(line[3]))
                gas.temperature.append(float(line[4]))
                gas.vol_flow.append(float(line[5]))
                gas.setpoint.append(float(line[6]))

            #for furnace temperature measurements...
            elif line[0] == 'F':       #F = Furnace
                data.temp.target.append(float(line[1]))
                data.temp.indicated.append(float(line[2]))

            #for thermopower measurements...
            elif line[0] == 'T':               #T = thermopower
                data.thermo.tref.append(float(line[1]))
                data.thermo.te1.append(float(line[2]))
                data.thermo.te2.append(float(line[3]))
                data.thermo.volt.append(float(line[4]))

            #if the data line being read relates to impedance measurements...
            elif line[0] == 'Z':               #Z = impedance
                Z.append(float(line[1]))
                theta.append(float(line[2]))
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

    with open(filename, 'rb') as f:  # Overwrites any existing file.
        return pickle.load(f)

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
