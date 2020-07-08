#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import time

import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from laboratory import config, processing, modelling
from matplotlib.offsetbox import AnchoredText
import matplotlib.dates as mdates
from impedance import preprocessing as pp
from datetime import datetime as dt
from impedance.models.circuits import fitting
# plt.style.use('seaborn-darkgrid')

plt.ion()
FREQ = np.around(np.geomspace(20, 2000000, 50))
K_OHM = r'k\Omega'
GEO_FACTOR =  97.686e-6 / 2.6e-3

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

    fig, ax = plt.subplots()

    ax.plot(data['voltage'], 'rx')
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

def conductivity(data, temp_list=None, ax=None, fmt='o'):

    def calculate(row):
      f, z = pp.cropFrequencies(FREQ, row.complex_z, 200)
      f, z = pp.ignoreBelowX(f, z)
      circuit = 'p(R1,C1)-p(R2,C2)'
      guess = [5e+4, 1e-10, 5e+6, 1e-10]
      model = modelling.model_impedance(circuit,guess,f, z)
      return modelling.get_resistance(model)


    resistance = []
    temp_out = []
    if temp_list:
        for temp in temp_list:
            [index, _] = index_temp(data.temp,temp)
            row = data.iloc[index]
            resistance.append(calculate(row))
            temp_out.append(row.kelvin)
    else:
        for _, row in data.iterrows():
            resistance.append(calculate(row))
            temp_out.append(row.wkelvin)

    conductivity = 1 / (np.array(resistance) * GEO_FACTOR)

    ax.plot(data.index,np.log10(conductivity),fmt)

    ax.set_ylabel('Log10 Conductivity [S/m]')

    ax.tick_params(direction='in')

def temperature(data, step=None, time=[], kwargs={}):
    """Plots furnace indicated and target temperature, thermocouple temperature and thermistor data versus time elapsed. A dictionary of key word arguments may be passed through to customize this plot"""
    data = index_data(data,step,time)

    fig, ax = plt.subplots()
    ax.plot(data['thermo_1'], '.', label='Te1')
    ax.plot(data['thermo_2'], '.', label='Te2')
    ax.step(data['target'], 'y', linestyle='--', label='Target temperature')
    # ax.plot(data['indicated'], label='Furnace indicated')
    ax = format_time_axis(ax)
    ax.set_ylabel(r'$Temperature [\circ C]$')
    ax.tick_params(direction='in')
    fig.tight_layout()
    fig.autofmt_xdate()

    ax.legend()
    plt.show()

def cole(data, temp_list, start=0, end=None, fit=False, **kwargs):
    """Creates a Cole-Cole plot (imaginary versus real impedance) at a given temperature. Finds the available data to the temperature specified by 'temp'. A linear least squares circle fit can be added by setting fit=True.

    :param temp: temperature in degrees C
    :type temp: float/int
    """
    fig, ax = plt.subplots()

    resistance = []
    for temp in temp_list:
        [index, Tval] = index_temp(data.temp,temp)
        z = data.complex_z.iloc[index]
        f, z = pp.cropFrequencies(FREQ, z, 200)
        f, z = pp.ignoreBelowX(f, z)
        p = ax.scatter(np.real(z)/1000, np.abs(np.imag(z))/1000, c=f, norm=colors.LogNorm())

        if fit:   
            circuit = 'p(R1,C1)-p(R2,C2)'
            C = 1e-10
            guess = [5e+4, C, 5e+6, C]
            model = modelling.model_impedance(circuit,guess,f, z)
            rmse = fitting.rmse(z, model.predict(f))
            print(rmse)
            predicted = model.predict(np.geomspace(0.001,2000000,100))
            ax.plot(np.real(predicted)/1000, np.abs(np.imag(predicted))/1000, label=r'$@{}^\circ C$'.format(round(Tval)))       
            resistance.append(modelling.get_resistance(model))
            ax.add_artist(AnchoredText(circuit, loc=2))

    # ax.axis('equal')
    ax.axis('square')
    # ax.set_xlim(left=0, right=1200)
    # ax.set_ylim(bottom=0, top=1200)
    ax.set_ylabel(r'$-Im(Z) [{}]$'.format(K_OHM))
    ax.set_xlabel(r'$Re(Z) [{}]$'.format(K_OHM))
    ax.ticklabel_format(style='sci', scilimits=(-3, 4), axis='both')
    ax.set_title('Cole-Cole')
    ax.legend()


    # cb = fig.colorbar(p, ax=ax, orientation="horizontal")
    cb = fig.colorbar(p, ax=ax)
    cb.set_label('Frequency')
    cb.ax.invert_xaxis()
    plt.show()

    if fit:
        return resistance

    # for _, row in data.iterrows():
    #     Tval = round(row.temp)
    #     Re, Im = processing.get_Re_Im(row.z[start:end], row.theta[start:end])
    #     p = ax.scatter(Re/1000, Im/1000, c=FREQ[start:end], norm=colors.LogNorm())
    #     l = ax.plot(Re/1000, Im/1000, 'b')
    #     if fit:
    #         processing.circle_fit(Re, Im, ax)

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

