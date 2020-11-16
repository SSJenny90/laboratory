#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import time
import statsmodels.api as sm
from functools import wraps
from cycler import cycler
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from laboratory import config, processing, modelling
from laboratory.processing import Sample
from matplotlib.offsetbox import AnchoredText
import matplotlib.dates as mdates
from matplotlib.pyplot import cm
from impedance import preprocessing as pp
from datetime import datetime as dt
from impedance.models.circuits import fitting
plt.style.use('ggplot')
plt.ion()
color_cycle = cycler(color=cm.tab20(np.linspace(0,1,20)))

K_OHM = r'k\Omega'
degC = r'$^\degree$C'
CONDUCTIVITY = r'$Conductivity~[S/m]$'
THERMOPOWER = r'$Thermopower~[\mu V/K]$'
TEMP_C = r'$Temperature~[\degree C]$'
TEMP_K = r'$Temperature~[\degree K]$'
FUGACITY = r'$fo2p~[log Pa]$'
RESISTIVITY = r'$Resistivity [\omega m^-1]$'

def plot(func):
    @wraps(func)
    def wrapper(data,*args,**kwargs):
        if isinstance(data, Sample):
            sample = data
            data = sample.data
        else:
            sample=None

        if not kwargs.get('ax'):
            _, ax = plt.subplots()
            # _, ax = plt.subplots(subplot_kw=kwargs)
            kwargs['ax'] = ax

        return func(data, *args,**kwargs)
    return wrapper

def thermopower_only(data):
    return data[data.z.isnull()]

def conductivity_only(data):
    return data[data.z.notnull()]

def index_temp(T, Tx):
    # returns the index of T nearest to the specified temp Tx. For use in colecole plots
    index = np.abs(T - Tx).argmin()
    return [index, T.to_numpy().flat[index]]

def voltage(data, step=None, bars=False, time=[], kwargs={}):
    """Plots voltage versus time"""
    data = index_data(data,step,time)

    fig, ax = plt.subplots()

    # ax.plot(data['voltage'], 'rx')
    if bars:
        ax.errorbar(data.index, data.voltage, yerr=data.volt_stderr,fmt='.')
    # else:
    p = ax.scatter(data.index, data.voltage, c=data.temp)
    cb = fig.colorbar(p, ax=ax)
    cb.set_label('Temperature [degC]')
        # ax.plot(data.index, data.voltage,'.')
    ax = format_time_axis(ax)
    ax.set_ylabel('Voltage [microV]')
    ax.tick_params(direction='in')
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

    if ax is None:
        fig, ax = plt.subplots()

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

    ax.plot(data.index,np.log10(conductivity),fmt)

    ax.set_ylabel('Log10 Conductivity [S/m]')

    ax.tick_params(direction='in')

def fugacity_target(data,ax=None, **kwargs):
    if ax is None:
        fig, ax = plt.subplots()

    ax.step(data.time, data['offset'], label='fo2 buffer',**kwargs)
    ax.set_ylabel(data['buffer'].unique()[0] + ' +/- ')

    return ax

@plot
def temperature(data, ax=None, **kwargs):
    """Plots furnace indicated and target temperature, thermocouple temperature and thermistor data versus time elapsed. A dictionary of key word arguments may be passed through to customize this plot"""

    ax.plot(data.time, data['temp'], label='Sample temperature',**kwargs)

    ax = format_time_axis(ax)
    ax.set_ylabel(r'$Temperature [\circ C]$')

    return ax


