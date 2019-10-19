"""
Module with ObjectMapper classes for the icephys-meta Container classes/neurodata_types
"""
from pynwb import register_map
from pynwb.io.file import NWBFileMap
from ndx_icephys_meta.icephys import ICEphysFile


@register_map(ICEphysFile)
class ICEphysFileMap(NWBFileMap):
    """
    Customize object mapping for ICEphysFile to define the mapping
    for our custom icephys tables, i.e., InteracellularRecordings, Sweeps,
    SweepSequences, Runs, and Conditions
    """
    def __init__(self, spec):
        super(ICEphysFileMap, self).__init__(spec)
        general_spec = self.spec.get_group('general')
        icephys_spec = general_spec.get_group('intracellular_ephys')
        self.map_spec('intracellular_recordings', icephys_spec.get_neurodata_type('IntracellularRecordings'))
        self.map_spec('sweeps', icephys_spec.get_neurodata_type('Sweeps'))
        self.map_spec('sweep_sequences', icephys_spec.get_neurodata_type('SweepSequences'))
        self.map_spec('runs', icephys_spec.get_neurodata_type('Runs'))
        self.map_spec('conditions', icephys_spec.get_neurodata_type('Conditions'))