def arrhenius(data, temp_list=None, ax=None, fmt='o'):
    """Plots inverse temperature versus conductivity"""

    def calculate(row):
        f, z = pp.cropFrequencies(FREQ, row.complex_z, 200)
        f, z = pp.ignoreBelowX(f, z)
        circuit = 'p(R1,C1)-p(R2,C2)'
        guess = [5e+4, 1e-10, 5e+6, 1e-10]
        model = modelling.model_impedance(circuit,guess,f, z)
        return modelling.get_resistance(model)

    resistance = []
    temp_out = []
    if temp_list:
        for temp in temp_list:
            [index, _] = index_temp(data.temp,temp)
            row = data.iloc[index]
            resistance.append(calculate(row))
            temp_out.append(row.kelvin)
    else:
        for _, row in data.iterrows():
            resistance.append(calculate(row))
            temp_out.append(row.kelvin)

    conductivity = 1 / (np.array(resistance) * GEO_FACTOR)

    ax.plot(10000/np.array(temp_out),np.log10(conductivity),fmt)
    # ax.plot(np.array(temp_out),np.log10(conductivity),fmt)
    # ax.semilogy(10000/np.array(temp_out),conductivity,fmt)

    # prevents redrawing axes, only really required for the second axes because multiple calls will redraw over itself
    if not ax.xaxis.get_label().get_text():
        ax.set_ylabel('Log10 Conductivity [S/m]')
        ax.set_xlabel('10000/Temperature [K]')
        secax = ax.secondary_xaxis('top', functions=(inverseK2celsius, celsius2inverseK))
        secax.set_xlabel(r'$Temperature [^\circ C]$')
        ax.tick_params(direction='in')
    plt.draw()

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

def cond_fugacity(data, temp_list=None, ax=None, fmt='o'):
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


