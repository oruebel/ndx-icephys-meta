import unittest
import warnings
import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
import h5py
from pynwb.icephys import VoltageClampStimulusSeries, VoltageClampSeries, CurrentClampStimulusSeries, IZeroClampSeries
from pynwb.testing import remove_test_file
from pynwb import NWBHDF5IO
from hdmf.utils import docval, popargs
from pandas.testing import assert_frame_equal

try:
    from ndx_icephys_meta.icephys import (IntracellularRecordingsTable,
                                          SimultaneousRecordingsTable,
                                          SequentialRecordingsTable,
                                          RepetitionsTable,
                                          ExperimentalConditionsTable,
                                          ICEphysFile)
except ImportError:
    # If we are running tests directly in the GitHub repo without installing the extension
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import (IntracellularRecordingsTable,
                                          SimultaneousRecordingsTable,
                                          SequentialRecordingsTable,
                                          RepetitionsTable,
                                          ExperimentalConditionsTable,
                                          ICEphysFile)

# TODO Add simple round-trip tests for all classes (i.e., test_round_trip_container_no_data tests without NWBFile)
# TODO Add tests for adding custom categories (both on init and using add_category)
# TODO Add test provide category tables for IntracellularRecording on init to test error checks for bad/missing tables
# TODO Add tests for adding custom columns to IntracellularRecordings on init


