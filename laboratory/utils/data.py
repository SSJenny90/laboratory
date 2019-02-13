#!/usr/bin/env python
from laboratory import config
import numpy as np
from datetime import datetime as dt

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

        self.thermo = Thermo()
        self.gas = Gas()
        self.temp = Temp()
        self.imp = Impedance()
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

        if np.max(freq_arr) > config.max_freq:
            raise ValueError('Frequencies may not exceed {} MHz'.format(config.max_freq/10**6))
        elif np.min(freq_arr) < config.min_freq:
            raise ValueError('Frequencies may not be less than {} Hz'.format(config.min_freq))

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
        return "{}:\n\n\tdata.filename: {}\n\tdata.freq: {}\b ...] (n={})\n\tdata.time: {}\b, ...] (n={})\n\tdata.xpos: {}\b, ...] (n={})\n\tdata.step_time: {}\b, ...] (n={})\n\n{}\n\n{}\n\n{}\n\n{}".format(
            self.__class__.__name__,
            self.filename,
            self.freq[:5], len(self.freq),
            self.time[:2], len(self.time),
            self.xpos[:5], len(self.xpos),
            self.step_time[:2], len(self.step_time),
            self.thermo,
            self.temp,
            self.imp,
            self.gas
            )

class Thermo():
    """Stores thermopower data

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    tref            temperature of the internal thermistor
    te1             temperature of electrode 1
    te2             temperature of electrode 2
    volt            voltage across the sample
    =============== ===========================================================
    """

    def __init__(self):
        self.tref = []
        self.te1 = []
        self.te2 = []
        self.volt = []

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}:\n\n\tthermo.tref: {}\b, ...] (n={})\n\tthermo.te1: {}\b, ...] (n={})\n\tthermo.te2: {}\b, ...] (n={})\n\tthermo.volt: {}\b, ...] (n={})".format(
            self.__class__.__name__,
            self.tref[:5], len(self.tref),
            self.te1[:5], len(self.tref),
            self.te2[:5], len(self.tref),
            self.volt[:5], len(self.tref)
            )

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

        self.h2 = MFC_data()
        self.co2 = MFC_data()
        self.co_a = MFC_data()
        self.co_b = MFC_data()

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}:\n\n\tgas.h2:\n{}\n\tgas.co2:\n{}\n\tgas.co_a:\n {}\n\tgas.co_b:\n{}".format(
            self.__class__.__name__,
            self.h2,
            self.co2,
            self.co_a,
            self.co_b
            )

class Temp():
    """Stores furnace temperature data

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    target          target temperature of current cycle
    indicated       temperature indicated by furnace
    =============== ===========================================================
    """
    def __init__(self):

        self.target = []
        self.indicated = []

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}:\n\n\ttemp.target: {}\b, ...] (n={})\n\ttemp.indicated: {}\b, ...] (n={})".format(
            self.__class__.__name__,
            self.target[:5], len(self.target),
            self.indicated[:5], len(self.indicated)
            )

class Impedance():
    """Stores complex impedance data

    =============== ===========================================================
    Attributes      Description
    =============== ===========================================================
    Z               impedance
    theta           phase angle
    =============== ===========================================================
    """
    def __init__(self):

        self.Z = []
        self.theta = []

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}:\n\n\timp.Z: [{}\b, ...],\n\t\t{}\b, ...],\n\t\t{}\b, ...],...] (n={})\n\timp.theta: [{}\b, ...],\n\t\t{}\b, ...],\n\t\t{}\b, ...],...] (n={})".format(
            self.__class__.__name__,
            self.Z[0][:5],
            self.Z[1][:5],
            self.Z[2][:5], len(self.Z),
            self.theta[0][:5],
            self.theta[1][:5],
            self.theta[2][:5], len(self.theta)
            )

class MFC_data():
    """Stores gas data for an individual mass flow controller"""
    def __init__(self):
        self.pressure = []
        self.temperature = []
        self.vol_flow = []
        self.mass_flow = []
        self.setpoint = []

    def __repr__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "\t\tpressure: {}\b, ...] (n={})\n\t\ttemperature: {}\b, ...] (n={})\n\t\tvol_flow: {}\b, ...] (n={})\n\t\tmass_flow: {}\b, ...] (n={})\n\t\tsetpoint: {}\b, ...] (n={})".format(
        self.pressure[:5], len(self.pressure),
        self.temperature[:5], len(self.temperature),
        self.vol_flow[:5], len(self.vol_flow),
        self.mass_flow[:5], len(self.mass_flow),
        self.setpoint[:5], len(self.setpoint)
            )

def parse_datafile(filename):
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
            if line == '\n' or line.startswith('#'):
                continue

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

def append_data(filename,data):

    pass