# BASE LEVEL PLOTS
@plot
def cole(data, freq, temp, freq_min=200, freq_max=None, fit=False, ax=None, **kwargs):
    """Creates a Cole-Cole plot (imaginary versus real impedance) at a given temperature. Finds the available data closest to the temperature specified by 'temp'. A linear least squares circle fit can be added by setting fit=True.

    :param temp: temperature in degrees C
    :type temp: float/int
    """
    data = conductivity_only(data)
    # for temp in temp_list:
    [index, Tval] = index_temp(data.temp,temp)
    f, z = pp.cropFrequencies(
        frequencies=np.array(freq), 
        Z=data.complex_z.iloc[index], 
        freqmin=freq_min,
        freqmax=freq_max)
    f, z = pp.ignoreBelowX(f, z)
    p = ax.scatter(np.real(z)/1000, np.abs(np.imag(z))/1000,**kwargs)

    if fit:
        model = data.model.iloc[index]
        predicted = model.predict(np.geomspace(0.001,2000000,100))      
        ax.plot(np.real(predicted)/1000, np.abs(np.imag(predicted))/1000) 
        ax.add_artist(AnchoredText(model.circuit, loc=2))


    if not ax.xaxis.get_label().get_text():
        ax.axis('equal')
        # ax.axis('square')
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.set_ylabel(r'$-Im(Z) [{}]$'.format(K_OHM))
        ax.set_xlabel(r'$Re(Z) [{}]$'.format(K_OHM))
        ax.ticklabel_format(style='sci', scilimits=(-3, 4), axis='both')
        ax.set_title('Cole-Cole')

    return ax

# @plot
def arrhenius_base(data, ax=None, **kwargs):
    """Plots inverse temperature versus conductivity"""
    ax.plot(10000/(data.temp+273), np.log10(data.conductivity),**kwargs)

    # prevents redrawing axes, only really required for the second axes because multiple calls will redraw over itself
    if not ax.xaxis.get_label().get_text():
        ax.set_ylabel(CONDUCTIVITY)
        ax.set_xlabel('10000/{}'.format(TEMP_K))
        secax = ax.secondary_xaxis('top', functions=(inverseK2celsius, celsius2inverseK))
        secax.set_xlabel(TEMP_C)
        ax.tick_params(direction='in')

    return ax

def conductivity_vs_fugacity(sample, no_hold=True, ax=None):
    """Plots inverse temperature versus conductivity"""
    if ax is None:
        fig, ax = plt.subplots(1)
    else:
        fig = ax.get_figure()

    data = sample.data
 
    data = data[data.hold_length == 0]

    p = ax.scatter(
        data.actual_fugacity, 
        data.conductivity,
        c=data.temp)

    ax.set_yscale('log')
    ax.set_xscale('log')

    cb = fig.colorbar(p, ax=ax)
    cb.set_label(TEMP_C)
    ax.set_ylabel(CONDUCTIVITY)
    ax.set_xlabel(FUGACITY)

    return ax

# @plot
def thermopower_vs_fugacity(sample, ax=None, **kwargs):
    if ax is None:
        fig, ax = plt.subplots(1)
    else:
        fig = ax.get_figure()

    data = sample.thermopower
    data = data[data.hold_length == 0]
    steps = data.step.unique()

    thermopower, fugacity, temp = [], [], []
    for step in steps:
        tmp = data.loc[data.step == step]
        result = sm.WLS(tmp.voltage, sm.add_constant(tmp.gradient), weights=1./(tmp.volt_stderr ** 2)).fit()
        slope = result.params['gradient']
        thermopower.append(-slope)
        fugacity.append(tmp.actual_fugacity.mean())
        temp.append(tmp.temp.mean())

    p = ax.scatter(
        fugacity, 
        thermopower,
        c=temp)

    ax.set_xscale('log')
    cb = fig.colorbar(p, ax=ax)
    cb.set_label(TEMP_C)
    ax.set_ylabel(THERMOPOWER)
    ax.set_xlabel(FUGACITY)
    return ax

