import numpy as np
import math
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def parabola(x, a, b, c):
    return np.multiply(a, np.square(x)) + np.multiply(b, x) + c

def fo2_buffer(temp, buffer, pressure=1.01325):
    def fug(buffer, temp, pressure):
        temp = temp+273  # convert Celsius to Kelvin

        a = buffer['a1']
        if buffer.get('Tc'):
            if temp > buffer['Tc']:
                a = buffer['a2']

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


if __name__ == '__main__':
    from time import sleep
    plt.ion()    

    fig, ax = plt.subplots(1)
    temps = np.linspace(200,1500,100)
    buffers = ['iw','qfm','wm','mh','qif','nno','mmo','cco']

    x, = ax.plot([], [], '--') # Returns a tuple of line objects, thus the comma
    ax.set_xlabel('something')
    for buffer in buffers:
        fug = [fo2_buffer(temp, buffer) for temp in temps] 
        x.set_data(1000/temps, fug)
        ax.set_ylim([-50,0])
        ax.set_xlim([0,5])
        fig.canvas.draw()
        fig.canvas.flush_events()
        sleep(.5)

    # plt.legend()
    # plt.show()

    # x = np.linspace(0, 6*np.pi, 100)
    # y = np.sin(x)

    # # You probably won't need this if you're embedding things in a tkinter plot...
    # plt.ion()

    # fig = plt.figure()
    # ax = fig.add_subplot(111)
    # line1, = ax.plot(x, y, 'r-') # Returns a tuple of line objects, thus the comma

    # for phase in np.linspace(0, 10*np.pi, 500):
    #     line1.set_ydata(np.sin(x + phase))
    #     fig.canvas.draw()
    #     fig.canvas.flush_events()
    #     # sleep(.5)