class LivePlot1():

    def __init__(self):
        self.fig, ax = plt.subplots(5,1, sharex=True, num='Live Plot 1')
        plt.subplots_adjust(hspace=.1)
        self.ax = {
            'conductivity': self.conductivity(ax[0]),
            'fugacity': self.fugacity(ax[1]),
            'temperature': self.temperature(ax[2]),
            'gas': self.gas(ax[3]),
            'voltage': self.voltage(ax[4]),
            }

        self.draw()

    def update(self, data, area, thickness,freq=2000):
        # recalls the figure in case it was closed
        # self.fig = plt.figure('Live Plot 1')
        data = processing.process_data(data, area, thickness)
        # hours = data.index.seconds / 60 / 60 + data.index.days * 24

        # update conductivity
        Re,_,freq = impedance_at(data,freq)
        conductivity = np.log10((1/Re)*(area / thickness))
        self.conductivity.set_data(data.index,conductivity)
        self.ax['conductivity'].add_artist(AnchoredText('@{} Hz'.format(freq), loc=1))



        # update temperatures
        self.temp.set_data(data.index,data.temp)
        self.target_temp.set_data(data.index,data.target)

        # update fugacity plot
        self.desired_fug.set_data(data.index,data.fugacity)
        self.actual_fug.set_data(data.index,data.actual_fugacity)

        # update voltage
        self.volt.set_data(data.index,data.voltage)

        # update gas
        self.co2.set_data(data.index,data.co2)
        self.h2.set_data(data.index,data.h2)
        self.co.set_data(data.index,data.co)

        # #recalculate all axes limits
        # for ax in self.ax.values():
        #     ax = format_time_axis(ax)

        self.fig.autofmt_xdate()
        self.relim_all()
        self.draw()

    def temperature(self, ax):
        ax = format_time_axis(ax)

        self.target_temp, = ax.step(*self.x(), 'y', linestyle='--', label='Target')
        self.temp, = ax.plot(*self.x(),'.', label='Temperature')
        ax.set_ylabel(r'$Temperature [\circ C]$')
        ax.tick_params(direction='in',labelbottom=False)
        ax.legend()
        return ax

    def fugacity(self, ax):
        ax = format_time_axis(ax)
        self.desired_fug, = ax.plot(*self.x(),'--', label='Target')
        self.actual_fug, = ax.plot(*self.x(),'.', label='Fugacity')
        ax.set_ylabel('log fo2p [Pascals]')
        ax.tick_params(direction='in',labelbottom=False)
        ax.legend()
        return ax

    def voltage(self, ax):
        ax = format_time_axis(ax)
        self.volt, = ax.plot(*self.x(),'.', label='Voltage')
        ax.set_ylabel('Voltage [mV]')
        ax.tick_params(direction='in')
        # ax.set_xlim(left=0)
        # ax.set_xlabel('Time Elapsed [hours]')
        return ax

    def gas(self, ax):
        ax = format_time_axis(ax)
        self.co2, = ax.plot(*self.x(), label='CO2')
        self.h2, = ax.plot(*self.x(), label='H2')
        self.co, = ax.plot(*self.x(), label='CO')
        ax.tick_params(direction='in', labelbottom=False)
        ax.set_ylabel('Mass Flow [SCCM]')
        ax.set_ylim(bottom=0)
        ax.legend()
        return ax

    def conductivity(self,ax):
        """Plots conductivity versus time"""
        ax = format_time_axis(ax)
        self.conductivity, = ax.plot(*self.x(),'.')

        # ax.set_ylabel('Conductivity [S]')
        ax.set_ylabel('Conductivity [S/m]')
        ax.tick_params(direction='in', labelbottom=False)
        return ax

    def x(self):
        return pd.Timestamp(0), 0

    def draw(self):
        self.fig.canvas.draw()
        self.fig.canvas.flush_events() 

    def relim_all(self):
        for ax in self.ax.values():
            ax.relim()
            ax.autoscale_view()