@plot
def diffusion(data, ax=None,**kwargs):
    # get only the data where the experiment was required to hold
    data = data[data.hold_length > 0]
    grouped = data.groupby('step')

    for _, group in grouped:
        ax.plot(group.time_elapsed.dt.total_seconds()/60/60,group.conductivity,marker='.',linestyle='')
    
    ax.set_yscale('log')
    ax.set_ylabel(CONDUCTIVITY)
    ax.set_xlabel('Time elapsed [hours]')
    # ax.set_title('Conductivity during gas mix changes')
    return ax

@plot
def thermopower(data, ax=None,**kwargs):
    data = thermopower_only(data)
    steps = data.step.unique()
    colors = ['r','b','g','c','m','y','k']
    data['gradient'] = data.thermo_1 - data.thermo_2

    thermopower = []
    fugacity = []
    for step, c in zip(steps,color_cycle):
        tmp = data.loc[data.step == step]
        result = sm.WLS(tmp.voltage, sm.add_constant(tmp.gradient), weights=1./(tmp.volt_stderr ** 2)).fit()
        slope = result.params['gradient']
        thermopower.append(-slope)
        fugacity.append(tmp.actual_fugacity.mean())
        # ax = voltage_vs_gradient(tmp, ax=ax, **c)
    ax.plot(fugacity, thermopower,'rx')
    ax.set_xscale('log')

    return thermopower

@plot
def voltage_vs_gradient(data, ax=None, **kwargs):
    """Plots a voltage versus thermal gradient for a single suite of thermopower measurements. A weighted least squares fit is applied to the data to determine the slope for thermopower calculations.

    Args:
        data ([type]): [description]
        ax ([type], optional): [description]. Defaults to None.

    Returns:
        ax: The figure axis.
        model: The WLS model object.

    Notes
    -----
    Thermopower is determined by the slope of a weighted least squares fit to the data:

    .. math:: Q = -\lim_{\Delta T \to 0} \Delta V / \Delta T
    """
    data = thermopower_only(data)

    volt = data.voltage
    data['gradient'] = (data.thermo_1 - data.thermo_2)
    ax.errorbar(data.gradient, volt, yerr=data.volt_stderr, fmt='.',**kwargs)
    model = sm.WLS(volt, sm.add_constant(data.gradient), weights=1./(data.volt_stderr ** 2)).fit()
    ax.plot(data.gradient,model.predict(),**kwargs)
    ax.set_title('Thermopower @ {temp:.0f}{units} [{run}]'.format(
        temp=data.temp.mean(),
        units=degC,
        run=data['run'].unique()[0]))

    ax.set_ylabel('Voltage [micro V]')
    ax.set_xlabel(r'$Gradient [\circ C]$')
    # ax.legend()
    return ax, model

# HIGHER LEVEL PLOTS
@plot
def experiment_overview(data,ax=None):
    """Generatre a plot showing displaying mean temperature over time on one axis and the target fo2 buffer on the other axis.

    Args:
        sample (a Sample instance): [description]

    Returns:
        left_ax, right_ax: [description]
    """

    c = 'tab:red'
    ax = temperature(data,ax=ax, color=c)
    ax.set_ylabel(r'$Temperature [\circ C]$',color=c)
    ax.tick_params(axis='y', labelcolor=c)
    ax = format_time_axis(ax)

    c = 'tab:blue'
    ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis
    ax2 = fugacity_target(data,ax=ax2, color=c)
    ax2.tick_params(axis='y', labelcolor=c)
    ax2.set_ylabel(data['buffer'].unique()[0] + ' +/- ',color=c)
    ax2 = format_time_axis(ax)

    # fig.set_size_inches(10, 5)

    return ax, ax2

def cole_at_temp(sample, temp, ax=None, **kwargs):
    freq = sample.freq
    data = sample.data

    for i, run in enumerate(data.run.unique().dropna()):
        tmp = data[data.run == run]
        kwargs = dict(  
            data=tmp, 
            freq=freq, 
            temp=temp,
            fit=True,
            label='{}{:+}'.format(tmp.buffer.unique()[0],tmp.offset.mode()[0]))
        if i != 0 or ax is not None:
            kwargs.update(ax=ax)
        ax = cole(**kwargs)

    ax.set_title('{} @ {}{}'.format(
        sample.name.title(),
        temp,
        degC))
    ax.legend()
    return ax

