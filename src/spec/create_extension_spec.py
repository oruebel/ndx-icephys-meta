from pynwb.spec import (
    NWBNamespaceBuilder,
    NWBGroupSpec,
    NWBAttributeSpec,
    NWBDatasetSpec,
    NWBDtypeSpec,
    NWBRefSpec
)
from hdmf.spec.write import export_spec
import os


def main():
    # the values for ns_builder are auto-generated from your cookiecutter inputs
    ns_builder = NWBNamespaceBuilder(doc='Implement proposal for hierarchical metadata structure '
                                         'for intracellular electrophysiology data ',
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
                     dtype=NWBRefSpec(target_type='TimeSeries',
                                      reftype='object'),
                     doc='The TimeSeries that this index applies to')
        ]

    # Create our table to group stimulus and response for Intracellular Electrophysiology Recordings
    icephys_recordings_table_spec = NWBGroupSpec(
        name='intracellular_recordings',
        neurodata_type_def='IntracellularRecordingsTable',
        neurodata_type_inc='DynamicTable',
        doc='A table to group together a stimulus and response from a single electrode and a single simultaneous '
            'recording. Each row in the table represents a single recording consisting typically of a stimulus and a '
            'corresponding response. In some cases, however, only a stimulus or a response are recorded as '
            'as part of an experiment. In this case both, the stimulus and resposne will point to the same '
            'TimeSeries while the idx_start and count of the invalid column will be set to -1, thus, '
            'indicating that no values have been recorded for the stimulus or response, respectively. Note, '
            'a recording MUST contain at least a stimulus or a response. Typically the stimulus and response '
            'are PatchClampSeries. However, the use of AD/DA channels that are not associated to an electrode '
            'is also common in intracellular electrophysiology, in which case other TimeSeries may be used.',
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

    # Create a SimultaneousRecordingsTable (similar to trials) table to group Intracellular Electrophysiology Recording that were
    # recorded at the same time and belong together
    simultaneous_recordings_table_spec = NWBGroupSpec(
        name='simultaneous_recordings',
        neurodata_type_def='SimultaneousRecordingsTable',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recordings from the '
            'IntracellularRecordingsTable table together that were recorded simultaneously '
            'from different electrodes',
        datasets=[NWBDatasetSpec(name='recordings',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the IntracellularRecordingsTable table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='IntracellularRecordingsTable',
                                                         reftype='object'),
                                        doc='Reference to the IntracellularRecordingsTable table that '
                                            'this table region applies to. This specializes the '
                                            'attribute inherited from DynamicTableRegion to fix '
                                            'the type of table that can be referenced here.'
                                     )]),
                  NWBDatasetSpec(name='recordings_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the recordings column.')
                  ]
        )

    # Create the SequentialRecordingsTable table to group different SimultaneousRecordingsTable together
    sequentialrecordings_table_spec = NWBGroupSpec(
        name='sequential_recordings',
        neurodata_type_def='SequentialRecordingsTable',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different sequential recordings from the '
            'SimultaneousRecordingsTable table together. This is typically '
            'used to group together sequential recordings where the a sequence '
            'of stimuli of the same type with varying parameters '
            'have been presented in a sequence.',
        datasets=[NWBDatasetSpec(name='simultaneous_recordings',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the SimultaneousRecordingsTable table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='SimultaneousRecordingsTable',
                                                         reftype='object'),
                                        doc='Reference to the SimultaneousRecordingsTable table that this table region '
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='simultaneous_recordings_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the simultaneous_recordings column.'),
                  NWBDatasetSpec(name='stimulus_type',
                                 neurodata_type_inc='VectorData',
                                 doc='The type of stimulus used for the sequential recording',
                                 dtype='text')
                  ]
        )

    # Create the RepetitionsTable table to group different SequentialRecordingsTable together
    repetitions_table_spec = NWBGroupSpec(
        name='repetitions',
        neurodata_type_def='RepetitionsTable',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different sequential intracellular recordings together. '
            'With each SequentialRecording typically representing a particular type of stimulus, the '
            'RepetitionsTable table is typically used to group sets of stimuli applied in sequence.',
        datasets=[NWBDatasetSpec(name='sequential_recordings',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the SequentialRecordingsTable table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='SequentialRecordingsTable',
                                                         reftype='object'),
                                        doc='Reference to the SequentialRecordingsTable table that this table region '
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='sequential_recordings_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the sequential_recordings column.')
                  ]
        )

    # Create ExperimentalConditionsTable tbale for grouping different RepetitionsTable together
    experimental_conditions_table_spec = NWBGroupSpec(
        name='experimental_conditions',
        neurodata_type_def='ExperimentalConditionsTable',
        neurodata_type_inc='DynamicTable',
        doc='A table for grouping different intracellular recording repetitions together that '
            'belong to the same experimental experimental_conditions.',
        datasets=[NWBDatasetSpec(name='repetitions',
                                 neurodata_type_inc='DynamicTableRegion',
                                 doc='A reference to one or more rows in the RepetitionsTable table.',
                                 attributes=[
                                     NWBAttributeSpec(
                                        name='table',
                                        dtype=NWBRefSpec(target_type='RepetitionsTable',
                                                         reftype='object'),
                                        doc='Reference to the RepetitionsTable table that this table region '
                                            'applies to. This specializes the attribute inherited '
                                            'from DynamicTableRegion to fix the type of table that '
                                            'can be referenced here.'
                                     )
                                 ]),
                  NWBDatasetSpec(name='repetitions_index',
                                 neurodata_type_inc='VectorIndex',
                                 doc='Index dataset for the repetitions column.')
                  ]
        )

    # Update NWBFile to modify /general/intracellular_ephys in NWB to support adding the new structure there
    # NOTE: If this proposal for extension to NWB gets merged with the core schema the new NWBFile type would
    #       need to be removed and the NWBFile schema updated instead
    icephys_file_spec = NWBGroupSpec(
        neurodata_type_inc='NWBFile',
        neurodata_type_def='ICEphysFile',
        doc='Extension of the NWBFile class to allow placing the new icephys '
            'metadata types in /general/intracellular_ephys in the NWBFile '
            'NOTE: If this proposal for extension to NWB gets merged with '
            'the core schema, then this type would be removed and the '
            'NWBFile specification updated instead',
        groups=[NWBGroupSpec(
         name='general',
         doc='expand definition of general from NWBFile',
         groups=[NWBGroupSpec(name='intracellular_ephys',
                              doc='expand definition from NWBFile',
                              groups=[NWBGroupSpec(neurodata_type_inc='IntracellularRecordingsTable',
                                                   doc=icephys_recordings_table_spec.doc,
                                                   name='intracellular_recordings',
                                                   quantity='?'),
                                      NWBGroupSpec(neurodata_type_inc='SimultaneousRecordingsTable',
                                                   doc=simultaneous_recordings_table_spec.doc,
                                                   name='simultaneous_recordings',
                                                   quantity='?'),
                                      NWBGroupSpec(neurodata_type_inc='SequentialRecordingsTable',
                                                   doc=sequentialrecordings_table_spec.doc,
                                                   name='sequential_recordings',
                                                   quantity='?'),
                                      NWBGroupSpec(neurodata_type_inc='RepetitionsTable',
                                                   doc=repetitions_table_spec.doc,
                                                   name='repetitions',
                                                   quantity='?'),
                                      NWBGroupSpec(neurodata_type_inc='ExperimentalConditionsTable',
                                                   doc=experimental_conditions_table_spec.doc,
                                                   name='experimental_conditions',
                                                   quantity='?'),
                                      # Update doc on SweepTable to declare it as deprecated
                                      NWBGroupSpec(neurodata_type_inc='SweepTable',
                                                   doc='[DEPRACATED] Table used to group different PatchClampSeries.'
                                                       'SweepTable is being replaced by IntracellularRecordingsTable '
                                                       'and SimultaneousRecordingsTable tabels (and corresponding SequentialRecordingsTable, RepetitionsTable '
                                                       'and Consitions tables.',
                                                   name='sweep_table',
                                                   quantity='?')
                                      ],
                              datasets=[NWBDatasetSpec(name='filtering',
                                                       doc='[DEPRECATED] Use IntracellularElectrode.filtering instead. '
                                                            'Description of filtering used. Includes filtering type '
                                                            'and parameters, frequency fall-off, etc. If this changes '
                                                            'between TimeSeries, filter description should be stored '
                                                            'as a text attribute for each TimeSeries.',
                                                       dtype='text',
                                                       quantity='?')]
                              )
                 ]
            )
        ]
    )

    # Add the type we want to include from core to this list
    include_core_types = ['DynamicTable',
                          'DynamicTableRegion',
                          'VectorData',
                          'VectorIndex',
                          'PatchClampSeries',
                          'IntracellularElectrode',
                          'NWBFile']
    # Include the types that are used by the extension and their namespaces (where to find them)
    for type_name in include_core_types:
        ns_builder.include_type(type_name, namespace='core')

    # Add our new data types to this list
    new_data_types = [icephys_recordings_table_spec,
                      simultaneous_recordings_table_spec,
                      sequentialrecordings_table_spec,
                      repetitions_table_spec,
                      experimental_conditions_table_spec,
                      icephys_file_spec]

    # Export the spec
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    output_dir = os.path.join(project_dir, 'spec')
    export_spec(ns_builder=ns_builder,
                new_data_types=new_data_types,
                output_dir=output_dir)
    print("Exported specification to: %s" % output_dir)


if __name__ == "__main__":
    main()
