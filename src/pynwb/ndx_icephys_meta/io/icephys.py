"""
Module with ObjectMapper classes for the icephys-meta Container classes/neurodata_types
"""
from pynwb import register_map
from pynwb.io.file import NWBFileMap
from hdmf.common.io.table import DynamicTableMap
from ndx_icephys_meta.icephys import ICEphysFile, AlignedDynamicTable


@register_map(ICEphysFile)
class ICEphysFileMap(NWBFileMap):
    """
    Customize object mapping for ICEphysFile to define the mapping
    for our custom icephys tables, i.e., InteracellularRecordings, SimultaneousRecordingsTable,
    SequentialRecordingsTable, RepetitionsTable, and ExperimentalConditionsTable
    """
    def __init__(self, spec):
        super().__init__(spec)
        general_spec = self.spec.get_group('general')
        icephys_spec = general_spec.get_group('intracellular_ephys')
        self.map_spec('intracellular_recordings', icephys_spec.get_neurodata_type('IntracellularRecordingsTable'))
        self.map_spec('icephys_simultaneous_recordings', icephys_spec.get_neurodata_type('SimultaneousRecordingsTable'))
        self.map_spec('icephys_sequential_recordings', icephys_spec.get_neurodata_type('SequentialRecordingsTable'))
        self.map_spec('icephys_repetitions', icephys_spec.get_neurodata_type('RepetitionsTable'))
        self.map_spec('icephys_experimental_conditions', icephys_spec.get_neurodata_type('ExperimentalConditionsTable'))
        self.map_spec('ic_filtering', icephys_spec.get_dataset('filtering'))


@register_map(AlignedDynamicTable)
class AlignedDynamicTableMap(DynamicTableMap):
    """
    Customize the mapping for AlignedDynamicTable
    """
    def __init__(self, spec):
        super().__init__(spec)
        # By default the DynamicTables contained as sub-categories in the AlignedDynamicTable are mapped to
        # the 'dynamic_tables' class attribute. This renames the attribute to 'category_tables'
        self.map_spec('category_tables', spec.get_neurodata_type('DynamicTable'))
