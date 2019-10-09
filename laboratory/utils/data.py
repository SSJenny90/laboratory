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

def dt_to_hours(dtlist):
    return [(t-dtlist[0]).total_seconds()/60/60 for t in dtlist]

def process_data(data):

    data['time_elapsed'] = dt_to_hours(data['time'])

    # settings = {}
    # for key in ['freq','file_name','time','step_time']:
    #     settings[key] = data[key]
    #     del data[key]

    # data = pd.DataFrame(data)
    # data['time']['actual'] = settings['time']
    # data['time']['elapsed'] = dt_to_hours(settings['time'])

    return data


def load_data(filename):
    if filename.endswith('.txt'):
         return process_data(_load_text('laboratory/datafiles/' + filename))
    elif filename.endswith('.pkl'):
         return process_data(_load_pkl('laboratory/datafiles/' + filename))
    else:
        raise ValueError('Unsupported filetype! Must be .txt or .pkl')

def _load_text(filename):
    """Parses a text file and stores the data in the Lab.Data object

    :param filename: name of the file to be parsed
    :type filename: str
    """

    def append_data(data_type,keys,vals):
        if data_type != 'lcr':
            vals = [float(v) for v in vals]
            
        for key, val in zip(keys,vals):
            data[data_type][key].append(val)

    data = data_dict()
    data['filename'] = filename

    with open(filename,'r') as f:
        datafile = f.readlines()

        Z,theta = [],[]
        for line in datafile:

            if line.startswith('frequencies'):
                line = re.findall(r'(?<=\[).*?(?=\])', line)[0].split(',')
                data['freq'] = np.array([float(f) for f in line])
                continue

            line = line.split()

            if not line: continue

            line_id = line[0]
            vals = line[1:]

            if line_id == 'D':       
                if len(vals) == 2:
                    data['time'].append(dt.strptime('_'.join(vals),'%H:%M.%S_%d-%m-%Y'))
                else:
                    append_data('daq',['reference','thermo_1','thermo_2','voltage'],vals)

            # if line_id == 'Time'[0]:
            #     data['time'].append(dt.strptime('_'.join(vals),'%H:%M.%S_%d-%m-%Y'))

            # elif line_id == 'DAQ'[0]:
            #     append_data('daq',['reference','thermo_1','thermo_2','voltage'],vals)

            elif line_id == 'Step Time'[0]:
                data['step_time'].append(dt.strptime('_'.join(vals),'%H:%M.%S_%d-%m-%Y'))

            elif line_id == 'Gas'[0]:
                pass

            elif line_id == 'Furnace'[0]:
                append_data('furnace',['target','indicated'],vals)

            elif line_id == 'Motor'[0]:
                append_data('motor',['position'],vals)
            
            elif line_id == 'X':    # Fugacity
                append_data('fugacity',['fugacity','ratio','offset'],vals)

            elif line_id == 'Z':       #Impedance
                Z.append(float(vals[0]))
                theta.append(float(vals[1]))
                if len(Z) == len(data['freq']):
                    append_data('lcr',['z','theta'],[Z,theta])
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
