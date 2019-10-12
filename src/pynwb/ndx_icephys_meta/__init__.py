def load_icephys_meta_namespace():
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


load_icephys_meta_namespace()

# Import the files
from .icephys import IntracellularRecordings # noqa E402, F401