def cole_at_run(sample, run, temp_list, ax=None, **kwargs):
    """Creates a Cole-cole plot for a given temperature run at the temperatures specified in temp_list.

    Args:
        sample (Sample): the sample to be plotted
        run (int): An integer number specifying the temperature run to plot from.           
        temp_list (list): A list of temperatures from which to plot and model impedance spectra
        ax (pyplot.Axes, optional): A pyplot figure axes object. If none, an axes will be created automatically. Defaults to None.

    Returns:
        ax: The figure axes
    """
    freq = sample.freq
    data = sample.run(run)

    for i, temp in enumerate(temp_list):
        kwargs = dict(  
            data=data, 
            freq=freq, 
            temp=temp,
            fit=True,
            label='{} {}'.format(temp,degC))
        if i != 0 or ax is not None:
            kwargs.update(ax=ax)
        ax = cole(**kwargs)
         
    buffer = '{}{:+}'.format(data.buffer.unique()[0],data.offset.mode()[0])
    ax.set_title('{} - {} [{}]'.format(
        sample.name.title(),
        data.run.unique()[0],
        buffer))
    ax.legend()
    return ax

@plot
def thermopower_base(data, ax=None):
    """Plots each temperature cycle for a given experiment on an arrhenius plot using different colours. Uses different symbols for heating and cooling to highlight possible sample alteration during a temperature cycle.

    ::note
        I don't believe this is actually hysteresis but can't be arsed finding the proper term.

    Args:
        sample (processing.Sample): a given sample

    Returns:
        [type]: [description]
    """
    steps = data.step.unique()
    colors = ['r','b','g','c','m','y','k']

    for step, c in zip(steps,color_cycle):
        print(c)

        tmp = data.loc[data.step == step]
        ax, _ = voltage_vs_gradient(tmp, ax=ax, **c)
        # print(model.summary())

    # ax.set_title('Thermopower @ {temp:.0f}{units} [{run}]'.format(
    #     temp=data.temp.mean(),
    #     units=degC,
    #     run=data['run'].unique()[0]))

    ax.set_ylabel('Voltage [micro V]')
    ax.set_xlabel(r'$Gradient [\circ C]$')
    # ax.legend()
    return ax

@plot
def arrhenius(data, cycle='both', ax=None):
    """Plots each temperature cycle for a given experiment on an arrhenius plot using different colours. Uses different symbols for heating and cooling to highlight possible sample alteration during a temperature cycle.

    ::note
        I don't believe this is actually hysteresis but can't be arsed finding the proper term.

    Args:
        sample (processing.Sample): a given sample

    Returns:
        [type]: [description]
    """
    data = conductivity_only(data)
    data = data[data.hold_length == 0]
    for ind, c in zip(data['run'].unique(),color_cycle):
        run = data.loc[data.run == ind]
        mean = int(np.mean([run.step.max(),run.step.min()]))

        if cycle in ['both','increasing']:
            arrhenius_base(run.loc[run.step <= mean], 
                ax=ax, 
                **c, 
                marker='.',
                label='{} increasing'.format(ind))
        if cycle in ['both','decreasing']:
            arrhenius_base(run.loc[run.step > mean], 
                ax=ax, 
                **c, 
                marker='x',
                label='{} decreasing'.format(ind))

    ax.legend()
    return ax


# LAB LEVEL PLOTS
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

def bode(z, theta, freq=None):
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

def fugacity_accuracy(sample):
    fig, ax = plt.subplots()

    data = sample.data

    actual_ratio = data.co2 / data.co

    ax.plot(data.ratio - actual_ratio,'rx')

    return ax

def test(sample):
    print('Hello')

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
