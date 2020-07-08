import os
import pickle
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
from laboratory import config, laboratory
from laboratory.utils import loggers
from laboratory.utils.exceptions import CalibrationError
from scipy.optimize import curve_fit

logger = loggers.lab(__name__)


def stage_temperature_profile(temperature=500, step=.1, mins_per_step=10, start_position=4000, end_position=6000):
    """Records the temperature of both electrodes (te1 and te2) as the sample is moved from one end of the stage to the other. Used to find the center of the stage or the xpos of a desired temperature gradient when taking thermopower measurements.
    """
    lab = laboratory.Laboratory()
    logger.info(
        'Beginning calibration of stage temperature profile at {} degrees.\n'.format(temperature))

    total_steps = (end_position-start_position)/(step*200)

    wait_time = timedelta(hours=8)

    logger.info('Estimated completion time: {}\n'.format(datetime.strftime(datetime.now(
    ) + timedelta(minutes=total_steps*mins_per_step) + wait_time, '%H:%M %A, %b %d')))
    lab.furnace.timer_status('reset')
    # set the furnace to the desired temperature
    lab.furnace.setpoint_1(temperature)
    lab.furnace.display(2)  # setdisplay to show time remaining
    # send the stage to the requested start position
    lab.stage.go_to(start_position)

    # hold here for an hour to let the temperature equilibrate
    time.sleep(wait_time.seconds)

    # the furnace will revert to it's default temp if the timer expires
    # set timer duration to 3 x step length
    lab.furnace.timer_duration(seconds=3*mins_per_step*60)

    data = {'xpos': [], 'thermo_1': [], 'thermo_2': []}

    xpos = start_position
    while xpos < end_position:
        lab.furnace.reset_timer()

        # save the stage position and temperature data
        data['xpos'].append(xpos)
        T = lab.daq.get_temp()
        data['thermo_1'].append(T['thermo_1'])
        data['thermo_2'].append(T['thermo_2'])

        print(xpos, T['thermo_1'], T['thermo_2'])
        # move the stage and wait for the next cycle
        lab.stage.move(step)
        xpos = lab.stage.position
        time.sleep(mins_per_step*60)

    df = pd.DataFrame(data)
    df.to_pickle(os.path.join(config.CALIBRATION_DIR, 'furnace_profile.pkl'))
    lab.shut_down()
    # plot_temperature_profile(data)


def open_furnace_calibration():
    """TODO"""
    lab = laboratory.Laboratory()
    logger.info(
        'Beginning calibration of stage temperature profile at {} degrees.\n'.format(temperature))

    df = pd.DataFrame(data)
    df.to_pickle(os.path.join(config.CALIBRATION_DIR,
                              'open_furnace_calibration.pkl'))
    lab.shut_down()


def parabola(x, a, b, c):
    return np.multiply(a, np.square(x)) + np.multiply(b, x) + c


def plot_temperature_profile():

    data = pd.read_pickle(os.path.join(
        config.CALIBRATION_DIR, 'furnace_profile.pkl'))

    print(data)
    # print(data.head())

    fig = plt.figure()
    ax = fig.add_subplot(111)
    x = data['xpos']
    te1 = data['thermo_1']
    te2 = data['thermo_2']

    ax.plot(x, te1, 'bx', label='te1')
    popt = curve_fit(parabola, x, te1)[0]
    ax.plot(x, parabola(x, *popt), 'b-')

    ax.plot(x, te2, 'rx', label='te2')
    popt2 = curve_fit(parabola, x, te2)[0]
    ax.plot(x, parabola(x, *popt2), 'r-')

    plt.legend()
    plt.show()


def gradient_profile():
    calibration_file = os.path.join(config.CALIBRATION_DIR, 'furnace_profile.pkl')
    try:
        f = open(calibration_file, 'rb')  # Overwrites any existing file.
    except FileNotFoundError:
        logger.warning(
            'WARNING: The linear stage requires calibration in order to find the position where both thermocouples sit at the peak temperature.')
    else:
        data = pickle.load(f)
        f.close()
        return data.thermo_1 - data.thermo_2


def find_indicated(temperature):
    calibration_file = os.path.join(
        config.CALIBRATION_DIR, "open_furnace_correction.pkl")
    try:
        f = open(calibration_file, 'rb')
    except FileNotFoundError:
        raise CalibrationError(
            "Can't find the correct calibration file at {}.The program requires this calibration to reconcile target temperatures with actual temperatures at the sample.".format(calibration_file))
    else:
        data = pickle.load(f)
        f.close()

    popt = data['correction']
    return np.around(np.multiply(popt[0], np.square(temperature)) + np.multiply(popt[1], temperature) + popt[2], 2)


if __name__ == '__main__':
    furnace_profile()
