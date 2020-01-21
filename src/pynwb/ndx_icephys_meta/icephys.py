from pynwb import register_class
from pynwb.file import NWBFile
from pynwb.icephys import IntracellularElectrode
from pynwb.base import TimeSeries
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


@register_class('IntracellularRecordings', namespace)
class IntracellularRecordings(DynamicTable):
    """
    A table to group together a stimulus and response from a single electrode and
    a single sweep. Each row in the table represents a single recording consisting
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
                                 'a single sweep. Each row in the table represents a single recording consisting'
                                 'typically of a stimulus and a corresponding response.')
        call_docval_func(super(IntracellularRecordings, self).__init__, kwargs)

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
        Add a single recording to the IntracellularRecordings table.

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

        # Add the row to the table
        row_kwargs = {'electrode': electrode,
                      'stimulus': (stimulus_start_index, stimulus_index_count, stimulus),
                      'response': (response_start_index, response_index_count, response)}
        row_kwargs.update(kwargs)
        _ = super(IntracellularRecordings, self).add_row(enforce_unique_id=True, **row_kwargs)
        return len(self.id) - 1


@register_class('Sweeps', namespace)
class Sweeps(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recordings from the
    IntracellularRecordings table together that were recorded simultaneously
    from different electrodes.
    """

    __columns__ = (
        {'name': 'recordings',
         'description': 'Column with a references to one or more rows in the IntracellularRecordings table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'intracellular_recordings_table',
             'type': IntracellularRecordings,
             'doc': 'the IntracellularRecordings table that the recordings column indexes. May be None when '
                    'reading the Container from file as the table attribute is already populated in this case '
                    'but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        intracellular_recordings_table = popargs('intracellular_recordings_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'sweeps'
        kwargs['description'] = ('A table for grouping different intracellular recordings from the'
                                 'IntracellularRecordings table together that were recorded simultaneously '
                                 'from different electrodes.')
        # Initialize the DynamicTable
        call_docval_func(super(Sweeps, self).__init__, kwargs)
        if self['recordings'].target.table is None:
            if intracellular_recordings_table is not None:
                self['recordings'].target.table = intracellular_recordings_table
            else:
                raise ValueError("intracellular_recordings constructor argument required")

    @docval({'name': 'recordings',
             'type': 'array_data',
             'doc': 'the indices of the recordings belonging to this sweep',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_sweep(self, **kwargs):
        """
        Add a single Sweep consisting of one-or-more recordings and associated custom
        Sweeps metadata to the table.
        """
        # Check recordings
        recordings = getargs('recordings', kwargs)
        if recordings is None:
            kwargs['recordings'] = []
        _ = super(Sweeps, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('SweepSequences', namespace)
class SweepSequences(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording sweeps from the
    Sweeps table together. This is typically used to group together sweeps
    where the a sequence of stimuli of the same type with varying parameters
    have been presented in a sequence.
    """

    __columns__ = (
        {'name': 'sweeps',
         'description': 'Column with a references to one or more rows in the Sweeps table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'sweeps_table',
             'type': Sweeps,
             'doc': 'the Sweeps table that the sweeps column indexes. May be None when '
                    'reading the Container from file as the table attribute is already '
                    'populated in this case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        sweeps_table = popargs('sweeps_table', kwargs)
        # Define defaultb name and description settings
        kwargs['name'] = 'sweep_sequences'
        kwargs['description'] = ('A table for grouping different intracellular recording sweeps from the '
                                 'Sweeps table together. This is typically used to group together sweeps '
                                 'where the a sequence of stimuli of the same type with varying parameters '
                                 'have been presented in a sequence.')
        # Initialize the DynamicTable
        call_docval_func(super(SweepSequences, self).__init__, kwargs)
        if self['sweeps'].target.table is None:
            if sweeps_table is not None:
                self['sweeps'].target.table = sweeps_table
            else:
                raise ValueError('sweeps_table constructor argument required')

    @docval({'name': 'sweeps',
             'type': 'array_data',
             'doc': 'the indices of the sweeps belonging to this sweep sequence',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_sweep_sequence(self, **kwargs):
        """
        Add a sweep sequence (i.e., one row)  consisting of one-or-more recording sweeps
        and associated custom sweep sequence  metadata to the table.
        """
        # Check recordings
        sweeps = getargs('sweeps', kwargs)
        if sweeps is None:
            kwargs['sweeps'] = []
        _ = super(SweepSequences, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('Runs', namespace)
class Runs(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording sweep sequences together.
    With each SweepSequence typically representing a particular type of stimulus, the
    Runs table is typically used to group sets of stimuli applied in sequence.
    """

    __columns__ = (
        {'name': 'sweep_sequences',
         'description': 'Column with a references to one or more rows in the SweepSequences table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'sweep_sequences_table',
             'type': SweepSequences,
             'doc': 'the SweepSequences table that the sweep_sequences column indexes. May be None when '
                    'reading the Container from file as the table attribute is already populated in this '
                    'case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        sweep_sequences_table = popargs('sweep_sequences_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'runs'
        kwargs['description'] = ('A table for grouping different intracellular recording sweep sequences together.'
                                 'With each SweepSequence typically representing a particular type of stimulus, the '
                                 'Runs table is typically used to group sets of stimuli applied in sequence.')
        # Initialize the DynamicTable
        call_docval_func(super(Runs, self).__init__, kwargs)
        if self['sweep_sequences'].target.table is None:
            if sweep_sequences_table is not None:
                self['sweep_sequences'].target.table = sweep_sequences_table
            else:
                raise ValueError('sweep_sequences_table constructor argument required')

    @docval({'name': 'sweep_sequences',
             'type': 'array_data',
             'doc': 'the indices of the sweep sequences belonging to this run',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_run(self, **kwargs):
        """
        Add a run (i.e., one row)  consisting of one-or-more recording sweep sequences
        and associated custom run  metadata to the table.
  """
        # Check recordings
        sweep_sequences = getargs('sweep_sequences', kwargs)
        if sweep_sequences is None:
            kwargs['sweep_sequences'] = []
        _ = super(Runs, self).add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('Conditions', namespace)
class Conditions(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording runs together that
    belong to the same experimental conditions.
    """

    __columns__ = (
        {'name': 'runs',
         'description': 'Column with a references to one or more rows in the Runs table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'runs_table',
             'type': Runs,
             'doc': 'the Runs table that the runs column indexes',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        runs_table = popargs('runs_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'conditions'
        kwargs['description'] = ('A table for grouping different intracellular recording runs together that '
                                 'belong to the same experimental conditions.')
        # Initialize the DynamicTable
        call_docval_func(super(Conditions, self).__init__, kwargs)
        if self['runs'].target.table is None:
            if runs_table is not None:
                self['runs'].target.table = runs_table
            else:
                raise ValueError('runs_table constructor argument required')

    @docval({'name': 'runs',
             'type': 'array_data',
             'doc': 'the indices of the runs  belonging to this condition',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_condition(self, **kwargs):
        """
        Add a condition (i.e., one row)  consisting of one-or-more recording runs of sweep sequences
        and associated custom conditions  metadata to the table.
        """
        # Check recordings
        runs = getargs('runs', kwargs)
        if runs is None:
            kwargs['runs'] = []
        _ = super(Conditions, self).add_row(enforce_unique_id=True, **kwargs)
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
                      'doc': 'IntracellularRecordings table to group together a stimulus and response '
                             'from a single intracellular electrode and a single sweep.'},
                     {'name': 'ic_sweeps',
                      'child': True,
                      'required_name': 'sweeps',
                      'doc': 'Sweeps table for grouping different intracellular recordings from the '
                              'IntracellularRecordings table together that were recorded simultaneously '
                              'from different electrodes'},
                     {'name': 'ic_sweep_sequences',
                      'child': True,
                      'required_name': 'sweep_sequences',
                      'doc': 'A table for grouping different intracellular recording sweeps from the '
                             'Sweeps table together. This is typically used to group together sweeps '
                             'where the a sequence of stimuli of the same type with varying parameters '
                             'have been presented in a sequence.'},
                     {'name': 'ic_runs',
                      'child': True,
                      'required_name': 'runs',
                      'doc': 'A table for grouping different intracellular recording sweep sequences together.'
                             'With each SweepSequence typically representing a particular type of stimulus, the '
                             'Runs table is typically used to group sets of stimuli applied in sequence.'},
                     {'name': 'ic_conditions',
                      'child': True,
                      'required_name': 'conditions',
                      'doc': 'A table for grouping different intracellular recording runs together that '
                             'belong to the same experimental conditions.'},
                     )

    @docval(*get_docval(NWBFile.__init__),
            {'name': 'intracellular_recordings', 'type': IntracellularRecordings,  'default': None,
             'doc': 'the IntracellularRecordings table that belongs to this NWBFile'},
            {'name': 'ic_sweeps', 'type': Sweeps, 'default': None,
             'doc': 'the Sweeps table that belongs to this NWBFile'},
            {'name': 'ic_sweep_sequences', 'type': SweepSequences, 'default': None,
             'doc': 'the SweepSequences table that belongs to this NWBFile'},
            {'name': 'ic_runs', 'type': Runs, 'default': None,
             'doc': 'the Runs table that belongs to this NWBFile'},
            {'name': 'ic_conditions', 'type': Conditions, 'default': None,
             'doc': 'the Conditions table that belongs to this NWBFile'},
            {'name': 'ic_filtering', 'type': str, 'default': None,
             'doc': '[DEPRECATED] Use IntracellularElectrode.filtering instead. Description of filtering used.'})
    def __init__(self, **kwargs):
        # Get the arguments to pass to NWBFile and remove arguments custum to this class
        intracellular_recordings = kwargs.pop('intracellular_recordings', None)
        ic_sweeps = kwargs.pop('ic_sweeps', None)
        ic_sweep_sequences = kwargs.pop('ic_sweep_sequences', None)
        ic_runs = kwargs.pop('ic_runs', None)
        ic_conditions = kwargs.pop('ic_conditions', None)
        if kwargs.get('sweep_table') is not None:
            warnings.warn("Use of SweepTable is deprecated. Use the intracellular_recordings, "
                          "sweeps, sweep_sequences, runs and/or conditions table(s) instead.", DeprecationWarning)
        # Initialize the NWBFile parent class
        pargs, pkwargs = fmt_docval_args(super(ICEphysFile, self).__init__, kwargs)
        super(ICEphysFile, self).__init__(*pargs, **pkwargs)
        # Set ic filtering if requested
        self.ic_filtering = kwargs.get('ic_filtering')
        # Set the intracellular_recordings if available
        setattr(self, 'intracellular_recordings', intracellular_recordings)
        setattr(self, 'ic_sweeps', ic_sweeps)
        setattr(self, 'ic_sweep_sequences', ic_sweep_sequences)
        setattr(self, 'ic_runs', ic_runs)
        setattr(self, 'ic_conditions', ic_conditions)

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
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordings, "
                              "Sweeps tables instead. See the add_intracellular_recordings, "
                              "add_sweep, add_sweep_sequence, add_run, add_ic_condition functions.",
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
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordings, "
                              "Sweeps tables instead. See the add_intracellular_recordings, "
                              "add_sweep, add_sweep_sequence, add_run, add_ic_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(nwbdata)

    @docval(returns='The NWBFile.intracellular_recordings table', rtype=IntracellularRecordings)
    def get_intracellular_recordings(self):
        """
        Get the NWBFile.intracellular_recordings table.

        In contrast to NWBFile.intracellular_recordings, this function will create the
        IntracellularRecordings table if not yet done, whereas NWBFile.intracellular_recordings
        will return None if the table is currently not being used.
        """
        if self.intracellular_recordings is None:
            self.intracellular_recordings = IntracellularRecordings()
        return self.intracellular_recordings

    @docval(*get_docval(IntracellularRecordings.add_recording),
            returns='Integer index of the row that was added to IntracellularRecordings',
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
        if stimulus is not None and stimulus.name not in self.stimulus:
            self.add_stimulus(stimulus, use_sweep_table=False)
        if response is not None and response.name not in self.acquisition:
            self.add_acquisition(response, use_sweep_table=False)
        if electrode is not None and electrode.name not in self.ic_electrodes:
            self.add_ic_electrode(electrode)
        # make sure the intracellular recordings table exists and if not create it using get_intracellular_recordings
        # Add the recoding to the intracellular_recordings table
        return call_docval_func(self.get_intracellular_recordings().add_recording, kwargs)

    @docval(returns='The NWBFile.ic_sweeps table', rtype=Sweeps)
    def get_ic_sweeps(self):
        """
        Get the NWBFile.ic_sweeps table.

        In contrast to NWBFile.ic_sweeps, this function will create the
        Sweeps table if not yet done, whereas NWBFile.ic_sweeps
        will return None if the table is currently not being used.
        """
        if self.ic_sweeps is None:
            self.ic_sweeps = Sweeps(self.get_intracellular_recordings())
        return self.ic_sweeps

    @docval(*get_docval(Sweeps.add_sweep),
            returns='Integer index of the row that was added to Sweeps',
            rtype=int,
            allow_extra=True)
    def add_ic_sweep(self, **kwargs):
        """
        Add a new sweep to the ic_sweeps table
        """
        return call_docval_func(self.get_ic_sweeps().add_sweep, kwargs)

    @docval(returns='The NWBFile.ic_sweep_sequences table', rtype=SweepSequences)
    def get_ic_sweep_sequences(self):
        """
         Get the NWBFile.ic_sweep_sequences table.

        In contrast to NWBFile.ic_sweep_sequences, this function will create the
        IntracellularRecordings table if not yet done, whereas NWBFile.ic_sweep_sequences
        will return None if the table is currently not being used.
        """
        if self.ic_sweep_sequences is None:
            self.ic_sweep_sequences = SweepSequences(self.get_ic_sweeps())
        return self.ic_sweep_sequences

    @docval(*get_docval(SweepSequences.add_sweep_sequence),
            returns='Integer index of the row that was added to SweepSequences',
            rtype=int,
            allow_extra=True)
    def add_ic_sweep_sequence(self, **kwargs):
        """
        Add a new sweep sequence to the ic_sweep_sequences table
        """
        self.get_ic_sweep_sequences()
        return call_docval_func(self.ic_sweep_sequences.add_sweep_sequence, kwargs)

    @docval(returns='The NWBFile.ic_runs table', rtype=Runs)
    def get_ic_runs(self):
        """
        Get the NWBFile.ic_runs table.

        In contrast to NWBFile.ic_runs, this function will create the
        Runs table if not yet done, whereas NWBFile.ic_runs
        will return None if the table is currently not being used.
        """
        if self.ic_runs is None:
            self.ic_runs = Runs(self.get_ic_sweep_sequences())
        return self.ic_runs

    @docval(*get_docval(Runs.add_run),
            returns='Integer index of the row that was added to Runs',
            rtype=int,
            allow_extra=True)
    def add_ic_run(self, **kwargs):
        """
        Add a new run to the Runs table
        """
        return call_docval_func(self.get_ic_runs().add_run, kwargs)

    @docval(returns='The NWBFile.ic_conditions table', rtype=Conditions)
    def get_ic_conditions(self):
        """
        Get the NWBFile.ic_conditions table.

        In contrast to NWBFile.ic_conditions, this function will create the
        Runs table if not yet done, whereas NWBFile.ic_conditions
        will return None if the table is currently not being used.
        """
        if self.ic_conditions is None:
            self.ic_conditions = Conditions(self.get_ic_runs())
        return self.ic_conditions

    @docval(*get_docval(Conditions.add_condition),
            returns='Integer index of the row that was added to Conditions',
            rtype=int,
            allow_extra=True)
    def add_ic_condition(self, **kwargs):
        """
        Add a new condition to the Conditions table
        """
        return call_docval_func(self.get_ic_conditions().add_condition, kwargs)
