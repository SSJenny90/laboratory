import pandas as pd
import numpy as np
from scipy import optimize
from laboratory import config, modelling
from impedance import preprocessing
# from impedance.models.circuits
from impedance import visualization
import math 
import os, glob, json


class Sample():
    area = None
    thickness = None

    def __init__(self, project_folder):
        self.directory = project_folder

        # saves the info from sample.json onto the class instance
        self.get_sample_info()

        self.area_m = self.area * 1e-6
        self.thickness_m = self.thickness * 1e-3
        self.geo_factor = self.area_m / self.thickness_m

        # saves control_file.csv as a dataframe on the class instance
        self.control_file = self.get_control_file()

        # loads the collected data for the given sample
        self.data = self.load_data()
        
    def __str__(self):
        return ',\n'.join(str(dict(
            directory = self.directory,
            name = self.name,
            area = '{} mm^2'.format(self.area),
            thickness = '{} mm'.format(self.thickness),
            freq_range = '{}-{}'.format(self.freq[0],self.freq[-1]),
            thermopower = not self.thermopower.empty,
            conductivity = not self.conductivity.empty,
        )).split(','))

    @property
    def thermopower(self):
        return self.data[self.data.z.isnull()]

    @property
    def conductivity(self):
        return self.data[self.data.z.notnull()]

    def run(self, run_number):
        return self.data[self.data.run == 'Run {}'.format(run_number)]

    def step(self, step_number):
        return self.data[self.data.step == step_number]

    def model_conductivity(self, 
            guess = [1e+5, 1e-10, 5e+6, 1e-10],
            circuit = 'p(R1,C1)-p(R2,C2)',
            ignore_below = 200,        
            ):
        result = []
        for _, row in self.data.iterrows():
            if isinstance(row.complex_z, np.ndarray):
                result.append(modelling.model_conductivity(
                    freq = self.freq,
                    complex_z = row.complex_z,
                    cutoff = ignore_below,
                    circuit=circuit,
                    guess=guess
                    ))
            else:
                result.append([np.nan,np.nan,np.nan])

        self.data['model'] = [r[0] for r in result]
        self.data['resistance'] = [r[1] for r in result]
        self.data['model_rmse'] = [r[2] for r in result]
        self.data['conductivity'] = self.thickness_m / (self.data['resistance'] * self.area_m)
        # self.data['conductivity_old'] = 1./self.data['resistance'] * self.geo_factor

    def get_sample_info(self):
        with open(os.path.join(self.directory, 'sample.json')) as f:
            sample = json.load(f)
        for k,v in sample.items():
            setattr(self,k,v)

    def get_control_file(self):
        return pd.read_csv(os.path.join(self.directory, 'control_file.csv'))

    def load_data(self):
        """loads a previous experiment for processing and analysis

        :param project_folder: name of experiment
        :type project_folder: str
        """
        data = pd.read_pickle(glob.glob(os.path.join(self.directory, '*.pkl'))[0])     

        # load sample.json and send sample specs to process data function
        return self.process_data(data)

    def process_data(self, data, drop_prep=True):
        data['time'] = data.index
        data['time_elapsed'] = data.time-data.time[0]

        tdelta = []
        for step in data.step.unique():
            tmp = data[data.step == step]
            tdelta.append(tmp.time-tmp.time.iloc[0])
        
        data['time_from_step'] = pd.concat(tdelta)          
        data = pd.merge(data,self.control_file,on='step')
        
        data['temp'] = data[['thermo_1','thermo_2']].mean(axis=1)
        data['kelvin'] = data.temp+273.18
        data['gradient'] = data.thermo_1 - data.thermo_2
        data['log10_fugacity'] = data.apply(lambda x: actual_fugacity(x), axis=1)
        data['actual_fugacity'] = 10**data.log10_fugacity
        data['complex_z'] = data.apply(lambda x: to_complex_z(x), axis=1)
        data['type'] = np.where(data.z.notnull(), 'cond','thermo')
        if drop_prep:
            data = data.loc[data.step.between(0,data.step.max()-1)].copy()

        # compute index for each temperature run
        # find each row of control file where hold length is greater than 0, this will be our slice points for seperating temperature runs
        hold_index = list(self.control_file.index[self.control_file.hold_length > 0])
        labels = ['Run {}'.format(i+1) for i,_ in enumerate(hold_index)]
        data['run'] = pd.cut(data.loc[:,'step'],list(hold_index) + [float('Inf')], labels=labels)


        return data