class LivePlot2():

    def __init__(self, freq):
        self.freq = freq

        self.fig = plt.figure('Live Plot 2')
        self.ax = {
            'cole': self.cole(),
            'bode': self.bode(),
            'arrhenius': self.arrhenius(),
            'fugacity': self.fugacity(),
            }

        self.fig.tight_layout()
        self.draw()

    # def update_bottom(self, z, theta):

    #     Re, Im = processing.get_Re_Im(z, theta)

    #     # update cole plot
    #     self.cole.set_data(Re/1000, Im/1000)


    #     # update bode plot
    #     self.bode_z.set_data(self.freq[:len(z)], z)
    #     self.bode_theta.set_data(self.freq[:len(z)], np.degrees(np.abs(theta)))

    #     #recalculate all axes limits
    #     for ax in [self.ax['cole'], *self.ax['bode']]:
    #         ax.relim()
    #         ax.autoscale_view()

    #     self.draw()

    def update(self, data, area, thickness,freq=2000):
        # recalls the figure in case it was closed
        # self.fig = plt.figure('Live Plot 1')
        data = processing.process_data(data, area, thickness)

        z, theta = data.z[-1], data.theta[-1]
        Re, Im = processing.get_Re_Im(z, theta)
        # update cole plot
        self.cole.set_data(Re/1000, Im/1000)

        # update bode plot
        self.bode_z.set_data(self.freq[:len(z)], z)
        self.bode_theta.set_data(self.freq[:len(z)], np.degrees(np.abs(theta)))


        # get impedance at a particular freq for the entire dataset
        Re,_,freq = impedance_at(data,freq)
        conductivity = np.log10((1/Re)*(area / thickness))

        self.arrhenius.set_data(10000/data.kelvin, conductivity)
        self.ax['arrhenius'].add_artist(AnchoredText('@{} Hz'.format(freq), loc=1))

        self.fugacity.set_data(data.fugacity,conductivity)

        for ax in [self.ax['arrhenius'], self.ax['fugacity'],self.ax['cole'], *self.ax['bode']]:
            ax.relim()
            ax.autoscale_view()

        self.draw()

    # def draw_target_fugacity(self,target_buffer, temp_range):
    #     temp_list = np.linspace(*temp_range,100)
    #     fug = [processing.fo2_buffer(temp, target_buffer) for temp in temp_list] 
    #     self.ax['fugacity'].plot(1000/temp_list, fug, '--')

    def cole(self):
        ax = self.fig.add_subplot(223)
        self.cole, = ax.plot([], [],'bo')
        # cb = self.fig.colorbar(self.cole, ax=ax)
        # cb.set_label('Frequency')

        ax.axis('square')
        ax.set_xlim(left=0, right=1200)
        ax.set_ylim(bottom=0, top=1200)
        ax.set_ylabel(r'$-Im(Z) [{}]$'.format(K_OHM))
        ax.set_xlabel(r'$Re(Z) [{}]$'.format(K_OHM))
        ax.ticklabel_format(style='sci', scilimits=(-3, 4), axis='both')
        # ax.set_title('Cole-Cole')
        ax.legend()


        # cb = fig.colorbar(p, ax=ax, orientation="horizontal")



        # ax.axis('equal')
        # ax.set_ylabel(r'$-Im(Z) [k\Omega]$')
        # ax.set_xlabel(r'$Re(Z) [k\Omega]$')
        # ax.ticklabel_format(style='sci', scilimits=(-3, 4), axis='both')
        return ax

    def bode(self):
        ax1 = self.fig.add_subplot(224)
        color = 'tab:red'

        self.bode_z, = ax1.semilogx([], [], '.',color=color)
        ax1.set_ylabel(r'$Re(Z) [k\Omega]$', color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.set_xlabel('Frequency [Hz]')
        ax1.set_xlim(left=0, right=self.freq.max())
        

        ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
        color = 'tab:blue'
        self.bode_theta, = ax2.semilogx([], [], '.',color=color)
        ax2.set_ylabel('Phase Angle [degrees]', color=color)  # we already handled the x-label with ax1
        ax2.set_ylim(bottom=0, top=100)
        ax2.tick_params(axis='y', labelcolor=color)
        return [ax1, ax2]

    def fugacity(self):
        ax = self.fig.add_subplot(222)

        self.fugacity, = ax.plot([],[],'.')

        ax.set_ylabel('Conductivity [S/m]')
        ax.set_xlabel('Fugacity [log Pa]')
        ax.tick_params(direction='in')
        return ax

    def arrhenius(self):
        """Plots inverse temperature versus conductivity"""
        ax = self.fig.add_subplot(221)
        self.arrhenius,  = ax.plot([],[],'rx')

        ax.set_ylabel('Conductivity [S/m]')
        ax.set_xlabel('10000/Temperature [K]')

        secax = ax.secondary_xaxis('top', functions=(inverseK2celsius, celsius2inverseK))
        secax.set_xlabel(r'$Temperature [^\circ C]$')
        ax.tick_params(direction='in')

        return ax

    def draw(self):
        self.fig.canvas.draw()
        self.fig.canvas.flush_events() 

if __name__ == '__main__':
    z = [1.20E+06, 1.38E+05, 5.44E+04, 9.31E+03, 1.16E+03]
    theta = [-1.40E+00, -1.13E+00, -8.10E-01, -1.41E+00, -1.54E+00]
    freq = [1.59E+02, 1.59E+03, 1.59E+04, 1.59E+05, 1.59E+06]
    # convert z and theta to real and imaginary components
    Re, Im = get_Re_Im(z, theta)
    plt.scatter(Re, Im, c=freq, norm=colors.LogNorm())
    plt.show()
    # print(_calculate_conductivity(z,theta))
