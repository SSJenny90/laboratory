from laboratory.utils import loggers
logger = loggers.lab(__name__)
from laboratory import config
from alicat import FlowController
import numpy as np
import math

class AlicatController(FlowController):
    """Driver for an individual Mass Flow Controller.

    .. note::

        not called directly - access is from within :class:'~Drivers.MFC'

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    get_massflow    gets massflow from controller
    set_massflow    sets massflow on controller
    get_pressure    gets pressure from controller
    set_pressure    sets massflow on controller
    get_temp        gets pressure from controller
    get_vol_flow    gets volumetric flow from controller
    get_setpoint    gets current set point from controller
    reset           resets the device
    =============== ===========================================================

    \*see FlowController for more methods
    """
    def __init__(self,port,address):
        super(AlicatController,self).__init__(port,address)

    def get_all(self):
        vals = [(self.massflow)]
        vals.append(self.pressure)
        vals.append(self.temperature)
        vals.append(self.volumetric_flow)
        vals.append(self.setpoint)
        return vals

    def massflow(self,value=None):
        """Get or set the massflow of the appropriate flowmeter

        :param value: desired massflow value
        :type value: float
        """
        self.control_point = 'flow'
        if value: self.set_flow_rate(value)
        else: return self.get()['mass_flow']

    def pressure(self,value=None):
        """Get or set pressure of the appropriate flowmeter

        :param value: desired massflow value
        :type value: float
        """
        self.control_point = 'pressure'
        if value: self.set_gas_pressure(value)
        else: return self.get()['pressure']

    def temperature(self):
        """Gets the temperature of the appropriate flowmeter
        :returns: gas temperature
        :rtype: float
        """
        self.flush()
        return self.get()['temperature']

    def volume_flow(self):
        """Gets the volumetric flow of the appropriate flowmeter"""
        return self.get()['volumetric_flow']

    def setpoint(self):
        """Gets the current set point of the appropriate flowmeter"""
        return self.get()['setpoint']

    def reset(self):
        """
        sets the massflow to 0
        """
        self.set_massflow(0)

