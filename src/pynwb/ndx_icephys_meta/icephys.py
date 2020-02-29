from pynwb import register_class
from pynwb.file import NWBFile
from pynwb.icephys import IntracellularElectrode
from pynwb.base import TimeSeries
try:
    from pynwb.core import DynamicTable, DynamicTableRegion
except ImportError:
    from hdmf.common import DynamicTable, DynamicTableRegion
from hdmf.utils import docval, popargs, getargs, call_docval_func, get_docval, fmt_docval_args
import warnings
import pandas as pd

namespace = 'ndx-icephys-meta'


class HierarchicalDynamicTableMixin(object):
    """
    Mixin class for defining specialized functionality for hierarchical dynamic tables.


    Assumptions:

    1) The current implementation assumes that there is only one DynamicTableRegion column
    that needs to be expanded as part of the hierarchy.  Allowing multiple hierarchical
    columns in a single table get tricky, because it is unclear how those rows should
    be joined. To clarify, allowing multiple DynamicTableRegion should be fine, as long
    as only one of them should be expanded as part of the hierarchy.

    2) The default implementation of the get_hierarchy_column_name function assumes that
    the first DynamicTableRegion that references a DynamicTable that inherits from
    HierarchicalDynamicTableMixin is the one that should be expanded as part of the
    hierarchy of tables. If there is no such column, then the default implementation
    assumes that the first DynamicTableRegion column is the one that needs to be expanded.
    These assumption of get_hierarchy_column_name can be easily fixed by overwriting
    the function in the subclass to return the name of the approbritate column.
    """

    def get_hierarchy_column_name(self):
        """
        Get the name of column that references another DynamicTable that
        is itseflHierarchicalDynamicTableMixin table.

        :returns: String with the column name or None
        """
        first_col = None
        for col_index, col in enumerate(self.columns):
            if isinstance(col, DynamicTableRegion):
                first_col = col.name
                if isinstance(col.table, HierarchicalDynamicTableMixin):
                    return col.name
        return first_col

    def get_referencing_column_names(self):
        """
        Determine the names of all columns that reference another table, i.e.,
        find all DynamicTableRegion type columns

        Returns: List of strings with the column names
        """
        col_names = []
        for col_index, col in enumerate(self.columns):
            if isinstance(col, DynamicTableRegion):
                col_names.append(col.name)
        return col_names

    def get_targets(self, include_self=False):
        """
        Get a list of the full table hierachy, i.e., recursively list all
        tables referenced in the hierarchy.

        Returns: List of DynamicTabl objects

        """
        hcol_name = self.get_hierarchy_column_name()
        hcol = self[hcol_name]
        hcol_target = hcol.table if isinstance(hcol, DynamicTableRegion) else hcol.target.table
        if isinstance(hcol_target, HierarchicalDynamicTableMixin):
            re = [self, ] if include_self else []
            re += [hcol_target, ]
            re += hcol_target.get_targets()
            return re
        else:
            return [hcol_target, ]

    def to_denormalized_dataframe(self, flat_column_index=False):
        """
        Shorthand for 'self.to_hierarchical_dataframe().reset_index()'

        The function denormalizes the hierarchical table and represents all data as
        columns in the resulting dataframe.
        """
        def get_first_prefix(instr, prefixs):
            """Internal helper function to find the first prefix that matches"""
            for p in prefixs:
                if instr.startswith(p):
                    return p
            return prefixs[-1]

        def remove_prefix(instr, prefix):
            """Internal helper function to remove the first prefix that matches"""

            if instr.startswith(prefix):
                return instr[len(prefix):]
            return instr

        hier_df = self.to_hierarchical_dataframe(flat_column_index=True)
        flat_df = hier_df.reset_index()
        if not flat_column_index:
            table_names = [t.name for t in self.get_targets(include_self=True)]
            mi_tuples = [(get_first_prefix(n, table_names),
                          remove_prefix(n, get_first_prefix(n, table_names)+"_")) for n in flat_df.columns]
            flat_df.columns = pd.MultiIndex.from_tuples(mi_tuples, names=('source_table', 'label'))

        return flat_df

    def to_hierarchical_dataframe(self, flat_column_index=False):
        """
        Create a Pandas dataframe with a hierarchical MultiIndex index that represents the
        hierarchical dynamic table.
        """
        # Get the references column
        hcol_name = self.get_hierarchy_column_name()
        hcol = self[hcol_name]
        hcol_target = hcol.table if isinstance(hcol, DynamicTableRegion) else hcol.target.table

        # Create the data variables we need to collect the data for our output dataframe and associated index
        index = []
        data = []
        columns = None
        index_names = None

        # Case 1:  Our DynamicTableRegion column points to a regular DynamicTable
        #          If this is the case than we need to de-normalize the data and flatten the hierarcht
        if not isinstance(hcol_target, HierarchicalDynamicTableMixin):
            # 1) Iterate over all rows in our hierarchcial columns (i.e,. the DynamicTableRegion column)
            for row_index, row_df in enumerate(hcol[:]):  # need hcol[:] here in case this is an h5py.Dataset
                # 1.1): Since hcol is a DynamicTableRegion, each row returns another DynamicTable so we
                #       next need to iterate over all rows in that table to denormalize our data
                for row in row_df.itertuples(index=True):
                    # 1.1.1) Determine the column data for our row. Each selected row from our target table
                    #        becomes a row in our flattened table
                    data.append(row)
                    # 1.1.2) Determine the multi-index tuple for our row, consisting of: i) id of the row in this
                    #        table, ii) all columns (except the hierarchical column we are flattening), and
                    #        iii) the index (i.e., id) from our target row
                    index_data = ([self.id[row_index], ] +
                                  [self[row_index, colname] for colname in self.colnames if colname != hcol_name])
                    index.append(tuple(index_data))
                    # Determine the names for our index and columns of our output table if this is the first row.
                    # These are constant for all rows so we only need to do this onle once for the first row.
                    if row_index == 0:
                        index_names = ([self.name + "_id", ] +
                                       [(self.name + "_" + colname)
                                        for colname in self.colnames if colname != hcol_name])
                        if flat_column_index:
                            columns = ['id', ] + list(row_df.columns)
                        else:
                            columns = pd.MultiIndex.from_tuples([(hcol_target.name, 'id'), ] +
                                                                [(hcol_target.name, c) for c in row_df.columns],
                                                                names=('source_table', 'label'))

        # Case 2:  Our DynamicTableRegion columns points to another HierarchicalDynamicTable.
        else:
            # 1) First we need to recursively flatten the hierarchy by calling 'to_hierarchical_dataframe()'
            #    (i.e., this function) on the target of our hierarchical column
            hcol_hdf = hcol_target.to_hierarchical_dataframe(flat_column_index=flat_column_index)
            # 2) Iterate over all rows in our hierarchcial columns (i.e,. the DynamicTableRegion column)
            for row_index, row_df_level1 in enumerate(hcol[:]):   # need hcol[:] here  in case this is an h5py.Dataset
                # 1.1): Since hcol is a DynamicTableRegion, each row returns another DynamicTable so we
                #       next need to iterate over all rows in that table to denormalize our data
                for row_df_level2 in row_df_level1.itertuples(index=True):
                    # 1.1.2) Since our target is itself a HierarchicalDynamicTable each target row itself
                    #        may expand into multiple rows in flattened hcol_hdf. So we now need to look
                    #        up the rows in hcol_hdf that correspond to the rows in row_df_level2.
                    #        NOTE: In this look-up we assume that the ids (and hence the index) of
                    #              each row in the table are in fact unique.
                    for row_tuple_level3 in hcol_hdf.loc[[row_df_level2[0]]].itertuples(index=True):
                        # 1.1.2.1) Determine the column data for our row.
                        data.append(row_tuple_level3[1:])
                        # 1.1.2.2) Determine the multi-index tuple for our row,
                        index_data = ([self.id[row_index], ] +
                                      [self[row_index, colname] for colname in self.colnames if colname != hcol_name] +
                                      list(row_tuple_level3[0]))
                        index.append(tuple(index_data))
                        # Determine the names for our index and columns of our output table if this is the first row
                        if row_index == 0:
                            index_names = ([self.name + "_id"] +
                                           [(self.name + "_" + colname)
                                            for colname in self.colnames if colname != hcol_name] +
                                           hcol_hdf.index.names)
                            columns = hcol_hdf.columns

        # Construct the pandas dataframe with the hierarchical multi-index
        multi_index = pd.MultiIndex.from_tuples(index, names=index_names)
        out_df = pd.DataFrame(data=data, index=multi_index, columns=columns)
        return out_df


