Frequently Asked Questions
--------------------------

.. dropdown:: What is ngen-regionalization?

    ngen-regionalization is a command line utility for identifying optimized NextGen
    formulations and parameter values in ungauged catchments.

.. dropdown:: What is a formulation?

    A NextGen formulation is any single model or combination of models and/or
    modules running in a basin to simulate that location's hydrology. A formulation
    may include one more hydrologic models and modules, plus a streamflow routing
    module, a coastal model, and other supporting routines.

    For more information on the available models/modules, please see
    https://github.com/NOAA-OWP/NextGen-Info

.. dropdown:: What are parameters in this context?

    Every model or module utilizes parameters to reflect physical attributes of
    a location when making predictions of hydrologic behavior. Parameters might
    measure physical quantities such as drainage area, they could be dimensionless
    indices such as topographic wetness index, or they may be non-interpretable
    quantities such as weights and activation functions in a neural network. Each
    model or module will require different sets of parameters to make predictions.

    During calibration in gauged catchments, parameter values are tuned to create
    the "best" recreation of observed data for a given model.

.. dropdown:: What inputs are needed to run ngen-regionalization?

    TODO

.. dropdown:: How does ngen-regionalization find optimal formulations?

    TODO

.. dropdown:: How does ngen-regionalization find optimal parameter values?

    TODO

.. dropdown:: How do I start using this tool?

    Check out the User Guide to get started.
