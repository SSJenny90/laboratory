from laboratory import Laboratory, processing
from impedance import preprocessing as pp
from impedance.models.circuits import CustomCircuit, Randles
from impedance.visualization import plot_nyquist, plot_bode
# from impedance import fitting
import numpy as np
import matplotlib.pyplot as plt

plt.ioff()

def plot():
    f = np.around(np.geomspace(20, 2000000, 50))
    z = np.array(
    [ 2.75978166e+06-1.39274121e+06j,  2.54200613e+06-1.57539933e+06j,
    2.49522352e+06-1.71147229e+06j,  1.90902885e+06-1.64497271e+06j,
    1.50143344e+06-1.33782116e+06j,  1.30572162e+06-1.52065266e+06j,
    9.99061032e+05-1.38551726e+06j,  7.36028897e+05-1.23313829e+06j,
    5.23682118e+05-1.09607018e+06j,  3.71223338e+05-9.04501330e+05j,
    2.64578469e+05-7.57134397e+05j,  1.89298501e+05-6.16280799e+05j,
    1.44571582e+05-5.03649798e+05j,  1.12195741e+05-4.05104006e+05j,
    9.01184802e+04-3.23290745e+05j,  7.66063174e+04-2.58111929e+05j,
    6.77561427e+04-2.06491157e+05j,  6.21590948e+04-1.64789196e+05j,
    5.84104204e+04-1.32235507e+05j,  5.59188495e+04-1.06704216e+05j,
    5.41847352e+04-8.69620145e+04j,  5.27360395e+04-7.18984013e+04j,
    5.13089391e+04-6.06960675e+04j,  4.96582886e+04-5.25989966e+04j,
    4.75433123e+04-4.69986448e+04j,  4.47138134e+04-4.32992888e+04j,
    4.10058589e+04-4.08830516e+04j,  3.63666767e+04-3.91060811e+04j,
    3.09691994e+04-3.73585067e+04j,  2.51431204e+04-3.51214363e+04j,
    1.94751422e+04-3.21635288e+04j,  1.44491660e+04-2.85838775e+04j,
    1.03611613e+04-2.47169036e+04j,  7.23646295e+03-2.08635908e+04j,
    4.96848597e+03-1.73136423e+04j,  3.38043929e+03-1.41844283e+04j,
    2.28436709e+03-1.15117294e+04j,  1.54767335e+03-9.28880295e+03j,
    1.05466821e+03-7.47005696e+03j,  7.23751357e+02-6.00223647e+03j,
    4.96273118e+02-4.82356660e+03j,  3.34777325e+02-3.88744133e+03j,
    2.06861400e+02-3.14861641e+03j,  9.09058741e+01-2.56115371e+03j,
    -3.50832993e+01-2.08287332e+03j, -1.76307027e+02-1.64719232e+03j,
    -2.59747333e+02-1.19109672e+03j, -1.96665670e+02-8.02848818e+02j,
    -9.21058415e+01-5.75797986e+02j, -2.38032642e+01-4.36855940e+02j,])

    f, z = pp.ignoreBelowX(f, z)
    f, z = pp.cropFrequencies(f, z, 200)

    # fig = plt.figure('a')
    # fig.clear()
    # fig, ax = plt.subplots(figsize=(5,5), num='a')
    # ax.loglog(f, np.abs(np.imag(z)),'rx')
    # i = np.argmax(np.sign(np.diff(np.imag(z)[20:])) <=0 )
    # ax.loglog(f[i],np.imag(z)[i],'bo')

    # plt.show()
    # return

    capacitor = 9e-10

    circuits = [
        # ('p(R2,C2)', [80000, capacitor]), 
        # ('p(R1,C1)-p(R2,C2)', [80000, .01, 10**6, .01]), 
        # ('p(R1,C1)-p(R2,C2)', [5.36e+04, capacitor, 4.23e+06, capacitor]), 
        ('p(R1,C1)-p(R2,C2)', [5e+4, capacitor, 5e+6, capacitor]), 
        # ('R0-p(R1,C1)-p(R2,C2)', [100, 80000, .01, 10**6, .01]), 
    ]


    # fig, ax = plt.subplots(2, 1, figsize=(5,5), num='Bode')
    # plot_bode(ax, f, z)

    
    fig = plt.figure('Test')
    fig.clear()
    fig, ax = plt.subplots(figsize=(5,5), num='Test')
    plot_nyquist(ax, z, fmt='o')

    for circuit in circuits:
        model = model_impedance(*circuit,f, z)
        res = get_resistance(model)
        res = res/1000
        # SAMPLE_THICKNESS = 2.6e-3 #in mm
        # for i in [2.5, 2.6, 2.7]:
        #     geo_fac = 97.686e-6/(i*1e-3)
        #     print(res * geo_fac,'k.Ohm.m')
        
        # res = get_resistance(model)

        # SAMPLE_THICKNESS = 2.6 #in mm
        # SAMPLE_DIAMETER = 12.7 #in mm
        # SAMPLE_AREA = 97.686

        GEO_FACTOR = 0.037571538461538455
        print(res * GEO_FACTOR)
        plot_nyquist(ax, model.predict(np.geomspace(0.001,2000000,100)), fmt='-')
        # plot_nyquist(ax, model.predict(np.geomspace(0.001,2000000,100),use_initial=True), fmt='-')
      
    ax.axis('auto')
    ax.legend(['Data','Tyb']+[c[0] for c in circuits[1:]])
    plt.show()


def model_impedance(circuit, guess, freq, impedance, name='circuit'):
    model = CustomCircuit(
        name='Custom {}'.format(name),
        circuit=circuit,
        initial_guess=guess
        )
    model.fit(freq, impedance, method='lm', bounds=(-np.inf, np.inf))
    return model

def get_resistance(model):
    """Only works for resistors in series"""
    result = {}
    for p, val in zip(model.get_param_names()[0], model.parameters_):
        result[p] = val

    return sum([val for element, val in result.items() if element.startswith('R')])




if __name__ == '__main__':
    plot()
    plt.show()
    pass