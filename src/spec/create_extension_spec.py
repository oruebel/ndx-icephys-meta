from pynwb.spec import (
    NWBNamespaceBuilder,
    NWBGroupSpec,
    NWBAttributeSpec,
    NWBDatasetSpec,
    NWBLinkSpec,
    NWBDtypeSpec,
    NWBRefSpec
)
from export_spec import export_spec


def main():
    # the values for ns_builder are auto-generated from your cookiecutter inputs
    ns_builder = NWBNamespaceBuilder(doc='Implement proposal for hierarchical metadata strucutre for intracellular electrophysiology data ',
                                     name='ndx-icephys-meta',
                                     version='0.1.0',
                                     author=['Oliver Ruebel',
                                             'Ryan Ly',
                                             'Benjamin Dichter',
                                             'Thomas Braun',
                                             'Andrew Tritt'],
                                     contact=['oruebel@lbl.gov',
                                              'rly@lbl.gov',
                                              'bdichter@lbl.gov',
                                              'None',
                                              'ajtritt@lbl.gov'])

    # Create a generic compound datatype for referencing a patch clamp series
    reference_timeseries_dtype = [
        NWBDtypeSpec(name='idx_start',
                     dtype='int32',
                     doc="Start index into the TimeSeries 'data' and 'timestamp' datasets of the "
                          "referenced TimeSeries. The first dimension of those arrays is always time."),
        NWBDtypeSpec(name='count',
                     dtype='int32',
                     doc="Number of data samples available in this time series, during this epoch"),
        NWBDtypeSpec(name='timeseries',
                     dtype=NWBRefSpec(target_type='PatchClampSeries',
                                      reftype='object'),
                     doc='The TimeSeries that this index applies to')
        ]

    # Create our table to group stimulus and response for Intracellular Electrophysiology Recordings
    icephys_recordings_table_spec = NWBGroupSpec(
        name='IntracellularRecordings',
        neurodata_type_def='IntracellularRecordings',
        neurodata_type_inc='DynamicTable',
        doc='A table to group together a stimulus and response from a single electrode and a single sweep. '
            'Each row in the table represents a single recording consisting typically of a stimulus and a '
            'corresponding response.',
        datasets=[NWBDatasetSpec(name='stimulus',
                                 neurodata_type_inc='VectorData',
                                 doc='Column storing the reference to the recorded stimulus for the recording (rows)',
                                 dtype=reference_timeseries_dtype),
                  NWBDatasetSpec(name='response',
                                 neurodata_type_inc='VectorData',
                                 doc='Column storing the reference to the recorded response for the recording (rows)',
                                 dtype=reference_timeseries_dtype),
                  NWBDatasetSpec(name='electrode',
                                 neurodata_type_inc='VectorData',
                                 doc='Column for storing the reference to the intracellular electrode',
                                 dtype=NWBRefSpec(target_type='IntracellularElectrode',
                                                  reftype='object'))]
    )

    # Create a Sweeps (similar to trials) table to group Intracellular Electrophysiology Recording that were
    # recorded at the same time and belong together
    sweeps_table_spec = NWBGroupSpec(
        name='Sweeps',
        neurodata_type_def='Sweeps',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recordings from the '
            'IntracellularRecordings table together that were recorded simultaneously '
            'from different electrodes',
        datasets=[NWBDatasetSpec(name='recordings',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the IntracellularRecordings table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='IntracellularRecordings',
                                                         reftype='object'),
                                        doc='Reference to the IntracellularRecordings table that '
                                            'this table region applies to. This specializes the '
                                            'attribute inherited from DynamicTableRegion to fix '
                                            'the type of table that can be referenced here.'
                                     )]),
                  NWBDatasetSpec(name='recordings_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the recordings column.')
                  ]
        )

    # Create the SweepSequences table to group different Sweeps together
    sweepsequences_table_spec = NWBGroupSpec(
        name='SweepSequences',
        neurodata_type_def='SweepSequences',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recording sweeps from the '
            'Sweeps table together. This is typically used to group together sweeps '
            'where the a sequence of stimuli of the same type with varying parameters '
            'have been presented in a sequence.',
        datasets=[NWBDatasetSpec(name='sweeps',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the Sweeps table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='Sweeps',
                                                         reftype='object'),
                                        doc='Reference to the Sweeps table that this table region'
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='sweeps_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the sweeps column.')
                  ]
        )

    # Create the Runs table to group different SweepSequences together
    runs_table_spec = NWBGroupSpec(
        name='Runs',
        neurodata_type_def='Runs',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recording sweep sequences together.'
            'With each SweepSequence typically representing a particular type of stimulus, the '
            'Runs table is typcially used to group sets of stimuli applied in sequence.',
        datasets=[NWBDatasetSpec(name='sweep_sequences',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the SweepSequences table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='SweepSequences',
                                                         reftype='object'),
                                        doc='Reference to the SweepSequences table that this table region'
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='sweep_sequences_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the sweep_sequences column.')
                  ]
        )

    # Create Conditions tbale for grouping different Runs together
    conditions_table_spec = NWBGroupSpec(
        name='Conditions',
        neurodata_type_def='Conditions',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recording runs together that '
            'belong to the same experimental conditions.',
        datasets=[NWBDatasetSpec(name='runs',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the Runs table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='Runs',
                                                         reftype='object'),
                                        doc='Reference to the Runs table that this table region'
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='runs_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the runs column.')
                  ]
        )

    # TODO need to modify /general/intracellular_ephys in NWB to support adding the new structure there

    # Add our new data types to this list
    new_data_types = [icephys_recordings_table_spec,
                      sweeps_table_spec,
                      sweepsequences_table_spec,
                      runs_table_spec,
                      conditions_table_spec]

    # Include the types that are used by the extension and their namespaces (where to find them)
    ns_builder.include_type('DynamicTable', namespace='core')
    ns_builder.include_type('DynamicTableRegion', namespace='core')
    ns_builder.include_type('VectorData', namespace='core')
    ns_builder.include_type('VectorIndex', namespace='core')
    ns_builder.include_type('PatchClampSeries', namespace='core')
    ns_builder.include_type('IntracellularElectrode', namespace='core')

    export_spec(ns_builder, new_data_types)


if __name__ == "__main__":
    main()

