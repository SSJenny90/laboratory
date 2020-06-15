import pandas as pd
import numpy as np
from scipy import optimize
from laboratory import config

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

        # i = np.argmax(np.sign(np.diff(Im[20:])) >=0 )

        i = 20
        for i in range(i, len(Im)-1):
            if Im[i+1] - Im[i] > Im[i] - Im[i-1]:
                break

        # if not i:
        #     i = len(Im)
        # i = len(Re)
        A = Re[:i]*2
        # print(A)
        r = np.dot(A, A)**-1 * np.dot(A, (Re[:i]**2 + Im[:i]**2))
        # print(r)
        diameter = 2*r

        return diameter


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

def process_data(data):
    thickness = config.SAMPLE_THICKNESS * 10 ** -3
    radius = (config.SAMPLE_DIAMETER/2) * 10 ** -3
    area = 97.686 * 10 ** -6

    data['resistance'] = data.apply(lambda x: fit_impedance(x,offset=5), axis=1)
    data['resistivity'] = (area / thickness) * data.resistance

    return data
    # data['resistivity'] = data.apply(lambda x: calculate_resistivity(x), axis=1)