Controlling the instruments
----------------------------------------------------
Before we begin with any Python, it is necessary to first navigate to the laboratory directory and activate the virtual environment. All the required packages are installed inside the virtual environment and therefore nothing will work without it first being activate. You can activate the environment by opening a terminal typing the following

    >pipenv shell

followed by 

    >ipython

to open up an iPython console inside the virtual environment. When this is done, you can then import the :class:`~laboratory.Laboratory` class and initialise a new instance.

    >>> from laboratory import Laboratory
    >>> lab = Laboratory()
    LCR connected at 
    DAQ connected at
    Gas connected at
    Furnace connected at 
    Stage connected at

If your console shows the same output as above, well done! This is by far the most troublesome part as maintaining connection to the instruments has proven difficult at times. If one or more of your instruments failed to connect, please see the :doc:`troubleshoot` section for tips on how to reconnect.

From this point you can now use the :code:`lab` variable to access the class attributes and methods available within :class:`~laboratory.Laboratory` (see the :doc:`/source/laboratory` documentation for a comprehensive of what is available). Most commonly, if you are calling the :class:`~laboratory.Laboratory` class, you will want to directly control the instruments in order to familiarise yourself with commands or troubleshoot various problems. Next, we'll walk through sending some commands and recieving a response from the various instruments.

The instruments are connected on initialisation and are accesible as class attributes.

    >>> lab.lcr
    <laboratory.drivers.LCR at 0x214786d76a0>
    >>> lab.daq
    <laboratory.drivers.DAQ at 0x214786ba2b0>
    >>> lab.furnace
    <laboratory.drivers.Furnace at 0x214786a28c3>
    >>> lab.gas
    <laboratory.drivers.GasControllers at 0x214786b46d0>
    >>> lab.stage
    <laboratory.drivers.Stage at 0x214786f26e0>

Each instrument has it's own attributes and methods which can be used to send commands and receive data from the instrument. Detailed documentation is available for all :doc:`drivers</source/drivers>`. Let's run through some examples of sending commands to the instruments. 

Furnace
^^^^^^^^^^^^^^^^^

First, let's query the furnace for it's current temperature and heating rate, then we will tell it to heat our sample up to 100 degrees Celsius.

    >>> lab.furnace.indicated() #the current temperature
    40.0
    >>> lab.furnace.heating_rate()  #the current heating rate
    3.0
    >>> lab.furnace.heating_rate(10) #set the heating rate to 10 degrees C/min
    True
    >>> lab.furnace.heating_rate()  #check to make sure
    10.0
    >>> lab.furnace.setpoint_select() #check which setpoint is currently active
    'setpoint_1'
    >>> lab.furnace.setpoint_1()    #what is it set to?
    40.0
    >>> lab.furnace.setpoint_1(100) #set it to 100 degrees C
    True
    >>> lab.furnace.setpoint_1()    #double check
    100.0

In general, most methods will either return the current value if no argument is passed or, if an argument is passed, return :code:`True` if the command was succesful or return :code:`None` if unsuccesful. 

DAQ
^^^^^^^^^^^^^^^^^

Let's now query the DAQ for the actual temperature inside the measurement apparatus and the voltage across the sample. Remember, these temperatures will be less than the furnace indicated temperature which is why calibrations are required before each experiment.

    >>> lab.daq.get_temperature()
    {'tref': 22.0, 'te1': 56.5, 'te2': 55.9}
    >>> lab.daq.get_voltage()
    {'voltage': 0.12827}
    >>> lab.daq.get_thermopower()
    {'tref': 22.0, 'te1': 56.5, 'te2': 55.9, 'voltage': 0.12827}

.. note::
    
    :func:`~laboratory.DAQ.get_thermopower` is merely a convenience method that first calls :func:`~laboratory.DAQ.get_temperature` and then calls :func:`~laboratory.DAQ.get_voltage` and combines the result.

Linear stage
^^^^^^^^^^^^^^^^^

Moving the linear stage is required in order to place the sample in specific temperature gradients within the furnace. During an experiment this will be handled for you using the calibration files and methods on the :class:`~laboratory.drivers.Stage` class. There are two main methods for controlling the position of the stage, moving to an absolute point and moving a displacement distance in either the positive or negative directions. Moving to an absolute position uses the internal measurement system of the motion controller while displacement is specified in millimeters.

    >>> lab.stage.reset() #send the stage back to 0
    True
    >>> lab.stage.speed(25) # set stage movement speed to 25 mm/s
    True
    >>> lab.stage.go_to(5000) #go to an absolute position on the stage
    True
    >>> lab.stage.speed(10) # set stage movement speed to 5 mm/s
    True
    >>> lab.stage.go_to(6000) #go to an absolute position on the stage
    True
    >>> lab.stage.move(-10) #move in the negative direction 10 mm
    True
    >>> lab.stage.move(20) #move in the positive direction 20 mm
    True
    >>> lab.position()  #get the final position
    7000

.. .. note::

..     It is always advisable to reset the linear stage before controlling movement via absolute position. The internal position can sometimes be corrupt when the stage tries to move beyond it's limits and therefore subsequent position commands can be wrong. 

.. attention::

    It is always advisable to reset the linear stage before controlling movement via absolute position. The internal position can sometimes be corrupt when the stage tries to move beyond it's limits and therefore subsequent position commands can be wrong. 

Mass Flow Controllers
^^^^^^^^^^^^^^^^^^^^^^^

The mass flow controllers in the lab can be controlled either as a group or individually, both of which prove useful depending on circumstance. At the highest level, the :class:`~laboratory.drivers.GasControllers` class will connect to each individual gas and save it to the class as an attribute accessible via the name of the gas. Via the :class:`~laboratory.drivers.GasControllers` object, it is possible to set and query all gas controllers at the same time which is often more convenient than getting or setting individually.

    >>> gas_input = {'co2':20,'co_a':15,'co_b':1.2,'h2':7.67}
    >>> gas.set_all(**gas_input)
    True
    >>> gas.get_all()
    {'co2': { 'pressure': 14.86,
            'temperature': 24.83,
            'volumetric_flow': 19.8,
            'mass_flow': 20.0,
            'setpoint': 20.0},
    'co_a': {'pressure': 14.78,
            'temperature': 24.69,
            'volumetric_flow': 14.89,
            'mass_flow': 15.0,
            'setpoint': 15.0},
    'co_b': {'pressure': 14.89,
            'temperature': 24.34,
            'volumetric_flow': 1.181,
            'mass_flow': 1.2,
            'setpoint': 1.2},
    'h2': {  'pressure': 14.8,
            'temperature': 23.9,
            'volumetric_flow': 7.59,
            'mass_flow': 7.67,
            'setpoint': 7.67}}

Or, if required, an individual gas may be set and data retrieved.

    >>> gas.co2.setpoint(12.57)
    >>> gas.co2.get()   #return results from an individual controller
    {'pressure': 14.83,
    'temperature': 24.86,
    'volumetric_flow': 12.57,
    'mass_flow': 12.57,
    'setpoint': 12.57}

Methods for both the higher level :class:`~laboratory.drivers.GasControllers` and lower-level :class:`~laboratory.drivers.AlicatController` can be found :doc:`here</source/drivers>`.

LCR
^^^^^^

The driver for the LCR meter doesn't really provide useful commands for troubleshooting. The interested user is welcome to read through the documentation and control the LCR meter in much the same way as the other instruments. It is much more useful to run test experiments in order to debug and troubleshoot the LCR meter. This is because many issues will relate to the returned data which is easire to debug when in the appropriate format (i.e. the format returned during an experiment).