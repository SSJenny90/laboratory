# import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np

def plot_profile(x,y,**kwargs):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x,y,**kwargs)
    plt.show()

def func(x,a,b,c):
    return np.multiply(a,np.square(x)) + np.multiply(b,x) + c

if __name__ == '__main__':
    data = Utils.load_obj('furnace_profile')

    te1 = np.asarray(data.thermo.te1)
    te2 = np.asarray(data.thermo.te2)
    x = np.asarray(data.xpos)

    popt, pcov = curve_fit(func, x, te1)
    print(popt)

    popt2, pcov2 = curve_fit(func, x, te2)
    print(popt2)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.plot(x,te1,'bx',label='te1')
    ax.plot(x,func(x,*popt),'b-')
    ax.plot(x,te2,'rx',label='te2')
    ax.plot(x,func(x,*popt2),'r-')
    plt.legend()
    plt.show()