def parabola(x, a, b, c):
    return np.multiply(a, np.square(x)) + np.multiply(b, x) + c

def fo2_buffer(temp, buffer, pressure=1.01325):
    def fug(buffer, temp, pressure):
        temp = temp+273  # convert Celsius to Kelvin

        if temp > buffer.get('Tc', False):
            a = buffer['a2']
        else:
            a = buffer['a1']

        if len(a) == 2:
            return a[0]/temp + a[1]
        elif len(a) == 3:
            return a[0]/temp + a[1] + a[2]*(pressure - 1e5)/temp

    BUFFERS = {
        'iw': {  # Iron-Wuestite - Myers and Eugster (1983)
            'a1': [-27538.2, 11.753]
        },
        'qfm': {  # Quartz-Fayalite-Magnetite - Myers and Eugster (1983)
            'a1': [-27271.3, 16.636],        # 298 to 848 K
            'a2': [-24441.9, 13.296],       # 848 to 1413 K
            'Tc': 848,  # K
        },
        'wm': { # O'Neill (1988)
            'a1': [-32356.6, 17.560]
        },
        'mh': { # Myers and Eugster (1983)
            'a1': [-25839.1, 20.581],        # 298 to 848 K
            'a2': [-23847.6, 18.486],       # 848 to 1413 K
            'Tc': 943,  # K
        },
        'qif': { # Myers and Eugster (1983)
            'a1': [-30146.6, 14.501],        # 298 to 848 K
            'a2': [-27517.5, 11.402],       # 848 to 1413 K
            'Tc': 848,  # K
        },
        'nno': { # a[0:1] from Myers and Gunter (1979) a[3] from Dai et al. (2008)
            'a1': [-24920, 14.352, 4.6e-7]
        },
        'mmo': { # a[3] from Dai et al. (2008)
            'a1': [-30650, 13.92, 5.4e-7]
        },
        'cco': {
            'a1': [-25070, 12.942]
        },
        'fsqm': {
            'a1': [-25865, 14.1456]
        },
        'fsqi': {
            'a1': [-29123, 12.4161]
        },
    }

    try:
        return fug(BUFFERS[buffer], temp, pressure)
    except KeyError:
        pass

