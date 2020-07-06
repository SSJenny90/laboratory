#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contains plotting tools for use with laboratory data.

======================= ===========================================================
Class Objects           Description
======================= ===========================================================
LabPlots                houses an assortment of plotting tools
======================= ===========================================================

======================= ===========================================================
Methods                 Description
======================= ===========================================================
impedance_fit           estimates the diameter of the impedance arc based on
dt_to_hours             converts recorded datetimes to time elapsed
leastsq_circle          fits a least squares circle to impedance data
index_temp              index the nearest temperature value
get_Re_Im               returns the real and imaginary components of complex impedance
calculate_resistivity   calculates resistivity from impedance spectra and sample
                        dimensions
======================= ===========================================================
"""
import math
import time

import numpy as np

import matplotlib.colors as colors
import matplotlib.pyplot as plt
from laboratory import config, processing, modelling
from matplotlib.offsetbox import AnchoredText
import matplotlib.dates as mdates
from impedance import preprocessing as pp

FREQ = np.around(np.geomspace(20, 2000000, 50))
GEO_FACTOR = 0.037571538461538455
K_OHM = 'k\Omega'

def index_temp(T, Tx):
    # returns the index of T nearest to the specified temp Tx. For use in colecole plots
    index = np.abs(T - Tx).argmin()
    return [index, T.to_numpy().flat[index]]

def index_freq(F):
    index = np.abs(FREQ - F).argmin()
    return [index, FREQ.flat[index]]

def index_data(data, step, time):
    if step is not None:
        data = data.loc[data.step == step]
    if time:
        data = data[time[0]:time[1]]

    return data

def voltage(data, step=None, time=[], kwargs={}):
    """Plots voltage versus time"""
    data = index_data(data,step,time)
    hours = data.index.seconds / 60 / 60 + data.index.days * 24

    fig, ax = plt.subplots()

    ax.plot(hours, data['voltage'], 'rx')
    ax.set_ylabel('Voltage [mV]')
    ax.tick_params(direction='in')
    ax.set_xlabel('Time Elapsed [hours]')
    plt.show()

def resistance(data, freq, step=None, time=[]):
    """Plots conductivity versus time"""
    data = index_data(data,step,time)

    fig, ax = plt.subplots()

    Re,_,freq = impedance_at(data,freq)

    ax.plot(data.index,Re, 'x',label='@{}Hz'.format(freq))

    # ax.set_ylabel('Conductivity [S]')
    ax.set_ylabel('Resistance [Ohm]')
    ax.tick_params(direction='in')
    ax.legend()
    ax = format_time_axis(ax)
    fig.autofmt_xdate()
    plt.show()

def temperature(data, step=None, time=[], kwargs={}):
    """Plots furnace indicated and target temperature, thermocouple temperature and thermistor data versus time elapsed. A dictionary of key word arguments may be passed through to customize this plot"""
    data = index_data(data,step,time)

    fig, ax = plt.subplots()
    ax.plot(data['thermo_1'], '.', label='Te1')
    ax.plot(data['thermo_2'], '.', label='Te2')
    ax.step(data['target'], 'y', linestyle='--', label='Target temperature')
    ax.plot(data['indicated'], label='Furnace indicated')
    ax = format_time_axis(ax)
    ax.set_ylabel(r'$Temperature [\circ C]$')
    ax.tick_params(direction='in')
    fig.tight_layout()
    fig.autofmt_xdate()

    ax.legend()
    plt.show()

def cole(data, temp_list, step=None, time=[], start=0, end=None, fit=False, **kwargs):
    """Creates a Cole-Cole plot (imaginary versus real impedance) at a given temperature. Finds the available data to the temperature specified by 'temp'. A linear least squares circle fit can be added by setting fit=True.

    :param temp: temperature in degrees C
    :type temp: float/int
    """
    fig, ax = plt.subplots()

    data = index_data(data, step, time)
    # index = np.round(np.linspace(0, len(data) - 1, n)).astype(int)
    # index = index_temp(data.temp,temp)
    # data = data.iloc[[index[0]]]

    for temp in temp_list:
        [index, Tval] = index_temp(data.temp,temp)

        Re, Im = processing.get_Re_Im(data.iloc[index].z[start:end], data.iloc[index].theta[start:end])
        p = ax.scatter(Re/1000, Im/1000, c=FREQ[start:end], norm=colors.LogNorm())
        l = ax.plot(Re/1000, Im/1000, label=r'$@{}^\circ C$'.format(round(Tval)))
        if fit:   
            circuit = 'p(R1,C1)-p(R2,C2)'
            C = 1e-10
            guess = [5e+4, C, 1e+6, C]
            complex_z = modelling.to_complex_z(Re,Im)
            f, z = pp.ignoreBelowX(FREQ, complex_z)
            f, z = pp.cropFrequencies(FREQ, complex_z, 200)
            model = modelling.model_impedance(circuit,guess,f, z)


        # ax.add_artist(AnchoredText(r'$@{}^\circ C$'.format(Tval), loc=2))

    # for _, row in data.iterrows():
    #     Tval = round(row.temp)
    #     Re, Im = processing.get_Re_Im(row.z[start:end], row.theta[start:end])
    #     p = ax.scatter(Re/1000, Im/1000, c=FREQ[start:end], norm=colors.LogNorm())
    #     l = ax.plot(Re/1000, Im/1000, 'b')
    #     if fit:
    #         processing.circle_fit(Re, Im, ax)

    # ax.axis('equal')
    ax.axis('square')
    ax.set_xlim(left=0, right=1200)
    ax.set_ylim(bottom=0, top=1200)
    ax.set_ylabel(r'$-Im(Z) [{}]$'.format(K_OHM))
    ax.set_xlabel(r'$Re(Z) [{}]$'.format(K_OHM))
    ax.ticklabel_format(style='sci', scilimits=(-3, 4), axis='both')
    ax.set_title('Cole-Cole')
    ax.legend()


    # cb = fig.colorbar(p, ax=ax, orientation="horizontal")
    cb = fig.colorbar(p, ax=ax)
    cb.set_label('Frequency')
    # cb.ax.invert_xaxis()

    plt.show()

def gas(data, step=None, time=[]):
    "Plots mass_flow data for all gases versus time elapsed"

    data = index_data(data,step,time)
    # hours = data.index.seconds / 60 / 60 + data.index.days * 24


    fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)

    ax1.plot(data['co2'], 'b.', label='CO2')
    ax1.plot(data['h2'], 'm.', label='H2')
    ax1.plot(data['co'], 'g.', label='CO')

    ax1.set_ylabel('Mass Flow [SCCM]')
    ax1.set_ylim(bottom=0)
    # ax1.set_xlim(left=0)
    ax1.set_title('Gas levels')
    ax1 = format_time_axis(ax1)
    ax1.legend()

    c = 'tab:red'
    ax2.plot(data['fugacity'], '--', color=c, label='Log[Fugacity]')
    ax2.set_ylabel('log fo2p [Pascals]',color=c)
    ax2.tick_params(axis='y', labelcolor=c)
    ax2 = format_time_axis(ax2)

    c = 'tab:blue'
    ax3 = ax2.twinx()  # instantiate a second axes that shares the same x-axis
    ax3.plot(data['ratio'], '--',color=c, label='Gas ratio')
    ax3.tick_params(axis='y', labelcolor=c)
    ax3.set_ylabel('Gas Ratio',color=c)
    ax3 = format_time_axis(ax3)

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()

def fugacity_time(data, freq, step=None, time=[]):
    "Plots mass_flow data for all gases versus time elapsed"

    data = index_data(data,step,time)

    fig, ax = plt.subplots()

    Re,_,freq = impedance_at(data,freq)
    p = ax.scatter(data.index,data['fugacity'], c=1/Re*GEO_FACTOR, norm=colors.LogNorm())
    # p = ax.scatter(Re/1000, Im/1000, c=FREQ[start:end], norm=colors.LogNorm())

    ax.set_ylabel('log10 fo2p [Pa]')
    ax = format_time_axis(ax)
    cb = fig.colorbar(p, ax=ax)
    cb.set_label('Conductivity')

    fig.autofmt_xdate()
    fig.tight_layout()
    plt.show()

def imp_diameter(data, step=None, time=[]):
    """Plots the impedance diameter against time_elapsed"""

    data = index_data(data,step,time)

    # data['diameter'] = [processing.fit_impedance(z[5:], theta[5:])
                        # for z, theta in zip(data.z, data.theta)]

    fig, ax = plt.subplots()
    ax.plot(data['resistance'], 'r')
    ax = format_time_axis(ax)
    ax.set_ylabel(r'$Diameter [\Omega$]')
    fig.autofmt_xdate()

    plt.show()

def arrhenius(data, freq=None, circuit=None):
    """Plots inverse temperature versus conductivity"""
    fig, ax = plt.subplots(1)
    if freq:
        Re,_,freq = impedance_at(data,freq)
        ax.plot(10000/data.kelvin, np.log10(1/Re*GEO_FACTOR), 'b')
        ax.plot(10000/data.kelvin, np.log10(1/Re*GEO_FACTOR), 'rx')
    elif circuit:
        circuit = 'p(R1,C1)-p(R2,C2)'
        C = 1e-10
        guess = [5e+4, C, 1e+6, C]
        complex_z = modelling.to_complex_z(z,theta)
        model = modelling.model_impedance(circuit,guess,FREQ)
    else:
        raise ValueError('Must specify either a freq or circuit string for modelling conductivity')




    ax.set_ylabel('Conductivity [S/m]')
    ax.set_xlabel('10000/Temperature [K]')

    secax = ax.secondary_xaxis('top', functions=(inverseK2celsius, celsius2inverseK))
    secax.set_xlabel(r'$Temperature [^\circ C]$')
    ax.tick_params(direction='in')
    ax.add_artist(AnchoredText('@{} Hz'.format(freq), loc=1))
    plt.show()

def bode(z, theta, freq=FREQ):
    fig, ax1 = plt.subplots(1)

    color = 'tab:red'
    ax1.set_xlabel('Frequency [Hz]')
    ax1.set_ylabel(r'$Re(Z) [{}]$'.format(K_OHM), color=color)
    ax1.semilogx(freq, z, 'o',color=color,)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Phase Angle [degrees]', color=color)  # we already handled the x-label with ax1
    ax2.semilogx(freq, np.degrees(theta), 'o', color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    fig.tight_layout()
    plt.show()

def cond_fugacity(data,freq):
    """Plots inverse temperature versus conductivity"""
    fig = plt.figure()
    ax = fig.add_subplot(111)

    Re,_,freq = impedance_at(data,freq)

    ax.semilogy(data.fugacity, 1/Re*GEO_FACTOR, 'b-', label='fugacity')

    ax.add_artist(AnchoredText('@{} Hz'.format(freq), loc=1))
    ax.set_ylabel('Conductivity [S/m]')
    ax.set_xlabel('Fugacity [Pa]')
    ax.tick_params(direction='in')
    ax.invert_xaxis()
    plt.show()

def impedance_at(data,freq):
    ind = index_freq(freq)

    z,theta = [], []

    for z1, theta1 in zip(data.z, data.theta):
        z.append(z1[ind[0]])
        theta.append(theta1[ind[0]])
    Re, Im = processing.get_Re_Im(z, theta)

    return Re, Im, ind[1]

def inverseK2celsius(x):
    return 10000/x-273

def celsius2inverseK(x):
    return 10000/(x+273)

def impedance_time(data,freq=-1):

    # freq_list = np.around(np.linspace(20, 2000000, 50))

    # index = freq_list[freq]

    fig, ax = plt.subplots(1)
    hours = data.index.seconds / 60 / 60 + data.index.days * 24

    impedance = np.array([np.array(z)[freq] for z in data.z])

    c = ['kx','bo','g^','r.']
    i=0
    for array in impedance.T:
        ax.semilogy(hours,array, c[i])
        # ax.plot(hours,array, c[i])
        i+=1

    ax.set_ylabel('Impedance [real]')
    ax.set_xlabel('Time [hours]')

def format_time_axis(ax):
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_formatter(formatter)
    return ax

def overlay_steps(ax,data):
    steps = data.step.unique()

    print(np.searchsorted(data.step,steps))

class LivePlot():

    def __init__(self):
        self.fig = plt.figure('Live Plot 1')
        self.ax = {
            'fugacity': self.fugacity(),
            'temperature': self.temperature(),
            'arrhenius': self.arrhenius(),
            'voltage': self.voltage(),
        }
    def update(self, data):
        data = processing.process_data(data)
        hours = data.index.seconds / 60 / 60 + data.index.days * 24
        self.ax['fugacity'].plot(hours,data.fugacity,'rx')
        self.ax['temperature'].plot(hours,data.temp,'rx')
        self.ax['arrhenius'].semilogy(1000/data.kelvin,data.resistivity,'rx')
        self.ax['voltage'].plot(hours,data.voltage,'rx')

    def temperature(self):
        temp = self.fig.add_subplot(221)
        temp.set_ylabel(r'$Temperature [\circ C]$')
        temp.set_xlabel('Time Elapsed [Hours]')
        temp.tick_params(direction='in')
        return temp

    def fugacity(self):
        fug = self.fig.add_subplot(223)
        fug.set_ylabel('log fo2p [Pascals]')
        fug.tick_params(direction='in')
        fug.set_xlabel('Time Elapsed [hours]')
        # fug.yscale('log')
        return fug

    def arrhenius(self):
        """Plots inverse temperature versus conductivity"""
        arr = self.fig.add_subplot(222)
        arr.set_ylabel('Conductivity [S/m]')
        arr.set_xlabel('Temperature [1000/K]')
        arr.tick_params(direction='in')
        arr.invert_xaxis()
        return arr

    def voltage(self):
        volt = self.fig.add_subplot(224)
        volt.set_ylabel('Voltage [mV]')
        volt.tick_params(direction='in')
        volt.set_xlabel('Time Elapsed [hours]')
        return volt

if __name__ == '__main__':
    z = [1.20E+06, 1.38E+05, 5.44E+04, 9.31E+03, 1.16E+03]
    theta = [-1.40E+00, -1.13E+00, -8.10E-01, -1.41E+00, -1.54E+00]
    freq = [1.59E+02, 1.59E+03, 1.59E+04, 1.59E+05, 1.59E+06]
    # convert z and theta to real and imaginary components
    Re, Im = get_Re_Im(z, theta)
    plt.scatter(Re, Im, c=freq, norm=colors.LogNorm())
    plt.show()
    # print(_calculate_conductivity(z,theta))
