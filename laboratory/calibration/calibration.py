from laboratory.utils import loggers
from laboratory.utils.data import Data, save_obj
from laboratory import config
import time
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import pickle
from scipy.optimize import curve_fit
import pandas as pd

logger = loggers.lab(__name__)

def stage_temperature_profile(self, filename, temperature=500, step=.1, mins_per_step=10, start_position=4000, end_position=6000):
    """Records the temperature of both electrodes (te1 and te2) as the sample is moved
    from one end of the stage to the other. Used to find the center of the stage or the xpos of a desired temperature gradient when taking thermopower measurements.
    """
    folder = 'calibration_files'
    if not os.path.exists(folder): os.mkdir(folder)

    logger.info('Beginning calibration of stage temperature profile at {} degrees.\n'.format(temperature))

    total_steps = (end_position-start_position)/(step*200)

    wait_time = 1   #in hours

    logger.info('Estimated completion time: {}\n'.format(datetime.strftime(datetime.now() + timedelta(minutes=total_steps*mins_per_step+wait_time*60),'%H:%M %A, %b %d')))

    self.furnace.setpoint_1(temperature)    #set the furnace to the desired temperature
    self.furnace.display(2) #setdisplay to show time remaining
    self.motor.position(start_position) #send the stage to the requested start position

    time.sleep(wait_time*60*60)   #hold here for an hour to let the temperature equilibrate

    data = Data()   #create a data object for storage

    #the furnace will revert to it's default temp if the timer expires
    #set timer duration to 3 x step length
    self.furnace.timer_duration(seconds=3*mins_per_step*60)

    xpos = start_position
    while xpos < end_position:
        self.furnace.reset_timer()

        #save the stage position to the data object
        data.xpos.append(xpos)

        #get temperature values from the DAQ and save
        vals = self.daq.get_temp()
        data.thermo = data.thermo.append({'tref':vals[0],'te1':vals[1],'te2':vals[2]},ignore_index=True)

        #move the stage
        self.motor.move(step)
        xpos = self.motor.position()

        #save the object and wait for the next step
        save_obj(data,os.path.join(folder,filename))
        time.sleep(mins_per_step*60)


    idx = np.argwhere(np.diff(np.sign(data.thermo.te1 - data.thermo.te2))).flatten()

    logger.info('Please update the config file with the following home_position: {}'.format(data.xpos[idx[0]]))

    plot_temperature_profile(data)
    #TODO save the data fits to the settings file for use in program

def parabola(x,a,b,c):
    return np.multiply(a,np.square(x)) + np.multiply(b,x) + c

def plot_temperature_profile(data):

    fig = plt.figure()
    ax = fig.add_subplot(111)
    x = data.xpos
    te1 = data.thermo.te1
    te2 = data.thermo.te2

    ax.plot(x,te1,'bx',label='te1')
    popt = curve_fit(parabola, x, te1)[0]
    ax.plot(x,parabola(x,*popt),'b-')

    ax.plot(x,te2,'rx',label='te2')
    popt2 = curve_fit(parabola, x, te2)[0]
    ax.plot(x,parabola(x,*popt2),'r-')

    plt.legend()
    plt.show()

def find_center(self):
    """TODO - Attempts to place the sample at the center of the heat source such that
    te1 = te2. untested.
    """
    self.daq.reset()
    self.daq.toggle_switch('thermo')
    self.daq._config_temp()

    while True:
        temp = self.daq.get_temp()

        if temp is None:
            self.logger.error('No temperature data collected')
        te1 = temp[1]
        te2 = temp[2]

        print(te1,te2)

        delta = abs(te1-te2)

        if delta < 0.1:
            print('Found center at' + self.motor.get_pos())
            break

        if te1 < te2:
            self.motor.move_mm(-0.05)
        elif te2 < te1:
            self.motor.move_mm(0.05)
        print(self.motor.get_pos())

        time.sleep(600)

def load_file(filename):
    """Loads a .pkl file

    :param filename: full path to file. must be a .pkl
    :type filename: str
    """
    if not filename.endswith('.pkl'):
        filename = filename + '.pkl'

    # for f in filenames:
    with open(filename, 'rb') as input:  # Overwrites any existing file.
        return pickle.load(input)

# def open_furnace_correction(data,temperature):
#
#     target = data.thermo.target
#     indicated = data.thermo.indicated
#     mean_temp = (data.thermo.te1 + data.thermo.te2) / 2
#
#     idx = np.where(np.roll(target,1)!=target)[0][1:]
#     popt = curve_fit(parabola, actual, indicated)[0]
#
#     temp_obj = {'target':target[idx], 'indicated':indicated, 'mean_temp':actual, 'correction':popt}
#
#     save_obj(temp_obj,'laboratory\\calibration\\open_furnace_correction')
#
#     return np.around(np.multiply(popt[0],np.square(temperature)) + np.multiply(popt[1],temperature) + popt[2],2)


def plot_open_furnace_correction():

    data = config.OPEN_FURNACE_CORRECTION
    indicated = data['indicated']
    actual = data['mean_temp']
    popt = data['correction']

    fig = plt.figure()
    ax = fig.add_subplot(121)
    ax.plot(indicated,indicated,'rx',label='Furnace indicated')
    ax.plot(indicated,actual,'gx',label='Actual sample temperature')
    ax.set_xlabel('Furnace indicated [C]')
    ax.legend()

    ax2 = fig.add_subplot(122)
    ax2.plot(actual,indicated,'rx')
    ax2.set_xlabel('Furnace indicated temperature [C]')
    ax2.set_ylabel('Actual sample temperature [C]')
    ax2.plot(actual,parabola(actual,*popt),'b-')

    ax2.set_xlim(50,1100)
    ax2.set_ylim(50,1100)
    plt.show()

if __name__ == '__main__':
    furnace_profile()
