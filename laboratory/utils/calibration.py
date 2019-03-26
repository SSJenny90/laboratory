from . import loggers
from .data import Data, save_obj
import time
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import pickle
# from laboratory import config

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
    logger.info('Please update the config file with the following home_position: {}'.format(data.xpos[idx[0]])

    plot_temperature_profile(data)
    #TODO save the data fits to the settings file for use in program

def plot_temperature_profile(data):

    from scipy.optimize import curve_fit

    def func(x,a,b,c):
        return np.multiply(a,np.square(x)) + np.multiply(b,x) + c

    fig = plt.figure()
    ax = fig.add_subplot(111)
    x = data.xpos
    te1 = data.thermo.te1
    te2 = data.thermo.te2


    ax.plot(x,te1,'bx',label='te1')
    popt = curve_fit(func, x, te1)[0]
    ax.plot(x,func(x,*popt),'b-')


    ax.plot(x,te2,'rx',label='te2')
    popt2 = curve_fit(func, x, te2)[0]
    ax.plot(x,func(x,*popt2),'r-')

    print(popt)


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


if __name__ == '__main__':
    furnace_profile()