class ICEphysMetaTestBase(unittest.TestCase):
    """
    Base helper class for setting up tests for the ndx-icephys-meta extension.

    Here we use the base NWBFile class for read/write (rather than our custom ICEphysFile)
    to make sure tests of the individual tables do not depend on our custom class. We are testing
    ICEphysFile separately.
    """
    @classmethod
    def create_stimulus_and_response(cls, sweep_number, electrode, randomize_data):
        """
        Internal helper function to construct a dummy stimulus and reponse pair representing an
        instracellular recording:

        :param sweep_number: Integer sweep number of the recording
        :param electrode: Intracellular electrode used
        :param randomize_data: Randomize data values in the stimulus and response

        :returns: Tuple of VoltageClampStimulusSeries with the stimulus and VoltageClampSeries with the response.
        """
        stimulus = VoltageClampStimulusSeries(
                    name="ccss_"+str(sweep_number),
                    data=[1, 2, 3, 4, 5] if not randomize_data else np.random.rand(10),
                    starting_time=123.6 if not randomize_data else (np.random.rand() * 100),
                    rate=10e3 if not randomize_data else int(np.random.rand()*10) * 1000 + 1000.,
                    electrode=electrode,
                    gain=0.1 if not randomize_data else np.random.rand(),
                    sweep_number=sweep_number)
        # Create and ic-response
        response = VoltageClampSeries(
                    name='vcs_'+str(sweep_number),
                    data=[0.1, 0.2, 0.3, 0.4, 0.5] if not randomize_data else np.random.rand(10),
                    conversion=1e-12,
                    resolution=np.nan,
                    starting_time=123.6 if not randomize_data else (np.random.rand() * 100),
                    rate=20e3 if not randomize_data else int(np.random.rand() * 20) * 1000. + 1000.,
                    electrode=electrode,
                    gain=0.02 if not randomize_data else np.random.rand(),
                    capacitance_slow=100e-12,
                    resistance_comp_correction=70.0 if not randomize_data else 70.0 + np.random.rand(),
                    sweep_number=sweep_number)
        return stimulus, response

    @classmethod
    def create_icephs_meta_testfile(cls, filename=None, add_custom_columns=True, randomize_data=True):
        """
        Create a small but relatively complex icephys test file that
        we can use for testing of queries.

        :param filename: The name of the output file to be generated. If set to None then the file is not written
                         but only created in memor
        :type filename: str, None
        :param add_custom_colums: Add custom metadata columns to each table
        :type add_custom_colums: bool
        :param randomize_data: Randomize data values in the stimulus and response
        :type randomize_data: bool

        :returns: ICEphysFile NWBFile object
        :rtype: ICEphysFile
        """
        nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN')
        # Add a device
        device = nwbfile.create_device(name='Heka ITC-1600')
        # Add an intracellular electrode
        electrode0 = nwbfile.create_icephys_electrode(
            name="elec0",
            description='a mock intracellular electrode',
            device=device)
        # Add an intracellular electrode
        electrode1 = nwbfile.create_icephys_electrode(
            name="elec1",
            description='another mock intracellular electrode',
            device=device)
        # Add the intracelluar recordings
        for sweep_number in range(20):
            elec = (electrode0 if (sweep_number % 2 == 0) else electrode1)
            stim, resp = cls.create_stimulus_and_response(sweep_number=np.uint64(sweep_number),
                                                          electrode=elec,
                                                          randomize_data=randomize_data)
            nwbfile.add_intracellular_recording(electrode=elec,
                                                stimulus=stim,
                                                response=resp,
                                                id=sweep_number)
        nwbfile.intracellular_recordings.add_column(name='recording_tags',
                                                    data=['A1', 'A2',
                                                          'B1', 'B2',
                                                          'C1', 'C2', 'C3',
                                                          'D1', 'D2', 'D3',
                                                          'A1', 'A2',
                                                          'B1', 'B2',
                                                          'C1', 'C2', 'C3',
                                                          'D1', 'D2', 'D3'],
                                                    description='String with a set of recording tags')
        # Add simultaneous_recordings
        nwbfile.add_icephys_simultaneous_recording(recordings=[0, 1], id=np.int64(100))
        nwbfile.add_icephys_simultaneous_recording(recordings=[2, 3], id=np.int64(101))
        nwbfile.add_icephys_simultaneous_recording(recordings=[4, 5, 6], id=np.int64(102))
        nwbfile.add_icephys_simultaneous_recording(recordings=[7, 8, 9], id=np.int64(103))
        nwbfile.add_icephys_simultaneous_recording(recordings=[10, 11], id=np.int64(104))
        nwbfile.add_icephys_simultaneous_recording(recordings=[12, 13], id=np.int64(105))
        nwbfile.add_icephys_simultaneous_recording(recordings=[14, 15, 16], id=np.int64(106))
        nwbfile.add_icephys_simultaneous_recording(recordings=[17, 18, 19], id=np.int64(107))
        if add_custom_columns:
            nwbfile.icephys_simultaneous_recordings.add_column(
                name='tag',
                data=np.arange(8),
                description='some integer tag for a sweep')

        # Add sequential recordings
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[0, 1],
                                                 id=np.int64(1000),
                                                 stimulus_type="StimType_1")
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[2, ],
                                                 id=np.int64(1001),
                                                 stimulus_type="StimType_2")
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[3, ],
                                                 id=np.int64(1002),
                                                 stimulus_type="StimType_3")
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[4, 5],
                                                 id=np.int64(1003),
                                                 stimulus_type="StimType_1")
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[6, ],
                                                 id=np.int64(1004),
                                                 stimulus_type="StimType_2")
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[7, ],
                                                 id=np.int64(1005),
                                                 stimulus_type="StimType_3")
        if add_custom_columns:
            nwbfile.icephys_sequential_recordings.add_column(
                name='type',
                data=['T1', 'T2', 'T3', 'T1', 'T2', 'T3'],
                description='type of the sequential recording')

        # Add repetitions
        nwbfile.add_icephys_repetition(sequential_recordings=[0, ], id=np.int64(10000))
        nwbfile.add_icephys_repetition(sequential_recordings=[1, 2], id=np.int64(10001))
        nwbfile.add_icephys_repetition(sequential_recordings=[3, ], id=np.int64(10002))
        nwbfile.add_icephys_repetition(sequential_recordings=[4, 5], id=np.int64(10003))
        if add_custom_columns:
            nwbfile.icephys_repetitions.add_column(
                name='type',
                data=['R1', 'R2', 'R1', 'R2'],
                description='some repetition type indicator')

        # Add experimental_conditions
        nwbfile.add_icephys_experimental_condition(repetitions=[0, 1], id=np.int64(100000))
        nwbfile.add_icephys_experimental_condition(repetitions=[2, 3], id=np.int64(100001))
        if add_custom_columns:
            nwbfile.icephys_experimental_conditions.add_column(
                name='temperature',
                data=[32., 24.],
                description='Temperatur in C')

        # Write our test file
        if filename is not None:
            with NWBHDF5IO(filename, 'w') as io:
                io.write(nwbfile)

        # Return our in-memory NWBFile
        return nwbfile

    def setUp(self):
        # Create an example nwbfile with a device, intracellular electrode, stimulus, and response
        self.nwbfile = ICEphysFile(
            session_description='my first synthetic recording',
            identifier='EXAMPLE_ID',
            session_start_time=datetime.now(tzlocal()),
            experimenter='Dr. Bilbo Baggins',
            lab='Bag End Laboratory',
            institution='University of Middle Earth at the Shire',
            experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
            session_id='LONELYMTN')
        self.device = self.nwbfile.create_device(name='Heka ITC-1600')
        self.electrode = self.nwbfile.create_icephys_electrode(name="elec0",
                                                               description='a mock intracellular electrode',
                                                               device=self.device)
        self.stimulus = VoltageClampStimulusSeries(name="ccss",
                                                   data=[1, 2, 3, 4, 5],
                                                   starting_time=123.6,
                                                   rate=10e3,
                                                   electrode=self.electrode,
                                                   gain=0.02,
                                                   sweep_number=np.uint64(15))
        self.nwbfile.add_stimulus(self.stimulus)
        self.response = VoltageClampSeries(name='vcs',
                                           data=[0.1, 0.2, 0.3, 0.4, 0.5],
                                           conversion=1e-12,
                                           resolution=np.nan,
                                           starting_time=123.6,
                                           rate=20e3,
                                           electrode=self.electrode,
                                           gain=0.02,
                                           capacitance_slow=100e-12,
                                           resistance_comp_correction=70.0,
                                           sweep_number=np.uint64(15))
        self.nwbfile.add_acquisition(self.response)
        self.path = 'test_icephys_meta_intracellularrecording.h5'

    def tearDown(self):
        remove_test_file(self.path)

    @docval({'name': 'ir',
             'type': IntracellularRecordingsTable,
             'doc': 'Intracellular recording to be added to the file before write',
             'default': None},
            {'name': 'sw',
             'type': SimultaneousRecordingsTable,
             'doc': 'SimultaneousRecordingsTable table to be added to the file before write',
             'default': None},
            {'name': 'sws',
             'type': SequentialRecordingsTable,
             'doc': 'SequentialRecordingsTable table to be added to the file before write',
             'default': None},
            {'name': 'repetitions',
             'type': RepetitionsTable,
             'doc': 'RepetitionsTable table to be added to the file before write',
             'default': None},
            {'name': 'cond',
             'type': ExperimentalConditionsTable,
             'doc': 'ExperimentalConditionsTable table to be added to the file before write',
             'default': None})
    def write_test_helper(self, **kwargs):
        """Internal helper function to roundtrip an ICEphys file with the given set of ICEphys tables"""
        ir, sw, sws, repetitions, cond = popargs('ir', 'sw', 'sws', 'repetitions', 'cond', kwargs)

        if ir is not None:
            self.nwbfile.intracellular_recordings = ir
        if sw is not None:
            self.nwbfile.icephys_simultaneous_recordings = sw
        if sws is not None:
            self.nwbfile.icephys_sequential_recordings = sws
        if repetitions is not None:
            self.nwbfile.icephys_repetitions = repetitions
        if cond is not None:
            self.nwbfile.icephys_experimental_conditions = cond

        # Write our test file
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)

        # Test that we can read the file
        with NWBHDF5IO(self.path, 'r') as io:
            infile = io.read()
            if ir is not None:
                in_ir = infile.intracellular_recordings
                self.assertIsNotNone(in_ir)
                to_dataframe_kwargs = dict(electrode_refs_as_objectids=True,
                                           stimulus_refs_as_objectids=True,
                                           response_refs_as_objectids=True)
                assert_frame_equal(ir.to_dataframe(**to_dataframe_kwargs), in_ir.to_dataframe(**to_dataframe_kwargs))
            if sw is not None:
                in_sw = infile.icephys_simultaneous_recordings
                self.assertIsNotNone(in_sw)
                self.assertListEqual(in_sw['recordings'].target.data[:].tolist(), sw['recordings'].target.data[:])
                self.assertEqual(in_sw['recordings'].target.table.object_id, sw['recordings'].target.table.object_id)
            if sws is not None:
                in_sws = infile.icephys_sequential_recordings
                self.assertIsNotNone(in_sws)
                self.assertListEqual(in_sws['simultaneous_recordings'].target.data[:].tolist(),
                                     sws['simultaneous_recordings'].target.data[:])
                self.assertEqual(in_sws['simultaneous_recordings'].target.table.object_id,
                                 sws['simultaneous_recordings'].target.table.object_id)
            if repetitions is not None:
                in_repetitions = infile.icephys_repetitions
                self.assertIsNotNone(in_repetitions)
                self.assertListEqual(in_repetitions['sequential_recordings'].target.data[:].tolist(),
                                     repetitions['sequential_recordings'].target.data[:])
                self.assertEqual(in_repetitions['sequential_recordings'].target.table.object_id,
                                 repetitions['sequential_recordings'].target.table.object_id)
            if cond is not None:
                in_cond = infile.icephys_experimental_conditions
                self.assertIsNotNone(in_cond)
                self.assertListEqual(in_cond['repetitions'].target.data[:].tolist(),
                                     cond['repetitions'].target.data[:])
                self.assertEqual(in_cond['repetitions'].target.table.object_id,
                                 cond['repetitions'].target.table.object_id)


