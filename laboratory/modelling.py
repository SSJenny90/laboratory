from impedance import preprocessing as pp
from impedance.models.circuits import CustomCircuit, Randles, fitting
from impedance.visualization import plot_nyquist, plot_bode
# from impedance import fitting
import numpy as np
import matplotlib.pyplot as plt
import warnings

# GEO_FACTOR = 0.037571538461538455

def to_complex_z(re, im):
    return re + 1j*im

def model_impedance(circuit, guess, freq, impedance, name='circuit'):
    model = CustomCircuit(
        name='Custom {}'.format(name),
        circuit=circuit,
        initial_guess=guess
        )
    model.fit(freq, impedance, method='lm', bounds=(-np.inf, np.inf))
    # print(repr(model.predict(np.geomspace(0.001,2e6,100),True)))
    return model

def get_resistance(model):
    """Only works for resistors in series"""
    result = {}
    for p, val in zip(model.get_param_names()[0], model.parameters_):
        result[p] = val

    return sum([val for element, val in result.items() if element.startswith('R')])