@register_class('IntracellularRecordingsTable', namespace)
class IntracellularRecordingsTable(DynamicTable):
    """
    A table to group together a stimulus and response from a single electrode and
    a single simultaneous_recording. Each row in the table represents a single recording consisting
    typically of a stimulus and a corresponding response.
    """

    __columns__ = (
        {'name': 'stimulus',
         'description': 'Column storing the reference to the recorded stimulus for the recording (rows)',
         'required': True,
         'index': False},
        {'name': 'response',
         'description': 'Column storing the reference to the recorded response for the recording (rows)',
         'required': True,
         'index': False},
        {'name': 'electrode',
         'description': 'Column for storing the reference to the intracellular electrode',
         'required': True,
         'index': False},
    )

    @docval(*get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        kwargs['name'] = 'intracellular_recordings'
        kwargs['description'] = ('A table to group together a stimulus and response from a single electrode and'
                                 'a single simultaneous_recording. Each row in the table represents a single recording consisting'
                                 'typically of a stimulus and a corresponding response.')
        call_docval_func(super(IntracellularRecordingsTable, self).__init__, kwargs)

    @docval({'name': 'electrode', 'type': IntracellularElectrode, 'doc': 'The intracellular electrode used'},
            {'name': 'stimulus_start_index', 'type': 'int', 'doc': 'Start index of the stimulus', 'default': -1},
            {'name': 'stimulus_index_count', 'type': 'int', 'doc': 'Stop index of the stimulus', 'default': -1},
            {'name': 'stimulus', 'type': TimeSeries,
             'doc': 'The TimeSeries (usually a PatchClampSeries) with the stimulus',
             'default': None},
            {'name': 'response_start_index', 'type': 'int', 'doc': 'Start index of the response', 'default': -1},
            {'name': 'response_index_count', 'type': 'int', 'doc': 'Stop index of the response', 'default': -1},
            {'name': 'response', 'type': TimeSeries,
             'doc': 'The TimeSeries (usually a PatchClampSeries) with the response',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_recording(self, **kwargs):
        """
        Add a single recording to the IntracellularRecordingsTable table.

        Typically, both stimulus and response are expected. However, in some cases only a stimulus
        or a resposne may be recodred as part of a recording. In this case, None, may be given
        for either stimulus or response, but not both. Internally, this results in both stimulus
        and response pointing to the same timeseries, while the start_index and index_count for
        the invalid series will both be set to -1.
        """
        # Get the input data
        stimulus_start_index, stimulus_index_count, stimulus = popargs('stimulus_start_index',
                                                                       'stimulus_index_count',
                                                                       'stimulus',
                                                                       kwargs)
        response_start_index, response_index_count, response = popargs('response_start_index',
                                                                       'response_index_count',
                                                                       'response',
                                                                       kwargs)
        electrode = popargs('electrode', kwargs)
        # Confirm that we have at least a valid stimulus or response
        if stimulus is None and response is None:
            raise ValueError("stimulus and response cannot both be None.")

        # Compute the start and stop index if necessary
        if stimulus is not None:
            stimulus_start_index = stimulus_start_index if stimulus_start_index >= 0 else 0
            stimulus_num_samples = stimulus.num_samples
            stimulus_index_count = (stimulus_index_count
                                    if stimulus_index_count >= 0
                                    else (stimulus_num_samples - stimulus_start_index))
            if stimulus_index_count is None:
                raise IndexError("Invalid stimulus_index_count cannot be determined from stimulus data.")
            if stimulus_num_samples is not None:
                if stimulus_start_index >= stimulus_num_samples:
                    raise IndexError("stimulus_start_index out of range")
                if (stimulus_start_index + stimulus_index_count) > stimulus_num_samples:
                    raise IndexError("stimulus_start_index+stimulus_index_count out of range")
        if response is not None:
            response_start_index = response_start_index if response_start_index >= 0 else 0
            response_num_samples = response.num_samples
            response_index_count = (response_index_count
                                    if response_index_count >= 0
                                    else (response_num_samples - response_start_index))
            if response_index_count is None:
                raise IndexError("Invalid response_index_count cannot be determined from stimulus data.")
            if response_num_samples is not None:
                if response_start_index > response_num_samples:
                    raise IndexError("response_start_index out of range")
                if (response_start_index + response_index_count) > response_num_samples:
                    raise IndexError("response_start_index+response_index_count out of range")

        # If either stimulus or response are None, then set them to the same TimeSeries to keep the I/O happy
        response = response if response is not None else stimulus
        stimulus = stimulus if stimulus is not None else response

        # Make sure the types are compatible
        if ((response.neurodata_type.startswith("CurrentClamp") and
                stimulus.neurodata_type.startswith("VoltageClamp")) or
                (response.neurodata_type.startswith("VoltageClamp") and
                 stimulus.neurodata_type.startswith("CurrentClamp"))):
            raise ValueError("Incompatible types given for 'stimulus' and 'response' parameters.' "
                             "'stimulus' is of type %s and 'response' is of type %s." %
                             (stimulus.neurodata_type, response.neurodata_type))

        # Add the row to the table
        row_kwargs = {'electrode': electrode,
                      'stimulus': (stimulus_start_index, stimulus_index_count, stimulus),
                      'response': (response_start_index, response_index_count, response)}
        row_kwargs.update(kwargs)
        _ = super(IntracellularRecordingsTable, self).add_row(enforce_unique_id=True, **row_kwargs)
        return len(self.id) - 1


@register_class('SimultaneousRecordingsTable', namespace)
class SimultaneousRecordingsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recordings from the
    IntracellularRecordingsTable table together that were recorded simultaneously
    from different electrodes.
    """

    __columns__ = (
        {'name': 'recordings',
         'description': 'Column with a references to one or more rows in the IntracellularRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'intracellular_recordings_table',
             'type': IntracellularRecordingsTable,
             'doc': 'the IntracellularRecordingsTable table that the recordings column indexes. May be None when '
                    'reading the Container from file as the table attribute is already populated in this case '
                    'but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        intracellular_recordings_table = popargs('intracellular_recordings_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'simultaneous_recordings'
        kwargs['description'] = ('A table for grouping different intracellular recordings from the'
                                 'IntracellularRecordingsTable table together that were recorded simultaneously '
                                 'from different electrodes.')
        # Initialize the DynamicTable
        call_docval_func(super(SimultaneousRecordingsTable, self).__init__, kwargs)
        if self['recordings'].target.table is None:
            if intracellular_recordings_table is not None:
                self['recordings'].target.table = intracellular_recordings_table
            else:
                raise ValueError("intracellular_recordings constructor argument required")

    @docval({'name': 'recordings',
             'type': 'array_data',
             'doc': 'the indices of the recordings belonging to this simultaneous recording',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_simultaneous_recording(self, **kwargs):
        """
        Add a single Sweep consisting of one-or-more recordings and associated custom
        SimultaneousRecordingsTable metadata to the table.
        """
        # Check recordings
        recordings = getargs('recordings', kwargs)
        if recordings is None:
            kwargs['recordings'] = []
        _ = super(SimultaneousRecordingsTable, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('SequentialRecordingsTable', namespace)
class SequentialRecordingsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording simultaneous_recordings from the
    SimultaneousRecordingsTable table together. This is typically used to group together simultaneous_recordings
    where the a sequence of stimuli of the same type with varying parameters
    have been presented in a sequence.
    """

    __columns__ = (
        {'name': 'simultaneous_recordings',
         'description': 'Column with a references to one or more rows in the SimultaneousRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
        {'name': 'stimulus_type',
         'description': 'Column storing the type of stimulus used for the sequential recording',
         'required': True,
         'index': False,
         'table': False}
    )

    @docval({'name': 'simultaneous_recordings_table',
             'type': SimultaneousRecordingsTable,
             'doc': 'the SimultaneousRecordingsTable table that the simultaneous_recordings column indexes. May be None when '
                    'reading the Container from file as the table attribute is already '
                    'populated in this case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        simultaneous_recordings_table = popargs('simultaneous_recordings_table', kwargs)
        # Define defaultb name and description settings
        kwargs['name'] = 'sequential_recordings'
        kwargs['description'] = ('A table for grouping different intracellular recording simultaneous_recordings from the '
                                 'SimultaneousRecordingsTable table together. This is typically used to group together simultaneous_recordings '
                                 'where the a sequence of stimuli of the same type with varying parameters '
                                 'have been presented in a sequence.')
        # Initialize the DynamicTable
        call_docval_func(super(SequentialRecordingsTable, self).__init__, kwargs)
        if self['simultaneous_recordings'].target.table is None:
            if simultaneous_recordings_table is not None:
                self['simultaneous_recordings'].target.table = simultaneous_recordings_table
            else:
                raise ValueError('simultaneous_recordings_table constructor argument required')

    @docval({'name': 'stimulus_type',
             'type': str,
             'doc': 'the type of stimulus used for the sequential recording'},
            {'name': 'simultaneous_recordings',
             'type': 'array_data',
             'doc': 'the indices of the simultaneous_recordings belonging to this sequential recording',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_sequential_recording(self, **kwargs):
        """
        Add a sequential recording (i.e., one row)  consisting of one-or-more recording simultaneous_recordings
        and associated custom sequential recording  metadata to the table.
        """
        # Check recordings
        simultaneous_recordings = getargs('simultaneous_recordings', kwargs)
        if simultaneous_recordings is None:
            kwargs[''] = []
        _ = super(SequentialRecordingsTable, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('RepetitionsTable', namespace)
class RepetitionsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording sequential recordings together.
    With each SweepSequence typically representing a particular type of stimulus, the
    RepetitionsTable table is typically used to group sets of stimuli applied in sequence.
    """

    __columns__ = (
        {'name': 'sequential_recordings',
         'description': 'Column with a references to one or more rows in the SequentialRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'sequential_recordings_table',
             'type': SequentialRecordingsTable,
             'doc': 'the SequentialRecordingsTable table that the sequential_recordings column indexes. May be None when '
                    'reading the Container from file as the table attribute is already populated in this '
                    'case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        sequential_recordings_table = popargs('sequential_recordings_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'repetitions'
        kwargs['description'] = ('A table for grouping different intracellular recording sequential recordings together.'
                                 'With each SweepSequence typically representing a particular type of stimulus, the '
                                 'RepetitionsTable table is typically used to group sets of stimuli applied in sequence.')
        # Initialize the DynamicTable
        call_docval_func(super(RepetitionsTable, self).__init__, kwargs)
        if self['sequential_recordings'].target.table is None:
            if sequential_recordings_table is not None:
                self['sequential_recordings'].target.table = sequential_recordings_table
            else:
                raise ValueError('sequential_recordings_table constructor argument required')

    @docval({'name': 'sequential_recordings',
             'type': 'array_data',
             'doc': 'the indices of the sequential recordings belonging to this repetition',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_repetition(self, **kwargs):
        """
        Add a repetition (i.e., one row)  consisting of one-or-more recording sequential recordings
        and associated custom repetition  metadata to the table.
        """
        # Check recordings
        sequential_recordings = getargs('sequential_recordings', kwargs)
        if sequential_recordings is None:
            kwargs['sequential_recordings'] = []
        _ = super(RepetitionsTable, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('ExperimentalConditionsTable', namespace)
class ExperimentalConditionsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording repetitions together that
    belong to the same experimental conditions.
    """

    __columns__ = (
        {'name': 'repetitions',
         'description': 'Column with a references to one or more rows in the RepetitionsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'repetitions_table',
             'type': RepetitionsTable,
             'doc': 'the RepetitionsTable table that the repetitions column indexes',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        repetitions_table = popargs('repetitions_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'experimental_conditions'
        kwargs['description'] = ('A table for grouping different intracellular recording repetitions together that '
                                 'belong to the same experimental experimental_conditions.')
        # Initialize the DynamicTable
        call_docval_func(super(ExperimentalConditionsTable, self).__init__, kwargs)
        if self['repetitions'].target.table is None:
            if repetitions_table is not None:
                self['repetitions'].target.table = repetitions_table
            else:
                raise ValueError('repetitions_table constructor argument required')

    @docval({'name': 'repetitions',
             'type': 'array_data',
             'doc': 'the indices of the repetitions  belonging to this condition',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_experimental_condition(self, **kwargs):
        """
        Add a condition (i.e., one row)  consisting of one-or-more recording repetitions of sequential recordings
        and associated custom experimental_conditions  metadata to the table.
        """
        # Check recordings
        repetitions = getargs('repetitions', kwargs)
        if repetitions is None:
            kwargs['repetitions'] = []
        _ = super(ExperimentalConditionsTable, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('ICEphysFile', namespace)
class ICEphysFile(NWBFile):
    """
    Extension of the NWBFile class to allow placing the new icephys
    metadata types in /general/intracellular_ephys in the NWBFile
    NOTE: If this proposal for extension to NWB gets merged with
    the core schema, then this type would be removed and the
    NWBFile specification updated instead
    """

    __nwbfields__ = ({'name': 'intracellular_recordings',
                      'child': True,
                      'required_name': 'intracellular_recordings',
                      'doc': 'IntracellularRecordingsTable table to group together a stimulus and response '
                             'from a single intracellular electrode and a single simultaneous recording.'},
                     {'name': 'icephys_simultaneous_recordings',
                      'child': True,
                      'required_name': 'simultaneous_recordings',
                      'doc': 'SimultaneousRecordingsTable table for grouping different intracellular recordings from'
                             'the IntracellularRecordingsTable table together that were recorded simultaneously '
                             'from different electrodes'},
                     {'name': 'icephys_sequential_recordings',
                      'child': True,
                      'required_name': 'sequential_recordings',
                      'doc': 'A table for grouping different simultaneous intracellular recording from the '
                             'SimultaneousRecordingsTable table together. This is typically used to group together simultaneous recordings '
                             'where the a sequence of stimuli of the same type with varying parameters '
                             'have been presented in a sequence.'},
                     {'name': 'icephys_repetitions',
                      'child': True,
                      'required_name': 'repetitions',
                      'doc': 'A table for grouping different intracellular recording sequential recordings together.'
                             'With each SweepSequence typically representing a particular type of stimulus, the '
                             'RepetitionsTable table is typically used to group sets of stimuli applied in sequence.'},
                     {'name': 'icephys_experimental_conditions',
                      'child': True,
                      'required_name': 'experimental_conditions',
                      'doc': 'A table for grouping different intracellular recording repetitions together that '
                             'belong to the same experimental experimental_conditions.'},
                     )

    @docval(*get_docval(NWBFile.__init__),
            {'name': 'intracellular_recordings', 'type': IntracellularRecordingsTable, 'default': None,
             'doc': 'the IntracellularRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_simultaneous_recordings', 'type': SimultaneousRecordingsTable, 'default': None,
             'doc': 'the SimultaneousRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_sequential_recordings', 'type': SequentialRecordingsTable, 'default': None,
             'doc': 'the SequentialRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_repetitions', 'type': RepetitionsTable, 'default': None,
             'doc': 'the RepetitionsTable table that belongs to this NWBFile'},
            {'name': 'icephys_experimental_conditions', 'type': ExperimentalConditionsTable, 'default': None,
             'doc': 'the ExperimentalConditionsTable table that belongs to this NWBFile'},
            {'name': 'ic_filtering', 'type': str, 'default': None,
             'doc': '[DEPRECATED] Use IntracellularElectrode.filtering instead. Description of filtering used.'})
    def __init__(self, **kwargs):
        # Get the arguments to pass to NWBFile and remove arguments custum to this class
        intracellular_recordings = kwargs.pop('intracellular_recordings', None)
        icephys_simultaneous_recordings = kwargs.pop('icephys_simultaneous_recordings', None)
        icephys_sequential_recordings = kwargs.pop('icephys_sequential_recordings', None)
        icephys_repetitions = kwargs.pop('icephys_repetitions', None)
        icephys_experimental_conditions = kwargs.pop('icephys_experimental_conditions', None)
        if kwargs.get('sweep_table') is not None:
            warnings.warn("Use of SweepTable is deprecated. Use the intracellular_recordings, "
                          "simultaneous_recordings, sequential_recordings, repetitions and/or experimental_conditions table(s) instead.", DeprecationWarning)
        # Initialize the NWBFile parent class
        pargs, pkwargs = fmt_docval_args(super(ICEphysFile, self).__init__, kwargs)
        super(ICEphysFile, self).__init__(*pargs, **pkwargs)
        # Set ic filtering if requested
        self.ic_filtering = kwargs.get('ic_filtering')
        # Set the intracellular_recordings if available
        setattr(self, 'intracellular_recordings', intracellular_recordings)
        setattr(self, 'icephys_simultaneous_recordings', icephys_simultaneous_recordings)
        setattr(self, 'icephys_sequential_recordings', icephys_sequential_recordings)
        setattr(self, 'icephys_repetitions', icephys_repetitions)
        setattr(self, 'icephys_experimental_conditions', icephys_experimental_conditions)

    @property
    def ic_filtering(self):
        return self.fields.get('ic_filtering')

    @ic_filtering.setter
    def ic_filtering(self, val):
        if val is not None:
            warnings.warn("Use of ic_filtering is deprecated. Use the IntracellularElectrode.filtering"
                          "field instead", DeprecationWarning)
            self.fields['ic_filtering'] = val

    @docval(*get_docval(NWBFile.add_stimulus),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_stimulus(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        timeseries = popargs('timeseries', kwargs)
        self._add_stimulus_internal(timeseries)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys)repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(timeseries)

    @docval(*get_docval(NWBFile.add_stimulus),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_stimulus_template(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        timeseries = popargs('timeseries', kwargs)
        self._add_stimulus_template_internal(timeseries)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys)repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(timeseries)

    @docval(*get_docval(NWBFile.add_acquisition),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_acquisition(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        nwbdata = popargs('nwbdata', kwargs)
        self._add_acquisition_internal(nwbdata)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys)repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(nwbdata)

    @docval(returns='The NWBFile.intracellular_recordings table', rtype=IntracellularRecordingsTable)
    def get_intracellular_recordings(self):
        """
        Get the NWBFile.intracellular_recordings table.

        In contrast to NWBFile.intracellular_recordings, this function will create the
        IntracellularRecordingsTable table if not yet done, whereas NWBFile.intracellular_recordings
        will return None if the table is currently not being used.
        """
        if self.intracellular_recordings is None:
            self.intracellular_recordings = IntracellularRecordingsTable()
        return self.intracellular_recordings

    @docval(*get_docval(IntracellularRecordingsTable.add_recording),
            returns='Integer index of the row that was added to IntracellularRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_intracellular_recording(self, **kwargs):
        """
        Add a intracellular recording to the intracellular_recordings table. If the
        electrode, stimulus, and/or response do not exsist yet in the NWBFile, then
        they will be added to this NWBFile before adding them to the table.
        """
        # Add the stimulus, response, and electrode to the file if they don't exist yet
        stimulus, response, electrode = getargs('stimulus', 'response', 'electrode', kwargs)
        if (stimulus is not None and
                (stimulus.name not in self.stimulus and
                 stimulus.name not in self.stimulus_template)):
            self.add_stimulus(stimulus, use_sweep_table=False)
        if response is not None and response.name not in self.acquisition:
            self.add_acquisition(response, use_sweep_table=False)
        if electrode is not None and electrode.name not in self.icephys_electrodes:
            self.add_icephys_electrode(electrode)
        # make sure the intracellular recordings table exists and if not create it using get_intracellular_recordings
        # Add the recoding to the intracellular_recordings table
        return call_docval_func(self.get_intracellular_recordings().add_recording, kwargs)

    @docval(returns='The NWBFile.icephys_simultaneous_recordings table', rtype=SimultaneousRecordingsTable)
    def get_icephys_simultaneous_recordings(self):
        """
        Get the NWBFile.icephys_simultaneous_recordings table.

        In contrast to NWBFile.icephys_simultaneous_recordings, this function will create the
        SimultaneousRecordingsTable table if not yet done, whereas NWBFile.icephys_simultaneous_recordings
        will return None if the table is currently not being used.
        """
        if self.icephys_simultaneous_recordings is None:
            self.icephys_simultaneous_recordings = SimultaneousRecordingsTable(self.get_intracellular_recordings())
        return self.icephys_simultaneous_recordings

    @docval(*get_docval(SimultaneousRecordingsTable.add_simultaneous_recording),
            returns='Integer index of the row that was added to SimultaneousRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_simultaneous_recording(self, **kwargs):
        """
        Add a new simultaneous recording to the icephys_simultaneous_recordings table
        """
        return call_docval_func(self.get_icephys_simultaneous_recordings().add_simultaneous_recording, kwargs)

    @docval(returns='The NWBFile.icephys_sequential_recordings table', rtype=SequentialRecordingsTable)
    def get_icephys_sequential_recordings(self):
        """
        Get the NWBFile.icephys_sequential_recordings table.

        In contrast to NWBFile.icephys_sequential_recordings, this function will create the
        IntracellularRecordingsTable table if not yet done, whereas NWBFile.icephys_sequential_recordings
        will return None if the table is currently not being used.
        """
        if self.icephys_sequential_recordings is None:
            self.icephys_sequential_recordings = SequentialRecordingsTable(self.get_icephys_simultaneous_recordings())
        return self.icephys_sequential_recordings

    @docval(*get_docval(SequentialRecordingsTable.add_sequential_recording),
            returns='Integer index of the row that was added to SequentialRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_sequential_recording(self, **kwargs):
        """
        Add a new sequential recording to the icephys_sequential_recordings table
        """
        self.get_icephys_sequential_recordings()
        return call_docval_func(self.icephys_sequential_recordings.add_sequential_recording, kwargs)

    @docval(returns='The NWBFile.icephys_repetitions table', rtype=RepetitionsTable)
    def get_icephys_repetitions(self):
        """
        Get the NWBFile.icephys_repetitions table.

        In contrast to NWBFile.icephys_repetitions, this function will create the
        RepetitionsTable table if not yet done, whereas NWBFile.icephys_repetitions
        will return None if the table is currently not being used.
        """
        if self.icephys_repetitions is None:
            self.icephys_repetitions = RepetitionsTable(self.get_icephys_sequential_recordings())
        return self.icephys_repetitions

    @docval(*get_docval(RepetitionsTable.add_repetition),
            returns='Integer index of the row that was added to RepetitionsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_repetition(self, **kwargs):
        """
        Add a new repetition to the RepetitionsTable table
        """
        return call_docval_func(self.get_icephys_repetitions().add_repetition, kwargs)

    @docval(returns='The NWBFile.icephys_experimental_conditions table', rtype=ExperimentalConditionsTable)
    def get_icephys_experimental_conditions(self):
        """
        Get the NWBFile.icephys_experimental_conditions table.

        In contrast to NWBFile.icephys_experimental_conditions, this function will create the
        RepetitionsTable table if not yet done, whereas NWBFile.icephys_experimental_conditions
        will return None if the table is currently not being used.
        """
        if self.icephys_experimental_conditions is None:
            self.icephys_experimental_conditions = ExperimentalConditionsTable(self.get_icephys_repetitions())
        return self.icephys_experimental_conditions

    @docval(*get_docval(ExperimentalConditionsTable.add_experimental_condition),
            returns='Integer index of the row that was added to ExperimentalConditionsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_experimental_condition(self, **kwargs):
        """
        Add a new condition to the ExperimentalConditionsTable table
        """
        return call_docval_func(self.get_icephys_experimental_conditions().add_experimental_condition, kwargs)

    def get_icephys_meta_parent_table(self):
        """
        Get the top-most table in the intracellular ephys metadata table hierarchy that exists in this NWBFile.

        The intracellular ephys metadata consists of a hierarchy of DynamicTables, i.e.,
        experimental_conditions --> repetitions --> sequential_recordings --> simultaneous_recordings --> intracellular_recordings etc.
        In a given NWBFile not all tables may exist. This convenience functions returns the top-most
        table that exists in this file. E.g., if the file contains only the simultaneous_recordings and intracellular_recordings
        tables then the function would return the simultaneous_recordings table. Similarly, if the file contains all tables
        then it will return the experimental_conditions table.

        :returns: DynamicTable object or None
        """
        if self.icephys_experimental_conditions is not None:
            return self.icephys_experimental_conditions
        elif self.icephys_repetitions is not None:
            return self.icephys_repetitions
        elif self.icephys_sequential_recordings is not None:
            return self.icephys_sequential_recordings
        elif self.icephys_simultaneous_recordings is not None:
            return self.icephys_simultaneous_recordings
        elif self.intracellular_recordings is not None:
            return self.intracellular_recordings
        else:
            return None