class IntracellularElectrodesTableTests(unittest.TestCase):
    """
    The IntracellularElectrodesTable is covered by the
    IntracellularRecordingsTableTests as this table is part of that table.
    """
    def setUp(self):
        pass

    def tearDown(self):
        pass


class IntracellularStimuliTableTests(unittest.TestCase):
    """
    The IntracellularStimuliTable is covered by the
    IntracellularRecordingsTableTests as this table is part of that table.
    """
    def setUp(self):
        pass

    def tearDown(self):
        pass


class IntracellularResponsesTableTests(unittest.TestCase):
    """
    The IntracellularResponsesTable is covered by the
    IntracellularRecordingsTableTests as this table is part of that table.
    """
    def setUp(self):
        pass

    def tearDown(self):
        pass


class IntracellularRecordingsTableTests(ICEphysMetaTestBase):
    """
    Class for testing the IntracellularRecordingsTable Container
    """

    def test_init(self):
        _ = IntracellularRecordingsTable()
        self.assertTrue(True)

    def test_add_row(self):
        # Add a row to our IR table
        ir = IntracellularRecordingsTable()

        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        # test that we get the correct row index back
        self.assertEqual(row_index, 0)
        # read our first (and only) row and assert that it is correct
        res = ir[0]
        # Confirm that slicing one row give the same result as converting the whole table, which has only one row
        assert_frame_equal(ir.to_dataframe(), res)
        # Check the row id
        self.assertEqual(res.index[0], 10)
        # Check electrodes
        self.assertIs(res[('electrodes', 'electrode')].iloc[0], self.electrode)
        # Check the stimulus
        self.assertTupleEqual(res[('stimuli', 'stimulus')].iloc[0], (0, 5, self.stimulus))
        # Check the response
        self.assertTupleEqual(res[('responses', 'response')].iloc[0], (0, 5, self.response))
        # test writing out ir table
        self.write_test_helper(ir)

    def test_add_row_incompatible_types(self):
        # Add a row that mixes CurrentClamp and VoltageClamp data
        sweep_number = 15
        local_stimulus = CurrentClampStimulusSeries(
            name="ccss_"+str(sweep_number),
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=self.electrode,
            gain=0.1,
            sweep_number=np.uint64(sweep_number))
        ir = IntracellularRecordingsTable()
        with self.assertRaises(ValueError):
            _ = ir.add_recording(electrode=self.electrode,
                                 stimulus=local_stimulus,
                                 response=self.response,
                                 id=np.int64(10))

    def test_warn_if_IZeroClampSeries_with_stimulus(self):
        local_response = IZeroClampSeries(
            name="ccss",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=self.electrode,
            gain=0.02,
            sweep_number=np.uint64(100000))
        ir = IntracellularRecordingsTable()
        with self.assertRaises(ValueError):
            _ = ir.add_recording(electrode=self.electrode,
                                 stimulus=self.stimulus,
                                 response=local_response,
                                 id=np.int64(10))

    def test_inconsistent_PatchClampSeries(self):
        local_electrode = self.nwbfile.create_icephys_electrode(name="elec1",
                                                                description='a mock intracellular electrode',
                                                                device=self.device)
        local_stimulus = VoltageClampStimulusSeries(name="ccss",
                                                    data=[1, 2, 3, 4, 5],
                                                    starting_time=123.6,
                                                    rate=10e3,
                                                    electrode=local_electrode,
                                                    gain=0.02,
                                                    sweep_number=np.uint64(100000))
        ir = IntracellularRecordingsTable()
        with self.assertRaises(ValueError):
            _ = ir.add_recording(electrode=self.electrode,
                                 stimulus=local_stimulus,
                                 response=self.response,
                                 id=np.int64(10))

    def test_add_row_no_response(self):
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=None,
                                     id=np.int64(10))
        res = ir[0]
        # Check the ID
        self.assertEqual(row_index, 0)
        self.assertEqual(res.index[0], 10)
        # Check the row id
        self.assertEqual(res.index[0], 10)
        # Check electrodes
        self.assertIs(res[('electrodes', 'electrode')].iloc[0], self.electrode)
        # Check the stimulus
        self.assertTupleEqual(res[('stimuli', 'stimulus')].iloc[0], (0, 5, self.stimulus))
        # Check the response
        self.assertTupleEqual(res[('responses', 'response')].iloc[0], (-1, -1, self.stimulus))
        # test writing out ir table
        self.write_test_helper(ir)

    def test_add_row_no_stimulus(self):
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=None,
                                     response=self.response,
                                     id=np.int64(10))
        res = ir[0]
        # Check the ID
        self.assertEqual(row_index, 0)
        self.assertEqual(res.index[0], 10)
        # Check the row id
        self.assertEqual(res.index[0], 10)
        # Check electrodes
        self.assertIs(res[('electrodes', 'electrode')].iloc[0], self.electrode)
        # Check the stimulus
        self.assertTupleEqual(res[('stimuli', 'stimulus')].iloc[0], (-1, -1, self.response))
        # Check the response
        self.assertTupleEqual(res[('responses', 'response')].iloc[0], (0, 5, self.response))
        # test writing out ir table
        self.write_test_helper(ir)

    def test_add_row_index_out_of_range(self):

        # Stimulus/Response start_index to large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_start_index=10,
                             response=self.response,
                             id=np.int64(10))
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_start_index=10,
                             response=self.response,
                             id=np.int64(10))
        # Stimulus/Reponse index count too large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_index_count=10,
                             response=self.response,
                             id=np.int64(10))
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_index_count=10,
                             response=self.response,
                             id=np.int64(10))
        # Stimulus/Reponse start+count combination too large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_start_index=3,
                             stimulus_index_count=4,
                             response=self.response,
                             id=np.int64(10))
        with self.assertRaises(IndexError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_start_index=3,
                             response_index_count=4,
                             response=self.response,
                             id=np.int64(10))

    def test_add_row_no_stimulus_and_response(self):
        with self.assertRaises(ValueError):
            ir = IntracellularRecordingsTable()
            ir.add_recording(electrode=self.electrode,
                             stimulus=None,
                             response=None)

    def test_add_column(self):
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        ir.add_column(name='test', description='test column', data=np.arange(1))
        self.assertTupleEqual(ir.colnames, ('test',))

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on RepetitionsTable table
        """
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        with self.assertRaises(ValueError):
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response=self.response,
                             id=np.int64(10))

    def test_basic_write(self):
        """
        Populate, write, and read the SimultaneousRecordingsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        ir.add_column(name='test', description='test column', data=np.arange(1))
        self.write_test_helper(ir=ir)

    def test_round_trip_container_no_data(self):
        """Test read and write the container by itself"""
        curr = IntracellularRecordingsTable()
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(curr)
        with NWBHDF5IO(self.path, 'r') as io:
            incon = io.read()
            self.assertListEqual(incon.categories, curr.categories)
            for n in curr.categories:
                # empty columns from file have dtype int64 or float64 but empty in-memory columns have dtype object
                assert_frame_equal(incon[n], curr[n], check_dtype=False, check_index_type=False)

    def test_write_with_stimulus_template(self):
        """
        Populate, write, and read the SimultaneousRecordingsTable container and other required containers
        """
        local_nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN')
        # Add a device
        local_device = local_nwbfile.create_device(name='Heka ITC-1600')
        local_electrode = local_nwbfile.create_icephys_electrode(
            name="elec0",
            description='a mock intracellular electrode',
            device=local_device)
        local_stimulus = VoltageClampStimulusSeries(name="ccss",
                                                    data=[1, 2, 3, 4, 5],
                                                    starting_time=123.6,
                                                    rate=10e3,
                                                    electrode=local_electrode,
                                                    gain=0.02,
                                                    sweep_number=np.uint64(15))
        local_response = VoltageClampSeries(name='vcs',
                                            data=[0.1, 0.2, 0.3, 0.4, 0.5],
                                            conversion=1e-12,
                                            resolution=np.nan,
                                            starting_time=123.6,
                                            rate=20e3,
                                            electrode=local_electrode,
                                            gain=0.02,
                                            capacitance_slow=100e-12,
                                            resistance_comp_correction=70.0,
                                            sweep_number=np.uint64(15))
        local_nwbfile.add_stimulus_template(local_stimulus)
        row_index = local_nwbfile.add_intracellular_recording(electrode=local_electrode,
                                                              stimulus=local_stimulus,
                                                              response=local_response,
                                                              id=np.int64(10))
        self.assertEqual(row_index, 0)
        # Write our test file
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(local_nwbfile)


