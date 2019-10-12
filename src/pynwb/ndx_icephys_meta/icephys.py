from pynwb import register_class
from pynwb.icephys import PatchClampSeries, IntracellularElectrode
from hdmf.common import DynamicTable
from hdmf.utils import docval, getargs, popargs, call_docval_func, get_docval

@register_class('IntracellularRecordings', 'ndx-icephys-meta')
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
        kwargs['name'] = 'IntracellularRecordings'
        kwargs['description'] = ('A table to group together a stimulus and response from a single electrode and'
                                  'a single sweep. Each row in the table represents a single recording consisting'
                                  'typically of a stimulus and a corresponding response.')
        call_docval_func(super(IntracellularRecordings, self).__init__, kwargs)


    @docval({'name': 'electrode', 'type': IntracellularElectrode, 'doc': 'The intracellular electrode used'},
            {'name': 'stimulus_start_index', 'type': 'int', 'doc': 'Start index of the stimulus', 'default': -1},
            {'name': 'stimulus_index_count', 'type': 'int', 'doc': 'Stop index of the stimulus', 'default': -1},
            {'name': 'stimulus', 'type': PatchClampSeries , 'doc': 'The PatchClampSeries with the stimulus',
             'default': None},
            {'name': 'response_start_index', 'type': 'int', 'doc': 'Start index of the response', 'default': -1},
            {'name': 'response_index_count', 'type': 'int', 'doc': 'Stop index of the response', 'default': -1},
            {'name': 'response', 'type': PatchClampSeries , 'doc': 'The PatchClampSeries with the response',
             'default': None},
            allow_extra=True)
    def add_recording(self, **kwargs):
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

        # Add the row to the table
        row_kwargs = {'electrode': electrode,
                      'stimulus': (stimulus_start_index, stimulus_index_count, stimulus),
                      'response': (response_start_index, response_index_count, response)}
        row_kwargs.update(kwargs)
        return super(IntracellularRecordings, self).add_row(**row_kwargs)

