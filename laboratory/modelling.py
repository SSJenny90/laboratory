from impedance import preprocessing as pp
from impedance.models.circuits import CustomCircuit, Randles, fitting
from impedance.visualization import plot_nyquist, plot_bode
# from impedance import fitting
import numpy as np
import matplotlib.pyplot as plt
import warnings


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

def model_conductivity(freq, complex_z, cutoff, circuit, guess):
    """Takes a row of the dataframe and return the model object, the resistance and the rmse.

    Args:
        row ([type]): [description]

    Returns:
        model: the model object
        resistance: calculated resistance
        rmse: the root mean square error on the resistance
    """
    f, z = pp.cropFrequencies(np.array(freq), complex_z, cutoff)
    f, z = pp.ignoreBelowX(f, z)
    model = model_impedance(circuit,guess,f, z)
    rmse = fitting.rmse(z, model.predict(f))
    resistance = get_resistance(model)
    return model, resistance, rmse