class SimultaneousRecordingsTableTests(ICEphysMetaTestBase):
    """
    Test class for testing the SimultaneousRecordingsTable Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the SimultaneousRecordingsTable container
        """
        ir = IntracellularRecordingsTable()
        _ = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        self.assertTrue(True)

    def test_missing_intracellular_recordings_on_init(self):
        """
        Test that ValueError is raised when intracellular_recordings is missing. This is
        allowed only on read where the intracellular_recordings table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = SimultaneousRecordingsTable()

    def test_add_simultaneous_recording(self):
        """
        Populate, write, and read the SimultaneousRecordingsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        self.assertEqual(len(ir), 1)
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        row_index = sw.add_simultaneous_recording(recordings=[row_index], id=100)
        self.assertEqual(row_index, 0)
        self.assertListEqual(sw.id[:], [100])
        self.assertListEqual(sw['recordings'].data, [1])
        self.assertListEqual(sw['recordings'].target.data[:], [0])

    def test_basic_write(self):
        """
        Populate, write, and read the SimultaneousRecordingsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        self.assertEqual(len(ir), 1)
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        row_index = sw.add_simultaneous_recording(recordings=[row_index])
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on RepetitionsTable table
        """
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sw.add_simultaneous_recording(recordings=[0], id=np.int64(10))
        with self.assertRaises(ValueError):
            sw.add_simultaneous_recording(recordings=[0], id=np.int64(10))


