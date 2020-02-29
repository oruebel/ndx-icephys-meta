"""
Python package with PyNWB extension classes for interacting with the icephys_meta extension
"""


def load_icephys_meta_namespace():
    """
    Internal helper function for loading the icephys_meta extension namespace for PyNWB

    Uses the load_namespaces function from PyNWB and as such modifies the state of PyNWB
    """
    # use function level imports here to avoid pulling these functions into the module namespace
    import os
    from pynwb import load_namespaces
    # Set the path where the spec will be installed by default
    ndx_icephys_meta_specpath = os.path.join(os.path.dirname(__file__),
                                             'spec',
                                             'ndx-icephys-meta.namespace.yaml')
    # If the extensions has not been installed but we running directly from the git repo
    if not os.path.exists(ndx_icephys_meta_specpath):
        ndx_icephys_meta_specpath = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                                 '../../../spec/',
                                                                 'ndx-icephys-meta.namespace.yaml'))
    # load namespace
    load_namespaces(ndx_icephys_meta_specpath)


# Load the icephys_meta extension namespace
load_icephys_meta_namespace()

# Import the files
from .icephys import ICEphysFile,  IntracellularRecordingsTable, Sweeps, SweepSequences, Runs, Conditions # noqa E402, F401
from . import io as __io  # noqa E402, F401
