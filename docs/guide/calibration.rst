Instrument Calibration
======================

In order for the laboratory to function as intended, instruments in the laboratory - namely the furnace - need to be calibrated before commencing an experiment. At present, two functions exist to help you calibrate the furnace.

Open furnace
^^^^^^^^^^^^

The :func:`~calibration.open_furnace_calibration` corrects for the difference between the temperature indicated on the furnace controller and the measured temperature at the sample istelf. Because the sample sits inside a tube threaded through the core of an open furnace, there will always be a reduced temperature at the sample when compared to the furnace itself. If not corrected for, this can become problematic as the sample may sit hundreds of degrees below what we intended. However, by calibrating the instrument, we can set it to automatically make this adjustment for us.

The :func:`~calibration.open_furnace_calibration` is accessible via the :mod:`~calibration` module and can be run as follows:

    >>> from laboratory import calibration
    >>> calibration.open_furnace_calibration()

The :func:`~calibration.open_furnace_calibration` typically takes around 24 hours to complete depending on the settings used. The reason it takes this long is that the furnace requires a minimum time at each temperature interval in order to equilibrate and get an accurate reading. Thankfully this particular calibration does not need to be performed before each experiment as the corrections are unlikely to change over time unless the furnace itself begins to deteriorate and lose power. Therefore, check the calibration folder to see if it contains a file called :file:`open_furnace_calibration.pkl` which stores the necessary calibration data.   

.. note::

    The open furnace correction needs to be accounted for when designing the experiment as the maximum temperature of the furnace is nowhere close to the maximum temperature attainable for the sample. To get an idea of the maximum sample temperature attainable using the current instrumentation, plot the results of the :func:`~calibration.open_furnace_calibration` using:

        >>> from laboratory import plot
        >>> plot.open_furnace_calibration()

Stage profile
^^^^^^^^^^^^^
The :func:`~calibration.stage_temperature_profile` calibration creates a temperature profile across the linear stage using both electrodes at the sample interface. This profile is required to characterise the thermal gradient across the sample during experimentation. This calibration can be called and plotted in a similar fashion to the :func:`~calibration.open_furnace_calibration` using:

    >>> from laboratory import calibration, plot
    >>> calibration.furnace_temperature_profile()
    >>> plot.furnace_temperature_profile()

This calibration also takes approximately 24 hours (based on the default settings) to complete and, upon completion, will save a file to the calibration folder called :file:`furnace_temperature_profile.pkl`. Once this file exists in the calibration folder the user can then begin a new experiment. 

.. warning::
    The :func:`~calibration.stage_temperature_profile` MUST BE performed everytime a new sample is loaded into the device. Failure to calibrate the instrument may result in the sample being placed in undesired temperature gradients which WILL affect the outcome of experiments. 

.. note::

    If either calibration files are not detected by the program when starting a new experiment, a :class:`~utils.exceptions.CalibrationException` wil be raised and the experiment will fail. If the :file:`stage_temperature_profile.pkl` file is found to be more than 12 months old, a :class:`~utils.exceptions.CalibrationWarning` will be output to the console to indicate the file may be outdated. See :func:`~laboratory.Laboratory.run` for how to suppress this warning.
