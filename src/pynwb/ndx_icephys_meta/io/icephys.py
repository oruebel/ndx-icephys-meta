from pynwb import register_map
from hdmf.common.io.table import DynamicTableMap
from ndx_icephys_meta.icephys import Sweeps, SweepSequences, Runs
from hdmf.build import ObjectMapper


@register_map(Sweeps)
class SweepsMap(DynamicTableMap):
    """
    Define object mapping for the Sweeps Container class/spec
    """

    @DynamicTableMap.object_attr("recordings")
    def recordings_column(self, container, manager):
        """
        Define the recordings column for write
        """
        ret = container.get('recordings')
        return ret

    @ObjectMapper.constructor_arg('intracellular_recordings')
    def intracellular_recordings_arg(self, builder, manager):
        """
        Define the intracellular_recordings constructor argument for read
        """
        ret = builder['recordings']['attributes']['table']
        ret = manager.construct(ret)
        return ret


@register_map(SweepSequences)
class SweepSequencesMap(DynamicTableMap):
    """
    Define object mapping for the SweepSequences Container class/spec
    """

    @DynamicTableMap.object_attr("sweeps")
    def sweeps_column(self, container, manager):
        """
        Define the sweeps column for write
        """
        ret = container.get('sweeps')
        return ret

    @ObjectMapper.constructor_arg('sweeps')
    def sweeps_arg(self, builder, manager):
        """
        Define the sweeps constructor argument for read
        """
        ret = builder['sweeps']['attributes']['table']
        ret = manager.construct(ret)
        return ret

@register_map(Runs)
class RunsMap(DynamicTableMap):
    """
    Define object mapping for the Runs Container class/spec
    """

    @DynamicTableMap.object_attr("sweep_sequences")
    def recordings_column(self, container, manager):
        """
        Define the sweep_sequences column for write
        """
        ret = container.get('sweep_sequences')
        return ret

    @ObjectMapper.constructor_arg('sweep_sequences')
    def sweep_sequences_arg(self, builder, manager):
        """
        Define the sweep_sequences constructor argument for read
        """
        ret = builder['sweep_sequences']['attributes']['table']
        ret = manager.construct(ret)
        return ret