class SequentialRecordingsTableTests(ICEphysMetaTestBase):
    """
    Test class for testing the SequentialRecordingsTable Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the SequentialRecordingsTable container
        """
        ir = IntracellularRecordingsTable()
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        _ = SequentialRecordingsTable(simultaneous_recordings_table=sw)
        self.assertTrue(True)

    def test_missing_simultaneous_recordings_on_init(self):
        """
        Test that ValueError is raised when simultaneous_recordings is missing. This is
        allowed only on read where the simultaneous_recordings table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = SequentialRecordingsTable()

    def test_basic_write(self):
        """
        Populate, write, and read the SequentialRecordingsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        row_index = sw.add_simultaneous_recording(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SequentialRecordingsTable(sw)
        row_index = sws.add_sequential_recording(simultaneous_recordings=[0, ], stimulus_type='MyStimStype')
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw, sws=sws)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on RepetitionsTable table
        """
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sw.add_simultaneous_recording(recordings=[0])
        sws = SequentialRecordingsTable(sw)
        sws.add_sequential_recording(simultaneous_recordings=[0, ], id=np.int64(10), stimulus_type='MyStimStype')
        with self.assertRaises(ValueError):
            sws.add_sequential_recording(simultaneous_recordings=[0, ], id=np.int64(10), stimulus_type='MyStimStype')


class RepetitionsTableTests(ICEphysMetaTestBase):
    """
    Test class for testing the RepetitionsTable Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the RepetitionsTable container
        """
        ir = IntracellularRecordingsTable()
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sws = SequentialRecordingsTable(simultaneous_recordings_table=sw)
        _ = RepetitionsTable(sequential_recordings_table=sws)
        self.assertTrue(True)

    def test_missing_sequential_recordings_on_init(self):
        """
        Test that ValueError is raised when sequential_recordings is missing. This is
        allowed only on read where the sequential_recordings table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = RepetitionsTable()

    def test_basic_write(self):
        """
        Populate, write, and read the RepetitionsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        row_index = sw.add_simultaneous_recording(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SequentialRecordingsTable(sw)
        row_index = sws.add_sequential_recording(simultaneous_recordings=[0, ], stimulus_type='MyStimStype')
        self.assertEqual(row_index, 0)
        repetitions = RepetitionsTable(sequential_recordings_table=sws)
        repetitions.add_repetition(sequential_recordings=[0, ])
        self.write_test_helper(ir=ir, sw=sw, sws=sws, repetitions=repetitions)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on RepetitionsTable table
        """
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sw.add_simultaneous_recording(recordings=[0])
        sws = SequentialRecordingsTable(sw)
        sws.add_sequential_recording(simultaneous_recordings=[0, ], stimulus_type='MyStimStype')
        repetitions = RepetitionsTable(sequential_recordings_table=sws)
        repetitions.add_repetition(sequential_recordings=[0, ], id=np.int64(10))
        with self.assertRaises(ValueError):
            repetitions.add_repetition(sequential_recordings=[0, ], id=np.int64(10))


class ExperimentalConditionsTableTests(ICEphysMetaTestBase):
    """
    Test class for testing the ExperimentalConditionsTable Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the ExperimentalConditionsTable container
        """
        ir = IntracellularRecordingsTable()
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sws = SequentialRecordingsTable(simultaneous_recordings_table=sw)
        repetitions = RepetitionsTable(sequential_recordings_table=sws)
        _ = ExperimentalConditionsTable(repetitions_table=repetitions)
        self.assertTrue(True)

    def test_missing_repetitions_on_init(self):
        """
        Test that ValueError is raised when repetitions is missing. This is
        allowed only on read where the repetitions table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = ExperimentalConditionsTable()

    def test_basic_write(self):
        """
        Populate, write, and read the ExperimentalConditionsTable container and other required containers
        """
        ir = IntracellularRecordingsTable()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=np.int64(10))
        self.assertEqual(row_index, 0)
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        row_index = sw.add_simultaneous_recording(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SequentialRecordingsTable(sw)
        row_index = sws.add_sequential_recording(simultaneous_recordings=[0, ], stimulus_type='MyStimStype')
        self.assertEqual(row_index, 0)
        repetitions = RepetitionsTable(sequential_recordings_table=sws)
        row_index = repetitions.add_repetition(sequential_recordings=[0, ])
        self.assertEqual(row_index, 0)
        cond = ExperimentalConditionsTable(repetitions_table=repetitions)
        row_index = cond.add_experimental_condition(repetitions=[0, ])
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw, sws=sws, repetitions=repetitions, cond=cond)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on RepetitionsTable table
        """
        ir = IntracellularRecordingsTable()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=np.int64(10))
        sw = SimultaneousRecordingsTable(intracellular_recordings_table=ir)
        sw.add_simultaneous_recording(recordings=[0])
        sws = SequentialRecordingsTable(sw)
        sws.add_sequential_recording(simultaneous_recordings=[0, ], stimulus_type='MyStimStype')
        repetitions = RepetitionsTable(sequential_recordings_table=sws)
        repetitions.add_repetition(sequential_recordings=[0, ])
        cond = ExperimentalConditionsTable(repetitions_table=repetitions)
        cond.add_experimental_condition(repetitions=[0, ], id=np.int64(10))
        with self.assertRaises(ValueError):
            cond.add_experimental_condition(repetitions=[0, ], id=np.int64(10))


