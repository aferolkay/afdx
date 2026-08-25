"""
A characterization test for the AFDX model.

It measures a fixed set of parameters from a simulation run, saves them as a
baseline, and fails if a later run changes any of them.

    metrics.py    the parameter set -- edit this by hand
    extractor.py  the API you implement to feed a model into it
    afdx.py       that API, implemented for this model
    measure.py    runs the spec against an extractor; saves/loads baselines
    report.py     compares two sets of measurements and prints the result
    __main__.py   the command line
"""
