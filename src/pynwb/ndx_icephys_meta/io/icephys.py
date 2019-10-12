from pynwb import register_map
from hdmf.common.io.table import DynamicTableMap
from ndx_icephys_meta.icephys import Sweeps
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
        if ret is None:
            return ret
        return ret

    @ObjectMapper.constructor_arg('intracellular_recordings')
    def intracellular_recordings_arg(self, builder, manager):
        """
        Define the intracellular_recordings constructor argument for read
        """
        ret = builder['recordings']['attributes']['table']
        ret = manager.construct(ret)
        return ret