class ICEphysFileTests(unittest.TestCase):
    """
    Test class for testing the ICEphysFileTests Container class
    """
    def setUp(self):
        warnings.simplefilter("always")  # Trigger all warnings
        self.path = 'test_icephys_meta_intracellularrecording.h5'

    def tearDown(self):
        remove_test_file(self.path)

    def __get_icephysfile(self):
        """
        Create a dummy ICEphysFile instance
        """
        icefile = ICEphysFile(
            session_description='my first synthetic recording',
            identifier='EXAMPLE_ID',
            session_start_time=datetime.now(tzlocal()),
            experimenter='Dr. Bilbo Baggins',
            lab='Bag End Laboratory',
            institution='University of Middle Earth at the Shire',
            experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
            session_id='LONELYMTN')
        return icefile

    def __add_device(self, icefile):
        return icefile.create_device(name='Heka ITC-1600')

    def __add_electrode(self, icefile, device):
        return icefile.create_icephys_electrode(name="elec0",
                                                description='a mock intracellular electrode',
                                                device=device)

    def __get_stimuls(self, electrode):
        """
        Create a dummy VoltageClampStimulusSeries
        """
        return VoltageClampStimulusSeries(
            name="ccss",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=electrode,
            gain=0.02,
            sweep_number=np.uint64(15))

    def __get_response(self, electrode):
        """
        Create a dummy VoltageClampSeries
        """
        return VoltageClampSeries(
            name='vcs',
            data=[0.1, 0.2, 0.3, 0.4, 0.5],
            conversion=1e-12,
            resolution=np.nan,
            starting_time=123.6,
            rate=20e3,
            electrode=electrode,
            gain=0.02,
            capacitance_slow=100e-12,
            resistance_comp_correction=70.0,
            sweep_number=np.uint64(15))

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the ICEphysFileTests container
        """
        _ = self.__get_icephysfile()

    def test_deprecate_simultaneous_recordings_on_add_stimulus(self):
        """
        Test that warnings are raised if the user tries to use a simultaneous_recordings table
        """
        nwbfile = self.__get_icephysfile()
        device = self.__add_device(nwbfile)
        electrode = self.__add_electrode(nwbfile, device)
        stimulus = self.__get_stimuls(electrode=electrode)
        responce = self.__get_response(electrode=electrode)
        # Make sure we warn if sweeptable is added on add_stimulus
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # Trigger all warnings
            nwbfile.add_stimulus(stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_acquisition(responce, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprecate_sweeptable_on_add_stimulus_template(self):
        """
        Make sure we warn when using the sweep-table
        """
        nwbfile = self.__get_icephysfile()
        local_electrode = nwbfile.create_icephys_electrode(
            name="elec0",
            description='a mock intracellular electrode',
            device=nwbfile.create_device(name='Heka ITC-1600'))
        local_stimulus = VoltageClampStimulusSeries(
            name="ccss",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=local_electrode,
            gain=0.02,
            sweep_number=np.uint64(15))
        local_stimulus2 = VoltageClampStimulusSeries(
            name="ccss2",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=local_electrode,
            gain=0.02,
            sweep_number=np.uint64(15))
        with warnings.catch_warnings(record=True) as w:
            nwbfile.add_stimulus_template(local_stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            self.assertEqual(str(w[-1].message),
                             "Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                             "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                             "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                             "add_icephys_repetition, add_icephys_condition functions.")
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_stimulus_template(local_stimulus2, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprecate_sweepstable_on_add_acquistion(self):
        """
        Test that warnings are raised if the user tries to use a sweeps table
        """
        nwbfile = self.__get_icephysfile()
        device = self.__add_device(nwbfile)
        electrode = self.__add_electrode(nwbfile, device)
        stimulus = self.__get_stimuls(electrode=electrode)
        responce = self.__get_response(electrode=electrode)
        # Make sure we warn if sweeptable is added on add_stimulus
        with warnings.catch_warnings(record=True) as w:
            nwbfile.add_acquisition(responce, use_sweep_table=True)
            self.assertEqual(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            self.assertEqual(str(w[-1].message),
                             "Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                             "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                             "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                             "add_icephys_repetition, add_icephys_condition functions.")
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_stimulus(stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprecate_sweepstable_on_init(self):
        """
        Test that warnings are raised if the user tries to use a sweeps table
        """
        from pynwb.icephys import SweepTable
        with warnings.catch_warnings(record=True) as w:
            nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN',
                sweep_table=SweepTable())
            device = self.__add_device(nwbfile)
            electrode = self.__add_electrode(nwbfile, device)
            stimulus = self.__get_stimuls(electrode=electrode)
            self.assertEqual(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_stimulus(stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprectation_ic_filtering_on_init(self):
        with warnings.catch_warnings(record=True) as w:
            nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN',
                ic_filtering='test filtering')
            assert issubclass(w[-1].category, DeprecationWarning)
            self.assertEqual(nwbfile.ic_filtering, 'test filtering')

    def test_ic_filtering_roundtrip(self):
        # create the base file
        nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN')
        # set the ic_filtering attribute and make sure we get a deprectation warning
        with warnings.catch_warnings(record=True) as w:
            nwbfile.ic_filtering = 'test filtering'
            assert issubclass(w[-1].category, DeprecationWarning)
        # write the test fil
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(nwbfile)
        # read the test file and confirm ic_filtering has been written
        with NWBHDF5IO(self.path, 'r') as io:
            with warnings.catch_warnings(record=True) as w:
                infile = io.read()
                assert issubclass(w[-1].category, DeprecationWarning)
                self.assertEqual(infile.ic_filtering, 'test filtering')

    def test_get_icephys_meta_parent_table(self):
        """
        Create the table hierarchy step-by-step and check that as we add tables the get_icephys_meta_parent_table
        returns the expected top table
        """
        local_nwbfile = ICEphysFile(
                session_description='my first synthetic recording',
                identifier='EXAMPLE_ID',
                session_start_time=datetime.now(tzlocal()),
                experimenter='Dr. Bilbo Baggins',
                lab='Bag End Laboratory',
                institution='University of Middle Earth at the Shire',
                experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
                session_id='LONELYMTN')
        # Add a device
        local_device = local_nwbfile.create_device(name='Heka ITC-1600')
        local_electrode = local_nwbfile.create_icephys_electrode(
            name="elec0",
            description='a mock intracellular electrode',
            device=local_device)
        local_stimulus = VoltageClampStimulusSeries(name="ccss",
                                                    data=[1, 2, 3, 4, 5],
                                                    starting_time=123.6,
                                                    rate=10e3,
                                                    electrode=local_electrode,
                                                    gain=0.02,
                                                    sweep_number=np.uint64(15))
        local_response = VoltageClampSeries(name='vcs',
                                            data=[0.1, 0.2, 0.3, 0.4, 0.5],
                                            conversion=1e-12,
                                            resolution=np.nan,
                                            starting_time=123.6,
                                            rate=20e3,
                                            electrode=local_electrode,
                                            gain=0.02,
                                            capacitance_slow=100e-12,
                                            resistance_comp_correction=70.0,
                                            sweep_number=np.uint64(15))
        local_nwbfile.add_stimulus_template(local_stimulus)
        # Check that none of the table exist yet
        self.assertIsNone(local_nwbfile.get_icephys_meta_parent_table())
        # Add a recording and confirm that intracellular_recordings is the top table
        _ = local_nwbfile.add_intracellular_recording(electrode=local_electrode,
                                                      stimulus=local_stimulus,
                                                      response=local_response,
                                                      id=np.int64(10))
        self.assertIsInstance(local_nwbfile.get_icephys_meta_parent_table(),
                              IntracellularRecordingsTable)
        # Add a sweep and check that the simultaneous_recordings table is the top table
        _ = local_nwbfile.add_icephys_simultaneous_recording(recordings=[0])
        self.assertIsInstance(local_nwbfile.get_icephys_meta_parent_table(),
                              SimultaneousRecordingsTable)
        # Add a sweep_sequence and check that it is now our top table
        _ = local_nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[0], stimulus_type="MyStimulusType")
        self.assertIsInstance(local_nwbfile.get_icephys_meta_parent_table(),
                              SequentialRecordingsTable)
        # Add a repetition and check that it is now our top table
        _ = local_nwbfile.add_icephys_repetition(sequential_recordings=[0])
        self.assertIsInstance(local_nwbfile.get_icephys_meta_parent_table(),
                              RepetitionsTable)
        # Add a condition and check that it is now our top table
        _ = local_nwbfile.add_icephys_experimental_condition(repetitions=[0])
        self.assertIsInstance(local_nwbfile.get_icephys_meta_parent_table(),
                              ExperimentalConditionsTable)

    def test_add_icephys_meta_full_roundtrip(self):
        """
        This test adds all data and then constructs step-by-step the full table structure
        Returns:

        """
        ####################################
        # Create our file and timeseries
        ###################################
        nwbfile = self.__get_icephysfile()
        device = self.__add_device(nwbfile)
        electrode = self.__add_electrode(nwbfile, device)
        # Add the data using standard methods from NWBFile
        stimulus = self.__get_stimuls(electrode=electrode)
        nwbfile.add_stimulus(stimulus)
        # Check that the deprecated sweep table has indeed not been created
        self.assertIsNone(nwbfile.sweep_table)
        response = self.__get_response(electrode=electrode)
        nwbfile.add_acquisition(response)
        # Check that the deprecated sweep table has indeed not been created
        self.assertIsNone(nwbfile.sweep_table)

        #############################################
        #  Test adding IntracellularRecordingsTable
        #############################################
        # Check that our IntracellularRecordingsTable table does not yet exists
        self.assertIsNone(nwbfile.intracellular_recordings)
        # Add an intracellular recording
        nwbfile.add_intracellular_recording(electrode=electrode,
                                            stimulus=stimulus,
                                            response=response,
                                            id=np.int64(10))
        nwbfile.add_intracellular_recording(electrode=electrode,
                                            stimulus=stimulus,
                                            response=response,
                                            id=np.int64(11))
        # Check that the table has been created
        self.assertIsNotNone(nwbfile.intracellular_recordings)
        # Check that the values in our row are correct
        self.assertEqual(len(nwbfile.intracellular_recordings), 2)
        res = nwbfile.intracellular_recordings[0]
        # Check the ID
        self.assertEqual(res.index[0], 10)
        # Check electrodes
        self.assertIs(res[('electrodes', 'electrode')].iloc[0], electrode)
        # Check the stimulus
        self.assertTupleEqual(res[('stimuli', 'stimulus')].iloc[0], (0, 5, stimulus))
        # Check the response
        self.assertTupleEqual(res[('responses', 'response')].iloc[0], (0, 5, response))

        #############################################
        #  Test adding SimultaneousRecordingsTable
        #############################################
        # Confirm that our SimultaneousRecordingsTable table does not yet exist
        self.assertIsNone(nwbfile.icephys_simultaneous_recordings)
        # Add a sweep
        nwbfile.add_icephys_simultaneous_recording(recordings=[0, 1], id=np.int64(12))
        # Check that the SimultaneousRecordingsTable table has been added
        self.assertIsNotNone(nwbfile.icephys_simultaneous_recordings)
        # Check that the values for our icephys_simultaneous_recordings table are correct
        self.assertListEqual(nwbfile.icephys_simultaneous_recordings.id[:], [12])
        self.assertListEqual(nwbfile.icephys_simultaneous_recordings['recordings'].data, [2])
        self.assertListEqual(nwbfile.icephys_simultaneous_recordings['recordings'].target.data[:], [0, 1])
        res = nwbfile.icephys_simultaneous_recordings[0]
        # check the id value
        self.assertEqual(res.index[0], 12)
        # Check that our sweep contains 2 IntracellularRecording
        self.assertEqual(len(res['recordings_id']), 2)

        #############################################
        #  Test adding a SweepSequence
        #############################################
        # Confirm that our SequentialRecordingsTable table does not yet exist
        self.assertIsNone(nwbfile.icephys_sequential_recordings)
        # Add a sweep
        nwbfile.add_icephys_sequential_recording(simultaneous_recordings=[0],
                                                 id=np.int64(15),
                                                 stimulus_type="MyStimulusType")
        # Check that the SimultaneousRecordingsTable table has been added
        self.assertIsNotNone(nwbfile.icephys_sequential_recordings)
        # Check that the values for our SimultaneousRecordingsTable table are correct
        res = nwbfile.icephys_sequential_recordings[0]
        # check the id value
        self.assertEqual(res.index[0], 15)
        # Check that our sweep contains 1 IntracellularRecording
        self.assertEqual(len(res['simultaneous_recordings_id']), 1)

        #############################################
        #  Test adding a Run
        #############################################
        # Confirm that our RepetitionsTable table does not yet exist
        self.assertIsNone(nwbfile.icephys_repetitions)
        # Add a repetition
        nwbfile.add_icephys_repetition(sequential_recordings=[0], id=np.int64(17))
        # Check that the SimultaneousRecordingsTable table has been added
        self.assertIsNotNone(nwbfile.icephys_repetitions)
        # Check that the values for our RepetitionsTable table are correct
        res = nwbfile.icephys_repetitions[0]
        # check the id value
        self.assertEqual(res.index[0], 17)
        # Check that our repetition contains 1 SweepSequence
        self.assertEqual(len(res['sequential_recordings_id']), 1)

        #############################################
        #  Test adding a Condition
        #############################################
        # Confirm that our RepetitionsTable table does not yet exist
        self.assertIsNone(nwbfile.icephys_experimental_conditions)
        # Add a condition
        nwbfile.add_icephys_experimental_condition(repetitions=[0], id=np.int64(19))
        # Check that the ExperimentalConditionsTable table has been added
        self.assertIsNotNone(nwbfile.icephys_experimental_conditions)
        # Check that the values for our ExperimentalConditionsTable table are correct
        res = nwbfile.icephys_experimental_conditions[0]
        # check the id value
        self.assertEqual(res.index[0], 19)
        # Check that our repetition contains 1 repetition
        self.assertEqual(len(res['repetitions_id']), 1)

        #############################################
        #  Test writing the file to disk
        #############################################
        # Write our file to disk
        # Write our test file
        with NWBHDF5IO(self.path, 'w') as nwbio:
            # # Uncomment the following lines to enable profiling for write
            # import cProfile, pstats, io
            # from pstats import SortKey
            # pr = cProfile.Profile()
            # pr.enable()
            nwbio.write(nwbfile)
            # pr.disable()
            # s = io.StringIO()
            # sortby = SortKey.CUMULATIVE
            # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            # ps.print_stats()
            # print(s.getvalue())

        #################################################################
        # Confirm that the low-level data has been written as expected
        # before we try to read the file back
        #################################################################
        with h5py.File(self.path, 'r') as io:
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['intracellular_recordings']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['intracellular_recordings']['electrodes']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['intracellular_recordings']['stimuli']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['intracellular_recordings']['responses']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['simultaneous_recordings']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['sequential_recordings']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['repetitions']['id'].shape,
                (1,))
            self.assertTupleEqual(
                io['/general']['intracellular_ephys']['experimental_conditions']['id'].shape,
                (1,))

        #############################################
        #  Test reading the file back from disk
        #############################################
        with NWBHDF5IO(self.path, 'r') as nwbio:
            # # Uncomment the following lines to enable profiling for read
            # import cProfile, pstats, io
            # from pstats import SortKey
            # pr = cProfile.Profile()
            # pr.enable()
            infile = nwbio.read()
            # pr.disable()
            # s = io.StringIO()
            # sortby = SortKey.CUMULATIVE
            # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            # ps.print_stats()
            # print(s.getvalue())

            ############################################################################
            #  Test that the  IntracellularRecordingsTable table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.intracellular_recordings)
            self.assertEqual(len(infile.intracellular_recordings), 1)
            res = infile.intracellular_recordings[0]
            # Check the ID
            self.assertEqual(res.index[0], 10)
            # Check the stimulus
            self.assertEqual(res[('stimuli', 'stimulus')].iloc[0][0], 0)
            self.assertEqual(res[('stimuli', 'stimulus')].iloc[0][1], 5)
            self.assertEqual(res[('stimuli', 'stimulus')].iloc[0][2].object_id,  stimulus.object_id)
            # Check the response
            self.assertEqual(res[('responses', 'response')].iloc[0][0], 0)
            self.assertEqual(res[('responses', 'response')].iloc[0][1], 5)
            self.assertEqual(res[('responses', 'response')].iloc[0][2].object_id,
                             nwbfile.get_acquisition('vcs').object_id)
            # Check the Intracellular electrode
            self.assertEqual(res[('electrodes', 'electrode')].iloc[0].object_id,  electrode.object_id)

            ############################################################################
            #  Test that the  SimultaneousRecordingsTable table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.icephys_simultaneous_recordings)
            self.assertEqual(len(infile.icephys_simultaneous_recordings), 1)
            res = infile.icephys_simultaneous_recordings[0]
            # Check the ID and len of the intracellular_recordings column
            self.assertEqual(res.index[0], 12)
            self.assertEqual(len(res['recordings_id']), 1)
            self.assertEqual(res.iloc[0]['recordings_id'], 10)  # Check id of the references recordings row

            ############################################################################
            #  Test that the  SequentialRecordingsTable table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.icephys_sequential_recordings)
            self.assertEqual(len(infile.icephys_sequential_recordings), 1)
            res = infile.icephys_sequential_recordings[0]
            # Check the ID and len of the simultaneous_recordings column
            self.assertEqual(res.index[0], 15)
            self.assertEqual(len(res['simultaneous_recordings_id']), 1)
            # Check id of the references simultaneous_recordings row
            self.assertEqual(res.iloc[0]['simultaneous_recordings_id'], 12)

            ############################################################################
            #  Test that the  RepetitionsTable table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.icephys_repetitions)
            self.assertEqual(len(infile.icephys_repetitions), 1)
            res = infile.icephys_repetitions[0]
            # Check the ID and len of the simultaneous_recordings column
            self.assertEqual(res.index[0], 17)
            self.assertEqual(len(res['sequential_recordings_id']), 1)
            self.assertEqual(res.iloc[0]['sequential_recordings_id'], 15)  # Check id of the sweep_sequence row

            ############################################################################
            #  Test that the ExperimentalConditionsTable table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.icephys_experimental_conditions)
            self.assertEqual(len(infile.icephys_experimental_conditions), 1)
            res = infile.icephys_experimental_conditions[0]
            # Check the ID and len of the simultaneous_recordings column
            self.assertEqual(res.index[0], 19)
            self.assertEqual(len(res['repetitions_id']), 1)
            self.assertEqual(res.iloc[0]['repetitions_id'], 17)  # Check id of the referenced repetitions row


if __name__ == '__main__':
    unittest.main()
