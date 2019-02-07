#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 14 16:09:52 2018
@author: Sam
"""
import numpy as np
from scipy import optimize
import time
import math
from utils import *
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.offsetbox import AnchoredText

class LabPlots():
    """Contains an assortment of useful plots for visualising self.data"""
    def __init__(self,data):
        self.data = data
        self.t_elapsed = _datetime_to_hours(data.time[0],data.time)
        self.data.thermo.mean = np.average(np.array([data.thermo.te1,data.thermo.te2]),axis=0)
        # self._resistivity = _calculate_conductivity()

    # @property
    # def conductivity(self):
    #     return 1/self._resistivity

    # @property
    # def resistivity(self):
    #     return self._resistivity

    def voltage(self):
        """Plots voltage versus time"""
        fig = plt.figure('Voltage')
        ax = fig.add_subplot(111)

        ax.plot(self.t_elapsed,self.data.thermo.volt,'rx')

        ax.set_ylabel('Voltage [mV]')
        ax.tick_params(direction='in')
        ax.set_xlabel('Time Elapsed [hours]')

        plt.show()

    def cond_time(self):
        """Plots conductivity versus time"""
        return 'This plot is not working yet!'
        fig = plt.figure('Conductivity')
        ax = fig.add_subplot(111)

        ax.plot(self.t_elapsed,self.data.imp.cond,'rx')

        ax.set_ylabel('Conductivity [S]')
        ax.tick_params(direction='in')
        ax.set_xlabel('Time [min]')

        plt.show()

    def temperature(self):
        """Plots furnace indicated and target temperature, thermocouple temperature and thermistor self.data versus time elapsed"""
        thermo = self.data.thermo
        temp = self.data.temp

        fig = plt.figure('Temperature')
        ax = fig.add_subplot(111)

        ax.plot(self.t_elapsed,thermo.tref,'r-')
        ax.plot(self.t_elapsed,thermo.te1,'b.',label='Te1')
        ax.plot(self.t_elapsed,thermo.te2,'g.',label='Te2')
        ax.step(self.t_elapsed,temp.target,'y',linestyle='--',label='Target temperature')
        # ax.plot(self.t_elapsed,temp.indicated,'m.',label='Furnace indicated')

        ax.text(0,thermo.tref[0]+5,'Tref',color='red')
        ax.text(0,temp.target[0]+5,'Target',color='y')

        ax.set_ylabel(r'$Temperature [\circ C]$')
        ax.set_ylim(bottom=0)
        ax.set_xlabel('Time Elapsed [Hours]')
        ax.set_xlim(left=0)
        ax.tick_params(direction='in')
        fig.tight_layout()
        ax.legend()
        plt.show()

    def cole(self,temp_list,start=0,end=None,fit=False):
        """Creates a Cole-Cole plot (imaginary versus real impedance) at a given temperature. Finds the available self.data to the temperature specified by 'temp'. A linear least squares circle fit can be added by setting fit=True.

        :param temp: temperature in degrees C
        :type temp: float/int
        """
        fig = plt.figure('Cole-Cole plot')
        ax = fig.add_subplot(111)

        if not isinstance(temp_list,list): temp_list = [temp_list]

        for temp in temp_list:
            [index, Tval] = _get_index(np.array(self.data.thermo.te1),temp)
            Z = self.data.imp.Z[index][start:end]
            theta = self.data.imp.theta[index][start:end]
            Re,Im = _return_ReIm(Z,theta)

            p = ax.scatter(Re,Im,c=self.data.freq[start:end],norm=colors.LogNorm())

            ax.set_xlim(0,np.nanmax(Re))
            ax.set_ylim(bottom=0)
            if fit:
                self._circlefit(Re,Im,ax)
                ax.axis('scaled')
            else:
                ax.axis('equal')

        ax.set_ylabel('-Im(Z)')
        ax.set_xlabel('Re(Z)')
        ax.ticklabel_format(style='sci',scilimits=(-3,4),axis='both')

        atxt = AnchoredText('@ ' + str(Tval) + '$^\circ$ C',loc=2)
        ax.add_artist(atxt)

        cb = fig.colorbar(p,ax=ax,orientation="horizontal")
        cb.set_label('Frequency')
        cb.ax.invert_xaxis()

        plt.show()

    def gas(self):
        "Plots mass_flow self.data for all gases versus time elapsed"
        h2 = np.asarray(self.data.gas.h2.mass_flow)
        co2 = np.asarray(self.data.gas.co2.mass_flow)
        co_a = np.asarray(self.data.gas.co_a.mass_flow)
        co_b = np.asarray(self.data.gas.co_b.mass_flow)

        fig = plt.figure()
        ax = fig.add_subplot(111)

        ax.plot(self.t_elapsed,h2,'m-',label='H2')
        ax.plot(self.t_elapsed,co2,'b-',label='CO2')
        ax.plot(self.t_elapsed,np.add(co_a,co_b),'g-',label='CO_total')

        ax.set_ylabel('Gas concentrations [%]')
        ax.set_xlabel('Time elapsed [hours]')
        ax.tick_params(direction='in')
        ax.set_ylim(bottom=0)
        ax.legend()

        plt.show()

    def imp_diameter(self):
        """Plots the impedance diameter versus time_elapsed"""

        diameter = []
        for i,val in enumerate(self.data.imp.Z):
            z = self.data.imp.Z[i]
            theta = self.data.imp.theta[i]
            diameter.append(_impfit(z[1:],theta[1:]))

        fig = plt.figure()
        ax = fig.add_subplot(111)

        ax.plot(self.t_elapsed,diameter,'r.')

        ax.set_xlabel('Time Elapsed [hours]')
        ax.set_ylabel(r'$Diameter [\Omega$]')

        plt.show()

    def arrhenius(self):
        """Plots inverse temperature versus conductivity"""
        return 'This plot is not working yet!'
        thermo = self.data.thermo
        imp = self.data.imp

        fig = plt.figure('Arrhenius Diagram')
        ax = fig.add_subplot(111)

        ax.plot(thermo.mean+273.18,imp.conductivity,'b-',label='temp')

        ax.set_ylabel('Conductivity [S/m]')
        ax.set_xlabel('Temperature [1000/K]')
        ax.tick_params(direction='in')
        ax.invert_xaxis()
        fig.tight_layout()
        plt.show()

    def cond_fug(self):
        """Plots inverse temperature versus conductivity"""
        return 'This plot is not working yet!'
        imp = self.data.imp

        fig = plt.figure('Fugacity')
        ax = fig.add_subplot(111)

        ax.plot(self.data.fugacity,imp.conductivity,'b-',label='fugacity')

        ax.set_ylabel('Conductivity [S/m]')
        ax.set_xlabel('log10 Fugacity [Pa]')
        ax.tick_params(direction='in')
        ax.invert_xaxis()
        fig.tight_layout()
        plt.show()

def _impfit(Z,theta):

    Z = np.array(Z)
    theta = np.array(theta)

    x = np.multiply(Z,np.cos(theta))
    y = np.multiply(Z,np.sin(theta))

    x = np.flipud(x)
    y = np.flipud(y)

    i = 20
    for i in range(i, len(x)):
        if y[i] - y[i-1] > y[i-1] - y[i-2]:
            break

    i = i-1
    A = x[:i]*2
    r = np.dot(A,A)**-1 * np.dot(A,(x[:i]**2 + y[:i]**2))
    diameter = 2*r

    return diameter

def _datetime_to_hours(start,dtlist):
    return [(t-start).total_seconds()/60/60 for t in dtlist]

def _circlefit(Re,Im,ax):

    xc,yc,R,residu = _leastsq_circle(Re,Im)

    pi = np.pi
    theta_fit = np.linspace(0, pi, 180)   #semi circle

    x_fit = xc + R*np.cos(theta_fit)
    y_fit = yc + R*np.sin(theta_fit)

    ax.plot(x_fit, y_fit,'b-',lw=1,label='lsq_fit') #plot circle as blue line
    ax.plot([xc],[yc],'bx',mec='y',mew=1,label='fit_center')  #plot center of circle as blue cross

def _leastsq_circle(x,y):
    #xc - the center of the circle on the x-coordinates
    #yc = center of the circle on the y coordinates
    #R = mean distance to center of circle

    def _calc_R(x,y, xc, yc):
        """ calculate the distance of each 2D points from the center (xc, yc) """
        return np.sqrt((x-xc)**2 + (y-yc)**2)

    def _f(c, x, y):
        """calculate the algebraic distance between the self.data points and the mean circle centered at c=(xc, yc) """
        Ri = _calc_R(x, y, *c)
        return _calc_R(x, y, *c) - Ri.mean()

    # coordinates of the barycenter
    x_m = np.mean(x)
    y_m = np.mean(y)

    center_estimate = x_m, y_m
    center, ier = optimize.leastsq(_f, center_estimate, args=(x,y))
    xc, yc = center
    Ri = _calc_R(x, y, *center)    #distance to center for each point
    R = Ri.mean()    #mean representing radius of the circle
    residu = np.sum((Ri - R)**2)
    return xc, yc, R, residu

def _get_index(T,Tx):
    #returns the index of T nearest to the specified temp Tx. For use in colecole plots
    index = np.abs(T - Tx).argmin()
    return [index, T.flat[index]]

def _return_ReIm(Z,theta):
    Z = np.array(Z)
    theta = np.array(theta)

    Re = np.multiply(Z,np.cos(theta))
    Im = np.absolute(np.multiply(Z,np.sin(theta)))

    # Re,Im = [],[]
    # for zval,thetaval in zip(Z,theta):
    #     x = abs(zval*math.cos(thetaval))
    #     y = abs(zval*math.sin(thetaval))
    #     Re.append(x)
    #     Im.append(y)

    return Re,Im

def _calculate_conductivity(Z,theta):
    """
    conductivity = length / area * resistance
    """

    Re,Im = _return_ReIm(Z,theta)   #convert z and theta to real and imaginary components

    xc,yc,radius,residu = _leastsq_circle(Re,Im) #calculate radius from least squares circle fit

    resistance = 2*radius
    thickness = config.sample_thickness * 10 ** -3
    radius = (config.sample_diameter/2) * 10 ** -3
    area = np.pi * radius**2

    return thickness / area * resistance







if __name__ == '__main__':
    z = [1.20E+06,1.38E+05,5.44E+04,9.31E+03,1.16E+03]
    theta = [-1.40E+00,-1.13E+00,-8.10E-01,-1.41E+00,-1.54E+00]
    freq = [1.59E+02,1.59E+03,1.59E+04,1.59E+05,1.59E+06]
    Re,Im = _return_ReIm(z,theta)   #convert z and theta to real and imaginary components
    plt.scatter(Re,Im,c=freq,norm=colors.LogNorm())
    plt.show()
    # print(_calculate_conductivity(z,theta))
