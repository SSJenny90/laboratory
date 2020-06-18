from laboratory import Laboratory, processing
from impedance import preprocessing as pp
from impedance.models.circuits import CustomCircuit, Randles
from impedance.visualization import plot_nyquist, plot_bode
import numpy as np
import matplotlib.pyplot as plt

def plot():
    lab = lab = Laboratory(project_name='C:\\Users\\a1654095\\Google Drive\\Sam_Jennings\\PhD\\Test B')

    data = lab.data.loc[lab.data.temp > 500]
    data = data.iloc[0]

    re = np.multiply(data.z, np.cos(data.theta))

    im = np.multiply(data.z, np.sin(data.theta))

    f = np.around(np.geomspace(20, 2000000, 50))
    z = re + 1j*im

    # f, z = pp.readCSV('exampleData.csv')

    f, z = pp.ignoreBelowX(f, z)
    f, z = pp.cropFrequencies(f, z, 150, 10**6)

    # circuit = Randles(CPE=True, initial_guess=[.01, 10**5,100,.05,1, 1])

    # circuit = CustomCircuit(
    #     'R0-p(R1,C1)-p(R2-Wo1,C2)',
    #     # circuit = 'p(R1,C1)',
    #     initial_guess = [.01, .01, 100, .01, .05, 100, 1],
    # )
    # circuit.fit(f, z)
    # print(circuit)
    # z_fit1 = circuit.predict(f)

    circuits = [
        ('R1-p(R2,C2)-p(R3,C3)-C1', [.01, .01, 1, .01, 1, 1 ]), #tyb and roberts
        # ('R1-p(R2,C2)-p(R3,C3)', [.01, .01, 1, .01, 1]),
        ('p(R2,C2)-p(R3,C3)-CPE1', [.01, 1, .01, 1, 1, 1 ]),
        ('p(R2,C2)-p(R3,C3)-CPE1', [.01, 1, .01, 1, 1, 1 ]), 
        ('p(R2,C2)-p(R3,C3)-CPE1', [.01, 1, .01, 1, 1, 1 ]), 



    ]
    fig = plt.figure('Test')
    fig.clear()
    fig, ax = plt.subplots(figsize=(5,5), num='Test')
    plot_nyquist(ax, z)

    for circuit in circuits:
        
        a = CustomCircuit(
            name='Tyburczy and Roberts',
            circuit=circuit[0],
            initial_guess=circuit[1]
        )
        a.fit(f, z)
        plot_nyquist(ax, a.predict(f), fmt='.-')



    ax.axis('auto')
    ax.legend(['Data','Tyb']+[c[0] for c in circuits[1:]])
    plt.show()


    # fig, ax = plt.subplots(2,1)
    # plot_bode(ax, f, z)
    # plt.show()

if __name__ == '__main__':
    pass