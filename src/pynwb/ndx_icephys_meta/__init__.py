import os
from pynwb import load_namespaces
#ndx_icephys_meta_specpath = os.path.join(os.path.dirname(__file__), 'spec', 'ndx-icephys-meta.namespace.yaml')
ndx_icephys_meta_specpath = '/Users/oruebel/Devel/nwb/icephys_extensions/ndx-icephys-meta/spec/ndx-icephys-meta.namespace.yaml'
load_namespaces(ndx_icephys_meta_specpath)

from .icephys import *
