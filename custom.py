from laboratory import Laboratory, processing
from impedance import preprocessing as pp
from impedance.models.circuits import CustomCircuit, Randles
from impedance.visualization import plot_nyquist, plot_bode
# from impedance import fitting
import numpy as np
import matplotlib.pyplot as plt

def plot():
    # lab = lab = Laboratory(project_name='C:\\Users\\a1654095\\Google Drive\\Sam_Jennings\\PhD\\Test B')

    # data = lab.data.loc[lab.data.temp > 500]
    # data = data.iloc[0]

    # for z,t in zip(data.z,data.theta):
    #     print(z, t)

    # re = np.multiply(data.z, np.cos(data.theta))
    # im = np.multiply(data.z, np.sin(data.theta))
    f = np.around(np.geomspace(20, 2000000, 50))
    # print(np.linspace(f.min(), f.max(), 6)[1:-1])
    # print(f)
    # return
    test = "Z 4148386.171 -0.5270083016 \
Z 3749447.904 -0.5743760255 \
Z 3242746.131 -0.5628538004 \
Z 3075560.521 -0.7842152371 \
Z 2520269.868 -1.093873763 \
Z 2360322.905 -1.039938569 \
Z 1917410.135 -1.127827137 \
Z 1498256.638 -1.148737607 \
Z 1279688.921 -1.226242714 \
Z 1043484.238 -1.267587998 \
Z 818863.3774 -1.314428501\
Z 660819.9161 -1.341801836\
Z 526826.6945 -1.342700652\
Z 420074.0008 -1.344236496\
Z 335943.1841 -1.330299487\
Z 268952.1192 -1.304417333\
Z 216497.7429 -1.270038311\
Z 175709.7636 -1.22330233\
Z 144375.7368 -1.164387662\
Z 120314.273 -1.094591453\
Z 102367.1958 -1.019239513\
Z 89097.07548 -0.9421355039\
Z 79416.6516 -0.8717117149\
Z 72309.63689 -0.8155576883\
Z 66840.33751 -0.7799887498\
Z 62282.69347 -0.7686741025\
Z 58009.50832 -0.7827750839\
Z 53579.46627 -0.8203928889\
Z 48761.43503 -0.8782469762\
Z 43455.55685 -0.9508794307\
Z 37846.02227 -1.030158109\
Z 32210.34052 -1.108929103\
Z 26909.91656 -1.182112116\
Z 22117.53905 -1.247272376\
Z 17996.19423 -1.30280904\
Z 14529.38874 -1.34910968\
Z 11661.54242 -1.386891225\
Z 9335.269147 -1.417413064\
Z 7462.930382 -1.441666773\
Z 5970.803801 -1.461249523\
Z 4781.939221 -1.478286196\
Z 3843.609914 -1.494680458\
Z 3104.735022 -1.515506766\
Z 2517.557586 -1.547681193\
Z 2036.761941 -1.603270156\
Z 1601.814194 -1.694012583\
Z 1163.306612 -1.791000906\
Z 790.0131701 -1.799483371\
Z 562.0048376 -1.713316429\
Z 421.6272428 -1.612361718\
    "

    measurements = test.split('Z')
    zx = [z.strip().split(' ') for z in measurements][1:]
    # print(z)

    z, theta = [],[]
    for p in zx:
        z1, t1 = p
        z.append(float(z1))
        theta.append(float(t1))
    re = np.multiply(z, np.cos(theta))
    im = np.multiply(z, np.sin(theta))

    im = np.multiply(data.z, np.sin(data.theta))

    f = np.around(np.geomspace(20, 2000000, 50))
    z = re + 1j*im

    # f, z = pp.readCSV('exampleData.csv')

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
        ('p(R1,C1)-p(R2,C2)', [5e+4, capacitor, 1e+6, capacitor]), 
        # ('R0-p(R1,C1)-p(R2,C2)', [100, 80000, .01, 10**6, .01]), 
    ]


    # fig, ax = plt.subplots(2, 1, figsize=(5,5), num='Bode')
    # plot_bode(ax, f, z)

    ]
    fig = plt.figure('Test')
    fig.clear()
    fig, ax = plt.subplots(figsize=(5,5), num='Test')
    plot_nyquist(ax, z, fmt='o')

    for circuit in circuits:
        model = model_impedance(*circuit,f, z)
        res = get_resistance(model)
        # print(res)
        res = res/1000
        SAMPLE_THICKNESS = 2.6e-3 #in mm
        for i in [2.5, 2.6, 2.7]:
            geo_fac = 97.686e-6/(i*1e-3)
            print(res * geo_fac,'k.Ohm.m')
        
        # res = get_resistance(model)

        # SAMPLE_THICKNESS = 2.6 #in mm
        # SAMPLE_DIAMETER = 12.7 #in mm
        # SAMPLE_AREA = 97.686

        GEO_FACTOR = 0.037571538461538455
        print(res * GEO_FACTOR)
        # plot_nyquist(ax, model.predict(np.geomspace(0.001,2000000,100)), fmt='-')
      
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
    pass