class MFC(AlicatController):
    """Global driver for all Mass Flow Controllers

    .. note::

        see AlicatController for methods to control individual gases

    =============== ===========================================================
    Attributes      message
    =============== ===========================================================
    maxtry          max number to attempt command
    status          whether the instrument is connected
    co2             controls for the Carbon Dioxide (CO2) controller
    co_a            controls for the coarse Carbon Monoxide (CO) controller
    co_b            controls for the fine Carbon Monoxide (CO) controller
    h2              controls for the Hydrogen (H2) controller
    address         computer port address
    =============== ===========================================================

    =============== ===========================================================
    Methods         message
    =============== ===========================================================
    close_all       closes all controllers
    connect         attempt to connect to the LCR meter
    flush_all       flushes data from the input/output buffer of all devices
    fugacity_co     returns a ratio of CO2/CO to achieve desired oxygen fugacity
    fugacity_h2     returns a ratio of H2/CO2 to achieve desired oxugen fugacity
    reset           resets the device
    =============== ===========================================================

    :Example:

    >>> import Drivers
    >>> mfc = Drivers.MFC()
    >>> mfc.co2.get_massflow()
    """
    def __init__(self):
        self.maxtry = 5
        self.status = False
        self.address = config.mfc_address

        self._connect()

    def __str__(self):
        """String representation of the :class:`Drivers.LCR` object."""
        return "{}.{}<id=0x{:x}\n\naddress = {}\nmaxtry = {}\nstatus = {}".format(
            self.__module__,
            self.__class__.__name__,
            id(self),
            self.address,
            self.maxtry,
            self.status
            )

    def _connect(self):
        """
        Connects to the mass flow controllers
        """
        try:
            self.co2 = AlicatController(self.address,address='A')
            self.co_a = AlicatController(self.address,address='B')
            self.co_b = AlicatController(self.address,address='C')
            self.h2 = AlicatController(self.address,address='D')
        except Exception as e:
            logger.error('    MFC - FAILED (check log for details)')
            logger.debug(e)
            self.status = False
        else:
            logger.info('    MFC - CONNECTED!')
            self.all = [self.co2,self.co_a,self.co_b,self.h2]
            self.status = True

    def reset(self):
        """Resets all connected flow controllers to 0 massflow"""
        for controller in self.all: controller.set_massflow(0)

    def flush_all(self):
        """Flushes the input? buffer of all flow controllers"""
        for controller in self.all: controller.flush()

    def close_all(self):
        """Closes all flow controllers"""
        for controller in self.all: controller.close()

    # def set_fugacity(self):
    #     """
    #     Sets the correct gas ratio for the given buffer. Percentage offset from a given buffer can be specified by 'offset'. Type of gas to be used for calculations is specified by gas_type.
    #
    #     :param buffer: buffer type (see table for input options)
    #     :type buffer: str
    #
    #     :param offset: percentage offset from specified buffer
    #     :type offset: float, int
    #
    #     :param gas_type: gas type to use for calculating ratio - can be either 'h2' or 'co'
    #     :type pressure: str
    #     """
    #     logger.debug('Recalculating required co2:{:s} mix...'.format(gas_type))
    #     vals = self.daq.get_temp()
    #     temp = np.mean(vals[1:2])
    #     fo2p = self.mfc.fo2_buffer(temp,buffer)
    #
    #     if gas_type == 'h2':
    #         ratio = self.mfc.fugacity_h2(fo2p,temp)
    #         h2 = 10
    #         co2 = round(h2*ratio,2)
    #
    #         logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))
    #         logger.debug('    Setting CO2 to {}'.format(co2))
    #         self.save_data('delete_me',co2,gastype='co2')
    #         # self.mfc.co2.set_massflow()
    #         logger.debug('    Setting H2 to {:.2f}'.format(h2))
    #         self.save_data('delete_me',h2,gastype='h2')
    #         # self.mfc.h2.set_massflow()
    #
    #     elif gas_type == 'co':
    #
    #         ratio = self.mfc.fugacity_co(fo2p,temp)
    #         logger.debug('    {:.5f}:1 required to maintain +{:.2%} the "{:s}" buffer @ {:.1f} degrees Celsius'.format(ratio,offset,buffer,temp))
    #
    #         co2 = 50    #sets 50 sccm as the optimal co2 flow rate
    #         if co2/ratio >= 20:
    #             co2 = round(20*ratio,2)
    #
    #         co = round(co2/ratio,3)
    #         co_a = int(co2/ratio)
    #         co_b = co - co_a
    #         logger.debug('    Setting CO2 to {}'.format(co2))
    #         # self.mfc.co2.set_massflow(co2)
    #         self.save_data('delete_me',co2,gastype='co2')
    #         logger.debug('    Setting CO_a = {0:.3f}'.format(co_a))
    #         # self.mfc.co_a.set_massflow(co_a)
    #         self.save_data('delete_me',co_a,gastype='co_a')
    #         logger.debug('    Setting CO_b = {0:.3f}'.format(co_b))
    #         # self.mfc.co_b.set_massflow(co_b)
    #         self.save_data('delete_me',co_b,gastype='co_b')
    #     else:
    #         logger.error('Incorrect gas type specified!')

    def fugacity_co(self,fo2p, temp):
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
        fo2 = 1.01325*(10**(fo2p-5)) # convert Pa to atm

        g1=(((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10;  # Gibbs free energy
        k1=math.exp(-g1/rgc/tk);  # equilibrium constant

        CO = k1 - 3*k1*fo2 - 2*fo2**1.5
        CO2 = 2*k1*fo2 + fo2 + fo2**1.5 + fo2**0.5

        return CO2/CO

    def fugacity_h2(self,fo2p, temp):
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
        fo2 = 1.01325*(10**(fo2p-5)) # convert Pa to atm

        g1=(((a14*temp+a13)*temp+a12)*temp+a11)*temp+a10  # Gibbs free energy
        g3=(((a34*temp+a33)*temp+a32)*temp+a31)*temp+a30  # Gibbs free energy
        k1=math.exp(-g1/rgc/tk)  # equilibrium constant
        k3=math.exp(-g3/rgc/tk)  # equilibrium constant

        a = k1/(k1 + fo2**0.5)
        b = fo2**0.5/(k3 + fo2**0.5)

        H2 = a*(1-fo2) - 2*fo2
        CO2 = b*(1-fo2) + 2*fo2

        return CO2/H2

    def fo2_buffer(self,temp,buffer,pressure=1.01325):
        """
        Calculates oxygen fugacity at a given temperature and fo2 buffer

        =============== ===========================================================
        input options   type of fo2 buffer
        =============== ===========================================================
        'QFM'           quartz-fayalite-magnetite
        'IW'            iron-wustite
        'WM'            wustite-magnetite
        'MH'            magnetite-hematite
        'QIF'           quartz-iron-fayalite
        'NNO'           nickel-nickel oxide
        'MMO'           molyb
        'CCO'           cobalt-cobalt oxide
        =============== ===========================================================

        :param temp: Temperature in u'\N{DEGREE SIGN}C'
        :type temp: float, int

        :param buffer: buffer type (see table for input options)
        :type buffer: str

        :param pressure: pressure in bar (default: surface pressure)
        :type pressure: float, int

        :returns: log10 oxygen fugacity
        :rtype: float
        """

        def fug(a,temp,pressure):
            if len(a) is 2:
                fo2  =  10**(a[0]/temp + a[1])
            elif len(a) is 3:
                fo2  =  10**(a[0]/temp + a[1] + a[2]*(pressure - 1e5)/temp)
            return fo2

        # if isinstance(buffer,str):
        #     buffer = buffer.lower()
        # else:
        #     np.char.lower(buffer)

        Tc = 10000

        temp = temp+273 #convert Celsius to Kelvin

        #Many of these empirical relationships are determined fo2 in atm.
        #These relationships have been converted to Pa.
        if buffer == 'iw': # Iron-Wuestite
            # Myers and Eugster (1983)
            # a[1] = [-26834.7 11.477 5.2e-7]        # 833 to 1653 K
            # a[3] pressure term from Dai et al. (2008)
            # a = [-2.7215e4 11.57 5.2e-7] - O'Neill (1988)
            a1 = [-27538.2, 11.753]
        elif buffer in ['qfm','fmq','fqm']: # Fayalite-Quartz-Magnetite
            # Myers and Eugster (1983)
            a1 = [-27271.3, 16.636]        # 298 to 848 K
            a2 = [-24441.9, 13.296]        # 848 to 1413 K
            Tc = 848 # K

        elif buffer == 'wm': # Wuestite-Magnetite
            # # Myers and Eugster (1983)
            # a[1] = [-36951.3 21.098]        # 1273 to 1573 K
            # O'Neill (1988)
            a1 = [-32356.6, 17.560]
        elif buffer == 'mh': # Magnetite-Hematite
            # Myers and Eugster (1983)
            a1 = [-25839.1, 20.581]        # 298 to 950 K
            a2 = [-23847.6, 18.486]        # 943 to 1573 K
            Tc = 943 # K
        elif buffer == 'qif': # Quartz-Iron-Fayalite
            # Myers and Eugster (1983)
            a1 = [-30146.6, 14.501]        # 298 to 848 K
            a2 = [-27517.5, 11.402]        # 848 to 1413 K
            Tc = 848 # K
        elif buffer == 'osi': # Olivine-Quartz-Iron
            # Nitsan (1974)
            Xfa = 0.10
            gamma = (1 - Xfa)**2*((1 - 1690/temp)*Xfa - 0.24 + 730/temp)
            afa = gamma*Xfa
            fo2 = 10**(-26524/temp + 5.54 + 2*math.log10(afa) + 5.006)
            return fo2
        elif buffer == 'oqm': # Olivine-Quartz-Magnetite
            # Nitsan (1974)
            Xfa = 0.10
            Xmt = 0.01
            gamma = (1 - Xfa)**2*((1 - 1690/temp)*Xfa - 0.24 + 730/temp)
            afa = gamma*Xfa
            fo2 = 10**(-25738/temp + 9 - 6*math.log10(afa) + 2*math.log10(Xmt) + 5.006)
            return fo2
        elif buffer == 'nno': # Ni-NiO
            #a = [-24930 14.37] # Huebner and Sato (1970)
            #a = [-24920 14.352] # Myers and Gunter (1979)
            a1 = [-24920, 14.352, 4.6e-7]
            # a[3] from Dai et al. (2008)
        elif buffer == 'mmo': # Mo-MoO2
            a1 = [-30650, 13.92, 5.4e-7]
            # a[3] from Dai et al. (2008)
        elif buffer == 'cco': # Co-CoO
            # Myers and Gunter (1979)
            a1 = [-25070, 12.942]
        elif buffer == 'g': # Graphite, CO-CO2
            # French & Eugster (1965)
            fo2 = 10**(-20586/temp - 0.044 + math.log10(pressure) - 2.8e-7*(pressure - 1e5)/temp)
            return
        elif buffer == 'fsqm': # Ferrosilite-Quartz-Magnetite
            # Seifert (1982)
            # Kuestner (1979)
            a1 = [-25865, 14.1456]
        elif buffer == 'fsqi': # Ferrosilite-Quartz-Iron
            # Seifert et al. (1982)
            # Kuestner 1979
            a1 = [-29123, 12.4161]
        else:
            raise ValueError('(fugacityO2): Unknown buffer.')

        if temp < Tc:
            fo2 = fug(a1,temp,pressure)
        else:
            fo2 = fug(a2,temp,pressure)

        return math.log10(fo2)
