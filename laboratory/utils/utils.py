from laboratory.utils import loggers
logger = loggers.lab(__name__)
from laboratory import config
from pandas.api.types import is_numeric_dtype
import numpy as np
from datetime import datetime
import time
import sys

def check_controlfile(controlfile):
    """Checks to make sure the specified controlfile is a valid file that can be used by this program

    :param controlfile: a loaded control file
    :type controlfile: pd.DataFrame
    """
    # import pdb; pdb.set_trace()
    columns = set(list(controlfile.columns.values))
    exp_numeric = ['target_temp','hold_length','heat_rate','interval','offset']
    exp_str = ['buffer','fo2_gas']
    expected = set().union(exp_numeric, exp_str)

    #check if the headers in controlfile are what is expected
    if not columns == expected:
        if len(columns) > len(expected):   #if controlfile has an additional column
            dif = columns.difference(expected)
            logger.error('Found an unexpected additional column/s {} in the control file'.format(dif))
        else:       #if controlfile is missing an expected column
            dif = expected.difference(columns)
            logger.error('Could not find {} in the control file'.format(dif))
        logger.debug('    Expected to find {}'.format(expected))
        return False

    #if controlfile starts at the temperature of the furnace but was not intended to hold, it can get stuck in a loop. therefore the first value must be a 0. Only matters if no hold_length value was input into the first step
    if np.isnan(controlfile.hold_length[0]):
        controlfile.loc[0,'hold_length'] = 0

    #check that data types in numeric variables are correct
    for header in exp_numeric:
        if not is_numeric_dtype(controlfile[header]):
            logger.error('Encountered an unexpected data type in {} - must be numeric'.format(header))
            return False

    #check that buffer inputs are valid values
    buffer_types = ['qfm','fmq','fqm','iw','wm','mh','qif','nno','mmo','cco']
    for val in controlfile.buffer:
        if val not in buffer_types:
            logger.error("Found an unexpected buffer type:  '{}'".format(val))
            logger.debug('    Must be one of {}'.format(buffer_types))
            return False

    #check that fo2_gas inputs are valid values
    gas_types = ['h2','co']
    for val in controlfile.fo2_gas:
        if val not in gas_types:
            logger.error("Found an unexpected gas type:  '{}'".format(val))
            logger.debug('    Must be one of {}'.format(gas_types))
            return False

    return True

def find_indicated(temperature):
    #from calibration experiment
    data = config.OPEN_FURNACE_CORRECTION

    target = data['target']
    indicated = data['indicated']
    mean_temp = data['mean_temp']
    popt = data['correction']
    # popt = curve_fit(parabola, mean_temp[idx], indicated[idx])[0]

    return np.around(np.multiply(popt[0],np.square(temperature)) + np.multiply(popt[1],temperature) + popt[2],2)


    # furnace = np.array([400,500,600,700,800,900,1000])
    # daq = np.array([253.46,335.82,422.67,512,604.5,698.7,795.3])
    # A = np.vstack([daq,np.ones(len(daq))]).T
    # m,c = np.linalg.lstsq(A,furnace,rcond=None)[0]
    #
    # if default:
    #     #return a furnace value for a desired temperature
    #     return np.around(np.multiply(m,temperature)+c,2)
    # else:
    #     #return a daq value for given temperature
    #     return np.around(np.divide(temperature-c,m),2)

def count_down(start,interval,time_remaining=1):
    """Controls the count down until next measurement cycle

    :param interval: time in seconds remaining until next measurement
    :type interval: float/int
    """
    print('')
    while time_remaining > 0:
        time_remaining = int(interval*60+
        (start-datetime.now()).total_seconds())
        mins = int(time_remaining/60)
        seconds = time_remaining%60
        time.sleep(1)
        sys.stdout.write('\rNext measurement in... {:02}m {:02}s'.format(mins,seconds))
        sys.stdout.flush()
        if time_remaining < 1:
            sys.stdout.write('\r                                          \r'),
            sys.stdout.flush()

def break_measurement_cycle(step,indicated,cycle_start):
    """Checks whether the main measurements loop should be broken in order to proceed to the next  If temperature is increasing the loop will break once T-indicated exceeds the target temperature. If temperature is decreasing, the loop will break when T-indicated is within 5 degrees of the target. If temperature is holding, the loop will break when the hold time specified by hold_length is exceeded.

    :param step: the current measurement step
    :type step: pandas series object

    :param indicated: current indicated temperature on furnace
    :type indicated: float

    :param cycle_start: start time of the current step
    :type cycle_start: datetime object
    """

    # if step.hold_length == 0:
    #     return True
    time_elapsed = (datetime.now()-cycle_start).total_seconds()/60/60
    #if T is increasing, break when Tind exceeds target
    if step.target_temp >= step.previous_target and indicated >= step.target_temp:
        if time_elapsed >= step.hold_length:
            return True
    #if temp is decreasing, indicated rarely drops below the target - hence the + 5
    elif step.target_temp < step.previous_target and indicated < step.target_temp+5:
        if time_elapsed >= step.hold_length:
            return True

    # elif time_elapsed >= step.hold_length:
    #     return True
    return False

def print_df(df):

    print('Control File:\n')
    column_names = ['target_temp', 'hold_length', 'heat_rate', 'interval', 'buffer', 'offset', 'fo2_gas', 'est_total_mins']
    column_alias = ['Target [C]', 'Hold [hrs]', 'Heat rate [C/min]', 'Interval', 'Buffer', 'Offset', 'Gas', 'Est. mins']
    print(df.to_string(columns=column_names,header=column_alias,index=False))
    print(' ')

if __name__ == '__main__':
    m = Messages()
    print(m.delayed_start.format('0900'))