def fugacity_co(fo2p, temp):
    """Calculates the ratio CO2/CO needed to maintain a constant oxygen fugacity at a given temperature.

    :param fo2p: desired oxygen fugacity (log Pa)
    :type fo2p: float, int

    :param temp: temperature (u'\N{DEGREE SIGN}C)
    :type temp: float, int

    :returns: CO2/CO ratio
    :rtype: float
    """

    a10 = 62.110326
    a11 = -2.144446e-2
    a12 = 4.720325e-7
    a13 = -4.5574288e-12
    a14 = -7.3430182e-15

    t0 = 273.18      # conversion C to K
    rgc = .00198726  # gas constant

    tk = temp + t0
    fo2 = 1.01325*(10**(fo2p-5))  # convert Pa to atm

    g1 = (((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10  # Gibbs free energy
    k1 = math.exp(-g1/rgc/tk)  # equilibrium constant

    CO = k1 - 3*k1*fo2 - 2*fo2**1.5
    CO2 = 2*k1*fo2 + fo2 + fo2**1.5 + fo2**0.5

    return CO2/CO

def fugacity_h2(fo2p, temp):
    """Calculates the ratio CO2/H2 needed to maintain a constant oxygen fugacity at a given temperature.

    :param fo2p: desired oxygen fugacity (log Pa)
    :type fo2p: float, int

    :param temp: temperature (u'\N{DEGREE SIGN}C)
    :type temp: float, int

    :returns: CO2/H2 ratio
    :rtype: float
    """
    a10 = 62.110326
    a11 = -2.144446e-2
    a12 = 4.720325e-7
    a13 = -4.5574288e-12
    a14 = -7.3430182e-15

    a30 = 55.025254
    a31 = -1.1212207e-2
    a32 = -2.0800406e-6
    a33 = 7.6484887e-10
    a34 = -1.1232833e-13

    t0 = 273.18      # conversion C to K
    rgc = .00198726  # gas constant

    tk = temp + t0
    fo2 = 1.01325*(10**(fo2p-5))  # convert Pa to atm

    g1 = (((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10  # Gibbs free energy
    g3 = (((a34*temp+a33)*temp+a32)*temp+a31)*temp+a30  # Gibbs free energy
    k1 = math.exp(-g1/rgc/tk)  # equilibrium constant
    k3 = math.exp(-g3/rgc/tk)  # equilibrium constant

    a = k1/(k1 + fo2**0.5)
    b = fo2**0.5/(k3 + fo2**0.5)

    H2 = a*(1-fo2) - 2*fo2
    CO2 = b*(1-fo2) + 2*fo2

    return CO2/H2

def actual_fugacity(data):
    try:
        if data.fo2_gas == 'co':
            ratio = data.co2/data.co
            func = fugacity_co
        else:
            ratio = data.co2/data.h2
            func = fugacity_h2
    except ZeroDivisionError:
        return np.nan
    
    fugacity_list = np.linspace(data.fugacity-.1,data.fugacity+.1,10)
    r = [func(f, data.temp) for f in fugacity_list]  

    popt2 = optimize.curve_fit(parabola, r, fugacity_list)[0]
    return parabola(ratio, *popt2)

def to_complex_z(data):
    if data.z and data.theta:
        real = np.multiply(data.z, np.cos(data.theta))
        imag = np.multiply(data.z, np.sin(data.theta))
        return real + 1j*imag

def load_data(project_folder):
    """loads a previous experiment for processing and analysis

    :param project_folder: name of experiment
    :type project_folder: str
    """
    data = pd.read_pickle(glob.glob(os.path.join(project_folder, '*.pkl'))[0])

    with open(os.path.join(project_folder, 'sample.json')) as f:
        sample = json.load(f)

    sample['name']

    # load sample.json and send sample specs to process data function
    return process_data(data, sample['area'], sample['thickness'])

def process_data(data, sample_area, sample_thickness):
    if isinstance(data, list):
        data = pd.DataFrame(data)
    
    if 'time' in data.keys():
        data.set_index('time', inplace=True)

        if data.shape[0] > 1:
            data['time_elapsed'] = data.index - data.index[0]
        else:
            data['time_elapsed'] = pd.Timedelta(0)
        
    data['temp'] = data[['thermo_1','thermo_2']].mean(axis=1)
    data['kelvin'] = data.temp+273.18
    data['gradient'] = data.thermo_1 - data.thermo_2
    data['actual_fugacity'] = data.apply(lambda x: actual_fugacity(x), axis=1)
    data['complex_z'] = data.apply(lambda x: to_complex_z(x), axis=1)
    # data['resistance'] = data.apply(lambda x: fit_impedance(x,offset=5), axis=1)

    # if sample_area and sample_thickness:
    #     area = sample_area * 10 ** -6
    #     thickness = sample_thickness * 10 ** -3
    #     data['resistivity'] = (area / thickness) * data.resistance
    #     data['conductivity'] = 1/data.resistivity

    # thickness = config.SAMPLE_THICKNESS * 10 ** -3
    # if not config.SAMPLE_AREA:
    #     radius = (config.SAMPLE_DIAMETER/2) * 10 ** -3
    #     area = np.pi * radius**2
    # else:
    #     area = config.SAMPLE_AREA * 10 ** -6

    # data.geometric_factor = area/thickness
    # data['actual_fugacity'] = data.apply(lambda x: actual_fugacity(x), axis=1)
    # data['resistance'] = data.apply(lambda x: fit_impedance(x,offset=5), axis=1)
    # data['resistivity'] = data.geometric_factor * data.resistance
    # data['conductivity'] = 1/data.resistivity
    return data
