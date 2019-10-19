from pynwb import register_class
from pynwb.file import NWBFile
from pynwb.icephys import PatchClampSeries, IntracellularElectrode
from hdmf.common import DynamicTable
from hdmf.utils import docval, popargs, getargs, call_docval_func, get_docval, fmt_docval_args
import warnings

namespace = 'ndx-icephys-meta'


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
            {'name': 'stimulus', 'type': PatchClampSeries, 'doc': 'The PatchClampSeries with the stimulus',
             'default': None},
            {'name': 'response_start_index', 'type': 'int', 'doc': 'Start index of the response', 'default': -1},
            {'name': 'response_index_count', 'type': 'int', 'doc': 'Stop index of the response', 'default': -1},
            {'name': 'response', 'type': PatchClampSeries, 'doc': 'The PatchClampSeries with the response',
             'default': None},
            allow_extra=True)
    def add_recording(self, **kwargs):
        """
        Add a single recording to the IntracellularRecordings table.

        Typically, both stimulus and response are expected. However, in some cases only a stimulus
        or a resposne may be recodred as part of a recording. In this case, None, may be given
        for either stimulus or response, but not both. Internally, this results in both stimulus
        and response pointing to the same timeseries, while the start_index and index_count for
        the invalid series will both be set to -1.

        :returns: Result from DynamicTable.add_row(...) call

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

        # If either stimulus or response are None, then set them to the same PatchClampSeries to keep the I/O happy
        response = response if response is not None else stimulus
        stimulus = stimulus if stimulus is not None else response

        # Add the row to the table
        row_kwargs = {'electrode': electrode,
                      'stimulus': (stimulus_start_index, stimulus_index_count, stimulus),
                      'response': (response_start_index, response_index_count, response)}
        row_kwargs.update(kwargs)
        return super(IntracellularRecordings, self).add_row(**row_kwargs)


@register_class('Sweeps', namespace)
class Sweeps(DynamicTable):
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
            allow_extra=True)
    def add_sweep(self, **kwargs):
        """
        Add a single Sweep consisting of one-or-more recordings and associated custom
        Sweeps metadata to the table.

        :returns: Result from DynamicTable.add_row(...) call

        """
        # Check recordings
        recordings = getargs('recordings', kwargs)
        if recordings is None:
            kwargs['recordings'] = []
        re = super(Sweeps, self).add_row(**kwargs)
        return re


@register_class('SweepSequences', namespace)
class SweepSequences(DynamicTable):
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
            allow_extra=True)
    def add_sweep_sequence(self, **kwargs):
        """
        Add a sweep sequence (i.e., one row)  consisting of one-or-more recording sweeps
        and associated custom sweep sequence  metadata to the table.

        :returns: Result from DynamicTable.add_row(...) call

        """
        # Check recordings
        sweeps = getargs('sweeps', kwargs)
        if sweeps is None:
            kwargs['sweeps'] = []
        re = super(SweepSequences, self).add_row(**kwargs)
        return re


@register_class('Runs', namespace)
class Runs(DynamicTable):
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
            allow_extra=True)
    def add_run(self, **kwargs):
        """
        Add a run (i.e., one row)  consisting of one-or-more recording sweep sequences
        and associated custom run  metadata to the table.

        :returns: Result from DynamicTable.add_row(...) call

        """
        # Check recordings
        sweep_sequences = getargs('sweep_sequences', kwargs)
        if sweep_sequences is None:
            kwargs['sweep_sequences'] = []
        re = super(Runs, self).add_row(**kwargs)
        return re


@register_class('Conditions', namespace)
class Conditions(DynamicTable):
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
            allow_extra=True)
    def add_condition(self, **kwargs):
        """
        Add a condition (i.e., one row)  consisting of one-or-more recording runs of sweep sequences
        and associated custom conditions  metadata to the table.

        :returns: Result from DynamicTable.add_row(...) call

        """
        # Check recordings
        runs = getargs('runs', kwargs)
        if runs is None:
            kwargs['runs'] = []
        re = super(Conditions, self).add_row(**kwargs)
        return re


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
                             'belong to the same experimental conditions.'})

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
             'doc': 'the Conditions table that belongs to this NWBFile'})
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
        # Set the intracellular_recordings if available
        setattr(self, 'intracellular_recordings', intracellular_recordings)
        setattr(self, 'ic_sweeps', ic_sweeps)
        setattr(self, 'ic_sweep_sequences', ic_sweep_sequences)
        setattr(self, 'ic_runs', ic_runs)
        setattr(self, 'ic_conditions', ic_conditions)

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

    def _check_intracellular_recordings(self):
        """
        Create IntracellularRecordings table if not yet done
        """
        if self.intracellular_recordings is None:
            self.intracellular_recordings = IntracellularRecordings()

    @docval(*get_docval(IntracellularRecordings.add_column))
    def add_intracellular_recordings_column(self, **kwargs):
        """
        Add a column to the IntracellularRecordings table.
        See :py:meth:`~hdmf.common.DynamicTable.add_column` for more details
        """
        self._check_intracellular_recordings()
        call_docval_func(self.intracellular_recordings.add_column, kwargs)

    @docval(*get_docval(IntracellularRecordings.add_recording),
            allow_extra=True)
    def add_intracellular_recording(self, **kwargs):
        """
        Add a intracellular recording to the intracellular_recordings table. If the
        electrode, stimiulus, and/or response do not exsist yet in the NWBFile, then
        they will be added to this NWBFile before adding them to the table.
        """
        # Add the stimulus, response, and electrode to the file if they don't exist yet
        stimulus, response, electrode = getargs('stimulus', 'response', 'electrode', kwargs)
        if stimulus.name not in self.stimulus:
            self.add_stimulus(stimulus, use_sweep_table=False)
        if response.name not in self.acquisition:
            self.add_acquisition(response, use_sweep_table=False)
        if electrode.name not in self.ic_electrodes:
            self.add_ic_electrode(electrode)
        # make sure the intracellular recordings table exists and if not create it
        self._check_intracellular_recordings()
        # Add the recoding to the intracellular_recordings table
        call_docval_func(self.intracellular_recordings.add_recording, kwargs)

    def _check_ic_sweeps(self):
        """
        Create the Sweeps (and IntracellularRecordings) table if not yet done
        """
        if self.ic_sweeps is None:
            self._check_intracellular_recordings()
            self.ic_sweeps = Sweeps(self.intracellular_recordings)

    @docval(*get_docval(Sweeps.add_column))
    def add_ic_sweeps_column(self, **kwargs):
        """
        Add a column to the Sweeps table.
        See :py:meth:`~hdmf.common.DynamicTable.add_column` for more details
        """
        self._check_ic_sweeps()
        call_docval_func(self.ic_sweeps.add_column, kwargs)

    @docval(*get_docval(Sweeps.add_sweep),
            allow_extra=True)
    def add_sweep(self, **kwargs):
        """
        Add a new sweep to the ic_sweeps table
        """
        self._check_ic_sweeps()
        call_docval_func(self.ic_sweeps.add_sweep, kwargs)

    def _check_ic_sweep_sequences(self):
        """
        Create the SweepSequences (and dependent Sweeps and IntracellularRecordings) table if not yet done
        """
        if self.ic_sweep_sequences is None:
            self._check_ic_sweeps()
            self.ic_sweep_sequences = SweepSequences(self.ic_sweeps)

    @docval(*get_docval(SweepSequences.add_column))
    def add_ic_sweep_sequences_column(self, **kwargs):
        """
        Add a column to the SweepSequences table.
        See :py:meth:`~hdmf.common.DynamicTable.add_column` for more details
        """
        self._check_ic_sweeps()
        call_docval_func(self.ic_sweep_sequences.add_column, kwargs)

    @docval(*get_docval(SweepSequences.add_sweep_sequence),
            allow_extra=True)
    def add_sweep_sequence(self, **kwargs):
        """
        Add a new sweep sequence to the ic_sweep_sequences table
        """
        self._check_ic_sweep_sequences()
        call_docval_func(self.ic_sweep_sequences.add_sweep_sequence, kwargs)

    def _check_ic_runs(self):
        """
        Create the Runs (and dependent SweepSequences, Sweeps, and IntracellularRecrodings) table if not yet done
        """
        if self.ic_runs is None:
            self._check_ic_sweep_sequences()
            self.ic_runs = Runs(self.ic_sweep_sequences)

    @docval(*get_docval(Runs.add_column))
    def add_ic_runs_column(self, **kwargs):
        """
        Add a column to the Runs table.
        See :py:meth:`~hdmf.common.DynamicTable.add_column` for more details
        """
        self._check_ic_runs()
        call_docval_func(self.runs.add_column, kwargs)

    @docval(*get_docval(Runs.add_run),
            allow_extra=True)
    def add_run(self, **kwargs):
        """
        Add a new run to the Runs table
        """
        self._check_ic_runs()
        call_docval_func(self.ic_runs.add_run, kwargs)

    def _check_ic_conditions(self):
        """
        Create the Conditions (and dependent Runs, SweepSequences, Sweeps, and IntracellularRecrodings)
        table if not yet done
        """
        if self.ic_conditions is None:
            self._check_ic_runs()
            self.ic_conditions = Conditions(self.ic_runs)

    @docval(*get_docval(Conditions.add_column))
    def add_ic_conditions_column(self, **kwargs):
        """
        Add a column to the Conditions table.
        See :py:meth:`~hdmf.common.DynamicTable.add_column` for more details
        """
        self._check_ic_runs()
        call_docval_func(self.ic_runs.add_column, kwargs)

    @docval(*get_docval(Conditions.add_condition),
            allow_extra=True)
    def add_ic_condition(self, **kwargs):
        """
        Add a new condition to the Conditions table
        """
        self._check_ic_conditions()
        call_docval_func(self.ic_conditions.add_condition, kwargs)
