import pandas as pd
import numpy as np
from scipy import optimize
from laboratory import config
from impedance import preprocessing
# from impedance.models.circuits
from impedance import visualization
import math 

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

def circle_fit(x, y, ax):

    xc, yc, R = leastsq_circle(x, y)[:3]

    theta_fit = np.linspace(0, np.pi, 180)  # semi circle

    x_fit = xc + R*np.cos(theta_fit)
    y_fit = yc + R*np.sin(theta_fit)

    # plot circle as blue line
    ax.plot(x_fit, y_fit, 'b-', lw=1, label='lsq_fit')
    # plot center of circle as blue cross
    ax.plot([xc], [yc], 'bx', mec='y', mew=1, label='fit_center')

def leastsq_circle(x, y):
    # xc - the center of the circle on the x-coordinates
    # yc = center of the circle on the y coordinates
    # R = mean distance to center of circle

    def _calc_R(x, y, xc, yc):
        """ calculate the distance of each 2D points from the center (xc, yc) """
        return np.sqrt((x-xc)**2 + (y-yc)**2)

    def _f(c, x, y):
        """calculate the algebraic distance between the data points and the mean circle centered at c=(xc, yc) """
        Ri = _calc_R(x, y, *c)
        return _calc_R(x, y, *c) - Ri.mean()

    # coordinates of the barycenter
    x_m = np.mean(x)
    y_m = np.mean(y)

    center_estimate = x_m, y_m
    center, ier = optimize.leastsq(_f, center_estimate, args=(x, y))
    xc, yc = center
    Ri = _calc_R(x, y, *center)  # distance to center for each point
    R = Ri.mean()  # mean representing radius of the circle
    residu = np.sum((Ri - R)**2)
    return xc, yc, R, residu

def get_Re_Im(Z, theta):
    Re = np.multiply(Z, np.cos(theta))
    Im = np.absolute(np.multiply(Z, np.sin(theta)))
    return Re, Im

def fit_impedance(data, offset=0, method='lsq'):
    Z = np.array(data.z)
    theta = np.array(data.theta)

    if method == 'lsq':
        Re, Im = get_Re_Im(Z, theta)
        # calculate radius from least squares circle fit
        radius = leastsq_circle(Re[offset:], Im[offset:])[2]
        return 2*radius
    else:
        Re = np.flipud(np.multiply(Z, np.cos(theta)))
        Im = np.flipud(np.multiply(Z, np.sin(theta)))

        i = np.argmax(np.sign(np.diff(Im[20:])) <=0 )

        # i = 20
        # for i in range(i, len(Im)-1):
        #     if Im[i+1] - Im[i] > Im[i] - Im[i-1]:
        #         break

        # if not i:
        #     i = len(Im)
        # i = len(Re)
        A = Re[:i]*2
        # print(A)
        r = np.dot(A, A)**-1 * np.dot(A, (Re[:i]**2 + Im[:i]**2))
        # print(r)
        diameter = 2*r

        return diameter, i+20

def calculate_resistivity(data):
    """Calculates the resistivity of the sample from the resistance and sample dimensions supplied in config.py"""

    Z = data.z
    theta = data.theta

    # convert z and theta to real and imaginary components
    Re, Im = get_Re_Im(Z, theta)

    # calculate radius from least squares circle fit
    radius = leastsq_circle(Re, Im)[2]
    resistance = 2*radius

    # resistance = impedance_fit(Z, theta) 
    # print('R =',resistance)
    thickness = config.SAMPLE_THICKNESS * 10 ** -3
    # print('L =', thickness)
    radius = (config.SAMPLE_DIAMETER/2) * 10 ** -3
    # area = np.pi * radius**2
    area = 97.686 * 10 ** -6
    # print('A =',area)

    return (area / thickness) * resistance

def actual_fugacity(data):
    ratio = data.co2/data.co
    fugacity_list = np.linspace(data.fugacity-.1,data.fugacity+.1,10)
    r = [fugacity_co(f, data.temp) for f in fugacity_list]   
    popt2 = optimize.curve_fit(parabola, r, fugacity_list)[0]
    return parabola(ratio, *popt2)

def process_data(data):
    if isinstance(data, list):
        data = pd.DataFrame(data)
    if data.shape[0] > 1:
        # print(data.time.head())
        data['time_elapsed'] = data.index - data.index[0]
    else:
        data['time_elapsed'] = pd.Timedelta(0)
        
    # data.set_index('time_elapsed', inplace=True)
    # data.set_index('time', inplace=True)
    
    data['temp'] = data[['thermo_1','thermo_2']].mean(axis=1)
    data['kelvin'] = data.temp+273.18

    thickness = config.SAMPLE_THICKNESS * 10 ** -3
    if not config.SAMPLE_AREA:
        radius = (config.SAMPLE_DIAMETER/2) * 10 ** -3
        area = np.pi * radius**2
    else:
        area = config.SAMPLE_AREA * 10 ** -6

    data.geometric_factor = area/thickness
    data['actual_fugacity'] = data.apply(lambda x: actual_fugacity(x), axis=1)
    data['resistance'] = data.apply(lambda x: fit_impedance(x,offset=5), axis=1)
    data['resistivity'] = data.geometric_factor * data.resistance
    data['conductivity'] = 1/data.resistivity
    return data
    # data['resistivity'] = data.apply(lambda x: calculate_resistivity(x), axis=1)