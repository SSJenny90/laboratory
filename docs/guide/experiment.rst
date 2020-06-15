Beginning a new experiment
----------------------------

The :mod:`laboratory` package is designed to make starting an experiment in the lab as painless as possible. When it comes down to it, a new experiment can be started with

    >>> from laboratory import Experiment
    >>> Experiment.run()

Of course, to get to this stage a few things are required to be in place. First of all, we need a set of instruction to tell the program exactly what experimental conditions we want and for how long we want to run the experiment under those conditions. This is achieved by designing a control file that the program will be able to interpret as a set of instruction for running the experiment. The control file is a simple .xlsx spreadsheet with specific header names that will be read in by the program. A simple example experiment would look something like this.

.. figure:: /images/example_control.PNG
   :alt: exmple control file
   
   An example control file for designing experiments. 
   
This particular example experiment has four individual steps that will take measurements under specified conditions for a period of 4 hours each. Each step will ramp up in temperature at a rate specified by :code:`heat_rate` all the while taking a suite of measurements at intervals defined by :code:`interval`. The :code:`buffer` column specifies the desired fo2 buffer to be used and will determine the gas mix being fed into the inner measurement apparatus. Specifying an :code:`offset` other than :code:`0` will instruct the program to offset the fo2 buffer by that many log units and can be a positive or negative number. Finally, :code:`fo2_gas` determines whether CO or H2 is used to achieve the desired :code:`buffer`.  

.. todo::

    Complete instructions on conducting and experiment