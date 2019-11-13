import unittest2 as unittest
import warnings
import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb import NWBFile
from pynwb.icephys import CurrentClampStimulusSeries, VoltageClampSeries
from pynwb.testing import remove_test_file
from pynwb import NWBHDF5IO
from hdmf.utils import docval, popargs

try:
    from ndx_icephys_meta.icephys import (IntracellularRecordings,
                                          Sweeps,
                                          SweepSequences,
                                          Runs,
                                          Conditions,
                                          ICEphysFile)
except ImportError:
    # If we are running tests directly in the GitHub repo without installing the extension
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import (IntracellularRecordings,
                                          Sweeps,
                                          SweepSequences,
                                          Runs,
                                          Conditions,
                                          ICEphysFile)


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

        :returns: Tuple of CurrentClampStimulusSeries with the stimulus and VoltageClampSeries with the response.
        """
        stimulus = CurrentClampStimulusSeries(
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
        electrode0 = nwbfile.create_ic_electrode(name="elec0",
                                                 description='a mock intracellular electrode',
                                                 device=device)
        # Add an intracellular electrode
        electrode1 = nwbfile.create_ic_electrode(name="elec1",
                                                 description='another mock intracellular electrode',
                                                 device=device)
        # Add the intracelluar recordings
        for sweep_number in range(20):
            elec = (electrode0 if (sweep_number % 2 == 0) else electrode1)
            stim, resp = cls.create_stimulus_and_response(sweep_number=sweep_number,
                                                          electrode=elec,
                                                          randomize_data=randomize_data)
            nwbfile.add_intracellular_recording(electrode=elec,
                                                stimulus=stim,
                                                response=resp,
                                                id=sweep_number)
        nwbfile.intracellular_recordings.add_column(name='stimulus_type',
                                                    data=['A1', 'A2',
                                                          'B1', 'B2',
                                                          'C1', 'C2', 'C3',
                                                          'D1', 'D2', 'D3',
                                                          'A1', 'A2',
                                                          'B1', 'B2',
                                                          'C1', 'C2', 'C3',
                                                          'D1', 'D2', 'D3'],
                                                    description='String indicating the type of stimulus applied')
        # Add sweeps
        nwbfile.add_ic_sweep(recordings=[0, 1], id=100)
        nwbfile.add_ic_sweep(recordings=[2, 3], id=101)
        nwbfile.add_ic_sweep(recordings=[4, 5, 6], id=102)
        nwbfile.add_ic_sweep(recordings=[7, 8, 9], id=103)
        nwbfile.add_ic_sweep(recordings=[10, 11], id=104)
        nwbfile.add_ic_sweep(recordings=[12, 13], id=105)
        nwbfile.add_ic_sweep(recordings=[14, 15, 16], id=106)
        nwbfile.add_ic_sweep(recordings=[17, 18, 19], id=107)
        if add_custom_columns:
            nwbfile.ic_sweeps.add_column(name='tag',
                                         data=np.arange(8),
                                         description='some integer tag for a sweep')

        # Add sweep sequences
        nwbfile.add_ic_sweep_sequence(sweeps=[0, 1], id=1000)
        nwbfile.add_ic_sweep_sequence(sweeps=[2, ], id=1001)
        nwbfile.add_ic_sweep_sequence(sweeps=[3, ], id=1002)
        nwbfile.add_ic_sweep_sequence(sweeps=[4, 5], id=1003)
        nwbfile.add_ic_sweep_sequence(sweeps=[6, ], id=1004)
        nwbfile.add_ic_sweep_sequence(sweeps=[7, ], id=1005)
        if add_custom_columns:
            nwbfile.ic_sweep_sequences.add_column(name='type',
                                                  data=['T1', 'T2', 'T3', 'T1', 'T2', 'T3'],
                                                  description='type of the sweep sequence')

        # Add runs
        nwbfile.add_ic_run(sweep_sequences=[0, ], id=10000)
        nwbfile.add_ic_run(sweep_sequences=[1, 2], id=10001)
        nwbfile.add_ic_run(sweep_sequences=[3, ], id=10002)
        nwbfile.add_ic_run(sweep_sequences=[4, 5], id=10003)
        if add_custom_columns:
            nwbfile.ic_runs.add_column(name='type',
                                       data=['R1', 'R2', 'R1', 'R2'],
                                       description='some run type indicator')

        # Add conditions
        nwbfile.add_ic_condition(runs=[0, 1], id=100000)
        nwbfile.add_ic_condition(runs=[2, 3], id=100001)
        if add_custom_columns:
            nwbfile.ic_conditions.add_column(name='temperature',
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
        self.nwbfile = NWBFile(
            session_description='my first synthetic recording',
            identifier='EXAMPLE_ID',
            session_start_time=datetime.now(tzlocal()),
            experimenter='Dr. Bilbo Baggins',
            lab='Bag End Laboratory',
            institution='University of Middle Earth at the Shire',
            experiment_description='I went on an adventure with thirteen dwarves to reclaim vast treasures.',
            session_id='LONELYMTN')
        self.device = self.nwbfile.create_device(name='Heka ITC-1600')
        self.electrode = self.nwbfile.create_ic_electrode(name="elec0",
                                                          description='a mock intracellular electrode',
                                                          device=self.device)
        self.stimulus = CurrentClampStimulusSeries(name="ccss",
                                                   data=[1, 2, 3, 4, 5],
                                                   starting_time=123.6,
                                                   rate=10e3,
                                                   electrode=self.electrode,
                                                   gain=0.02,
                                                   sweep_number=15)
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
                                           sweep_number=15)
        self.nwbfile.add_acquisition(self.response)
        self.path = 'test_icephys_meta_intracellularrecording.h5'

    def tearDown(self):
        remove_test_file(self.path)

    @docval({'name': 'ir',
             'type': IntracellularRecordings,
             'doc': 'Intracellular recording to be added to the file before write',
             'default': None},
            {'name': 'sw',
             'type': Sweeps,
             'doc': 'Sweeps table to be added to the file before write',
             'default': None},
            {'name': 'sws',
             'type': SweepSequences,
             'doc': 'SweepSequences table to be added to the file before write',
             'default': None},
            {'name': 'runs',
             'type': Runs,
             'doc': 'Runs table to be added to the file before write',
             'default': None},
            {'name': 'cond',
             'type': Conditions,
             'doc': 'Conditions table to be added to the file before write',
             'default': None})
    def write_test_helper(self, **kwargs):
        ir, sw, sws, runs, cond = popargs('ir', 'sw', 'sws', 'runs', 'cond', kwargs)
        # For testing we'll add our IR table as a processing module and write the file to disk
        if ir is not None or sw is not None:
            test_module = self.nwbfile.create_processing_module(name='icephys_meta_module',
                                                                description='icephys metadata module')
            if ir is not None:
                test_module.add(ir)
            if sw is not None:
                test_module.add(sw)
            if sws is not None:
                test_module.add(sws)
            if runs is not None:
                test_module.add(runs)
            if cond is not None:
                test_module.add(cond)

        # Write our test file
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(self.nwbfile)
        # Test that we can read the file
        with NWBHDF5IO(self.path, 'r') as io:
            infile = io.read()
            if ir is not None:
                in_ir = infile.get_processing_module('icephys_meta_module').get('intracellular_recordings')  # noqa F841
                # TODO compare the data in ir with in_ir to make sure the data was written and read correctly
            if sw is not None:
                in_sw = infile.get_processing_module('icephys_meta_module').get('sweeps')  # noqa F841
                # TODO compare the data in sw with in_sw to make sure the data was written and read correctly
            if sws is not None:
                in_sws = infile.get_processing_module('icephys_meta_module').get('sweep_sequences')  # noqa F841
                # TODO compare the data in sws with in_sws to make sure the data was written and read correctly
            if runs is not None:
                in_runs = infile.get_processing_module('icephys_meta_module').get('runs')  # noqa F841
                # TODO compare the data in runs with in_runs to make sure the data was written and read correctly
            if cond is not None:
                in_con = infile.get_processing_module('icephys_meta_module').get('conditions')  # noqa F841
                # TODO compare the data in cond with in_cond to make sure the data was written and read correctly


class IntracellularRecordingsTests(ICEphysMetaTestBase):
    """
    Class for testing the IntracellularRecordings Container
    """

    def test_init(self):
        _ = IntracellularRecordings()
        self.assertTrue(True)

    def test_add_row(self):
        # Add a row to our IR table
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=10)
        res = ir[0]
        # Check the ID
        self.assertEqual(res.index[0], 10)
        # Check the stimulus
        self.assertEqual(res.iloc[0]['stimulus'][0], 0)
        self.assertEqual(res.iloc[0]['stimulus'][1], 5)
        self.assertIs(res.iloc[0]['stimulus'][2], self.stimulus)
        # Check the response
        self.assertEqual(res.iloc[0]['response'][0], 0)
        self.assertEqual(res.iloc[0]['response'][1], 5)
        self.assertIs(res.iloc[0]['response'][2], self.response)
        # Check the Intracellular electrode
        self.assertIs(res.iloc[0]['electrode'], self.electrode)
        # test writing out ir table
        self.write_test_helper(ir)
        # test that we get the correct row index back
        self.assertEqual(row_index, 0)

    def test_add_row_no_response(self):
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=None,
                                     id=10)
        res = ir[0]
        # Check the ID
        self.assertEqual(res.index[0], 10)
        # Check the stimulus
        self.assertEqual(res.iloc[0]['stimulus'][0], 0)
        self.assertEqual(res.iloc[0]['stimulus'][1], 5)
        self.assertIs(res.iloc[0]['stimulus'][2], self.stimulus)
        # Check the response
        self.assertEqual(res.iloc[0]['response'][0], -1)
        self.assertEqual(res.iloc[0]['response'][1], -1)
        self.assertIs(res.iloc[0]['response'][2], self.stimulus)
        # Check the Intracellular electrode
        self.assertIs(res.iloc[0]['electrode'], self.electrode)
        # test writing out ir table
        self.write_test_helper(ir)
        # test that we get the correct row index back
        self.assertEqual(row_index, 0)

    def test_add_row_index_out_of_range(self):

        # Stimulus/Response start_index to large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_start_index=10,
                             response=self.response,
                             id=10)
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_start_index=10,
                             response=self.response,
                             id=10)
        # Stimulus/Reponse index count too large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_index_count=10,
                             response=self.response,
                             id=10)
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_index_count=10,
                             response=self.response,
                             id=10)
        # Stimulus/Reponse start+count combination too large
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             stimulus_start_index=3,
                             stimulus_index_count=4,
                             response=self.response,
                             id=10)
        with self.assertRaises(IndexError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response_start_index=3,
                             response_index_count=4,
                             response=self.response,
                             id=10)

    def test_add_row_no_stimulus_and_response(self):
        with self.assertRaises(ValueError):
            ir = IntracellularRecordings()
            ir.add_recording(electrode=self.electrode,
                             stimulus=None,
                             response=None)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on Runs table
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        with self.assertRaises(ValueError):
            ir.add_recording(electrode=self.electrode,
                             stimulus=self.stimulus,
                             response=self.response,
                             id=10)


class SweepsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Sweeps Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Sweeps container
        """
        ir = IntracellularRecordings()
        _ = Sweeps(intracellular_recordings_table=ir)
        self.assertTrue(True)

    def test_missing_intracellular_recordings_on_init(self):
        """
        Test that ValueError is raised when intracellular_recordings is missing. This is
        allowed only on read where the intracellular_recordings table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = Sweeps()

    def test_basic_write(self):
        """
        Populate, write, and read the Sweeps container and other required containers
        """
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=10)
        self.assertEqual(row_index, 0)
        sw = Sweeps(intracellular_recordings_table=ir)
        row_index = sw.add_sweep(recordings=[0])
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on Runs table
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings_table=ir)
        sw.add_sweep(recordings=[0], id=10)
        with self.assertRaises(ValueError):
            sw.add_sweep(recordings=[0], id=10)


class SweepSequencesTests(ICEphysMetaTestBase):
    """
    Test class for testing the SweepsSequences Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the SweepSequences container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings_table=ir)
        _ = SweepSequences(sweeps_table=sw)
        self.assertTrue(True)

    def test_missing_sweeps_on_init(self):
        """
        Test that ValueError is raised when sweeps is missing. This is
        allowed only on read where the sweeps table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = SweepSequences()

    def test_basic_write(self):
        """
        Populate, write, and read the SweepSequences container and other required containers
        """
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=10)
        self.assertEqual(row_index, 0)
        sw = Sweeps(intracellular_recordings_table=ir)
        row_index = sw.add_sweep(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SweepSequences(sw)
        row_index = sws.add_sweep_sequence(sweeps=[0, ])
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw, sws=sws)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on Runs table
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings_table=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ], id=10)
        with self.assertRaises(ValueError):
            sws.add_sweep_sequence(sweeps=[0, ], id=10)


class RunsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Runs Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Runs container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings_table=ir)
        sws = SweepSequences(sweeps_table=sw)
        _ = Runs(sweep_sequences_table=sws)
        self.assertTrue(True)

    def test_missing_sweepsequences_on_init(self):
        """
        Test that ValueError is raised when sweep_sequences is missing. This is
        allowed only on read where the sweep_sequences table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = Runs()

    def test_basic_write(self):
        """
        Populate, write, and read the Runs container and other required containers
        """
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=10)
        self.assertEqual(row_index, 0)
        sw = Sweeps(intracellular_recordings_table=ir)
        row_index = sw.add_sweep(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SweepSequences(sw)
        row_index = sws.add_sweep_sequence(sweeps=[0, ])
        self.assertEqual(row_index, 0)
        runs = Runs(sweep_sequences_table=sws)
        runs.add_run(sweep_sequences=[0, ])
        self.write_test_helper(ir=ir, sw=sw, sws=sws, runs=runs)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on Runs table
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings_table=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ])
        runs = Runs(sweep_sequences_table=sws)
        runs.add_run(sweep_sequences=[0, ], id=10)
        with self.assertRaises(ValueError):
            runs.add_run(sweep_sequences=[0, ], id=10)


class ConditionsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Conditions Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Conditions container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings_table=ir)
        sws = SweepSequences(sweeps_table=sw)
        runs = Runs(sweep_sequences_table=sws)
        _ = Conditions(runs_table=runs)
        self.assertTrue(True)

    def test_missing_runs_on_init(self):
        """
        Test that ValueError is raised when runs is missing. This is
        allowed only on read where the runs table is already set
        from the file.
        """
        with self.assertRaises(ValueError):
            _ = Conditions()

    def test_basic_write(self):
        """
        Populate, write, and read the Conditions container and other required containers
        """
        ir = IntracellularRecordings()
        row_index = ir.add_recording(electrode=self.electrode,
                                     stimulus=self.stimulus,
                                     response=self.response,
                                     id=10)
        self.assertEqual(row_index, 0)
        sw = Sweeps(intracellular_recordings_table=ir)
        row_index = sw.add_sweep(recordings=[0])
        self.assertEqual(row_index, 0)
        sws = SweepSequences(sw)
        row_index = sws.add_sweep_sequence(sweeps=[0, ])
        self.assertEqual(row_index, 0)
        runs = Runs(sweep_sequences_table=sws)
        row_index = runs.add_run(sweep_sequences=[0, ])
        self.assertEqual(row_index, 0)
        cond = Conditions(runs_table=runs)
        row_index = cond.add_condition(runs=[0, ])
        self.assertEqual(row_index, 0)
        self.write_test_helper(ir=ir, sw=sw, sws=sws, runs=runs, cond=cond)

    def test_enforce_unique_id(self):
        """
        Test to ensure that unique ids are enforced on Runs table
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings_table=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ])
        runs = Runs(sweep_sequences_table=sws)
        runs.add_run(sweep_sequences=[0, ])
        cond = Conditions(runs_table=runs)
        cond.add_condition(runs=[0, ], id=10)
        with self.assertRaises(ValueError):
            cond.add_condition(runs=[0, ], id=10)


class ICEphysFileTests(ICEphysMetaTestBase):
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
        return icefile.create_ic_electrode(name="elec0",
                                           description='a mock intracellular electrode',
                                           device=device)

    def __get_stimuls(self, electrode):
        """
        Create a dummy CurrentClampStimulusSeries
        """
        return CurrentClampStimulusSeries(
            name="ccss",
            data=[1, 2, 3, 4, 5],
            starting_time=123.6,
            rate=10e3,
            electrode=electrode,
            gain=0.02,
            sweep_number=15)

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
            sweep_number=15)

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the ICEphysFileTests container
        """
        _ = self.__get_icephysfile()

    def test_deprecate_sweeps_on_add_stimulus(self):
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
            warnings.simplefilter("always")  # Trigger all warnings
            nwbfile.add_stimulus(stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)
            assert issubclass(w[-1].category, DeprecationWarning)
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_acquisition(responce, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprecate_sweeps_on_add_acquistion(self):
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
            # make sure we don't trigger the same deprecation warning twice
            nwbfile.add_stimulus(stimulus, use_sweep_table=True)
            self.assertEqual(len(w), 1)

    def test_deprecate_sweeps_on_init(self):
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

    @unittest.skip("Test not implemented yet")
    def test_add_ic_conditions_column(self):
        """
        Test that we can add a dynamic column to the conditions via nwb.add_ic_conditions_column(...)
        """
        pass

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
        #  Test adding IntracellularRecordings
        #############################################
        # Check that our IntracellularRecordings table does not yet exists
        self.assertIsNone(nwbfile.intracellular_recordings)
        # Add an intracellular recording
        nwbfile.add_intracellular_recording(electrode=electrode,
                                            stimulus=stimulus,
                                            response=response,
                                            id=10)
        # Check that the table has been created
        self.assertIsNotNone(nwbfile.intracellular_recordings)
        # Check that the values in our row are correct
        self.assertEqual(len(nwbfile.intracellular_recordings), 1)
        res = nwbfile.intracellular_recordings[0]
        # Check the ID
        self.assertEqual(res.index[0], 10)
        # Check the stimulus
        self.assertEqual(res.iloc[0]['stimulus'][0], 0)
        self.assertEqual(res.iloc[0]['stimulus'][1], 5)
        self.assertIs(res.iloc[0]['stimulus'][2], stimulus)
        # Check the response
        self.assertEqual(res.iloc[0]['response'][0], 0)
        self.assertEqual(res.iloc[0]['response'][1], 5)
        self.assertIs(res.iloc[0]['response'][2], response)
        # Check the Intracellular electrode
        self.assertIs(res.iloc[0]['electrode'], electrode)

        #############################################
        #  Test adding Sweeps
        #############################################
        # Confirm that our Sweeps table does not yet exist
        self.assertIsNone(nwbfile.ic_sweeps)
        # Add a sweep
        nwbfile.add_ic_sweep(recordings=[0], id=12)
        # Check that the Sweeps table has been added
        self.assertIsNotNone(nwbfile.ic_sweeps)
        # Check that the values for our ic_sweeps table are correct
        res = nwbfile.ic_sweeps[0]
        # check the id value
        self.assertEqual(res.index[0], 12)
        # Check that our sweep contains 1 IntracellularRecording
        self.assertEqual(len(res.iloc[0]['recordings']), 1)

        #############################################
        #  Test adding a SweepSequence
        #############################################
        # Confirm that our SweepSequences table does not yet exist
        self.assertIsNone(nwbfile.ic_sweep_sequences)
        # Add a sweep
        nwbfile.add_ic_sweep_sequence(sweeps=[0], id=15)
        # Check that the Sweeps table has been added
        self.assertIsNotNone(nwbfile.ic_sweep_sequences)
        # Check that the values for our Sweeps table are correct
        res = nwbfile.ic_sweep_sequences[0]
        # check the id value
        self.assertEqual(res.index[0], 15)
        # Check that our sweep contains 1 IntracellularRecording
        self.assertEqual(len(res.iloc[0]['sweeps']), 1)

        #############################################
        #  Test adding a Run
        #############################################
        # Confirm that our Runs table does not yet exist
        self.assertIsNone(nwbfile.ic_runs)
        # Add a run
        nwbfile.add_ic_run(sweep_sequences=[0], id=17)
        # Check that the Sweeps table has been added
        self.assertIsNotNone(nwbfile.ic_runs)
        # Check that the values for our Runs table are correct
        res = nwbfile.ic_runs[0]
        # check the id value
        self.assertEqual(res.index[0], 17)
        # Check that our run contains 1 SweepSequence
        self.assertEqual(len(res.iloc[0]['sweep_sequences']), 1)

        #############################################
        #  Test adding a Condition
        #############################################
        # Confirm that our Runs table does not yet exist
        self.assertIsNone(nwbfile.ic_conditions)
        # Add a condition
        nwbfile.add_ic_condition(runs=[0], id=19)
        # Check that the Conditions table has been added
        self.assertIsNotNone(nwbfile.ic_conditions)
        # Check that the values for our Conditions table are correct
        res = nwbfile.ic_conditions[0]
        # check the id value
        self.assertEqual(res.index[0], 19)
        # Check that our run contains 1 run
        self.assertEqual(len(res.iloc[0]['runs']), 1)

        #############################################
        #  Test writing the file to disk
        #############################################
        # Write our file to disk
        # Write our test file
        with NWBHDF5IO(self.path, 'w') as io:
            io.write(nwbfile)

        #############################################
        #  Test reading the file back from disk
        #############################################
        with NWBHDF5IO(self.path, 'r') as io:
            infile = io.read()

            ############################################################################
            #  Test that the  IntracellularRecordings table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.intracellular_recordings)
            self.assertEqual(len(infile.intracellular_recordings), 1)
            res = nwbfile.intracellular_recordings[0]
            # Check the ID
            self.assertEqual(res.index[0], 10)
            # Check the stimulus
            self.assertEqual(res.iloc[0]['stimulus'][0], 0)
            self.assertEqual(res.iloc[0]['stimulus'][1], 5)
            self.assertIs(res.iloc[0]['stimulus'][2], stimulus)
            # Check the response
            self.assertEqual(res.iloc[0]['response'][0], 0)
            self.assertEqual(res.iloc[0]['response'][1], 5)
            self.assertIs(res.iloc[0]['response'][2],  nwbfile.get_acquisition('vcs'))
            # Check the Intracellular electrode
            self.assertIs(res.iloc[0]['electrode'], electrode)

            ############################################################################
            #  Test that the  Sweeps table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.ic_sweeps)
            self.assertEqual(len(infile.ic_sweeps), 1)
            res = nwbfile.ic_sweeps[0]
            # Check the ID and len of the intracellular_recordings column
            self.assertEqual(res.index[0], 12)
            self.assertEqual(len(res.iloc[0]['recordings']), 1)
            self.assertEqual(res.iloc[0]['recordings'].index[0], 10)  # Check id of the references ic_recordings row

            ############################################################################
            #  Test that the  SweepSequences table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.ic_sweep_sequences)
            self.assertEqual(len(infile.ic_sweep_sequences), 1)
            res = nwbfile.ic_sweep_sequences[0]
            # Check the ID and len of the sweeps column
            self.assertEqual(res.index[0], 15)
            self.assertEqual(len(res.iloc[0]['sweeps']), 1)
            self.assertEqual(res.iloc[0]['sweeps'].index[0], 12)  # Check id of the references sweeps row

            ############################################################################
            #  Test that the  Runs table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.ic_runs)
            self.assertEqual(len(infile.ic_runs), 1)
            res = nwbfile.ic_runs[0]
            # Check the ID and len of the sweeps column
            self.assertEqual(res.index[0], 17)
            self.assertEqual(len(res.iloc[0]['sweep_sequences']), 1)
            self.assertEqual(res.iloc[0]['sweep_sequences'].index[0], 15)  # Check id of the sweep_sequence row

            ############################################################################
            #  Test that the Conditions table has been written correctly
            ############################################################################
            self.assertIsNotNone(infile.ic_conditions)
            self.assertEqual(len(infile.ic_conditions), 1)
            res = nwbfile.ic_conditions[0]
            # Check the ID and len of the sweeps column
            self.assertEqual(res.index[0], 19)
            self.assertEqual(len(res.iloc[0]['runs']), 1)
            self.assertEqual(res.iloc[0]['runs'].index[0], 17)  # Check id of the referenced runs row

    @unittest.skip("Test not implemented yet")
    def test_add_intracellular_recordings_column(self):
        """
        Test that we can add a dynamic column to the intracellular_recordings
        via nwbfile.add_intracellular_recordings_column
        """
        pass

    @unittest.skip("Test not implemented yet")
    def test_add_ic_sweeps_column(self):
        """
        Test that we can add a dynamic column to the sweeps via nwbfile.add_ic_sweeps_column
        """
        pass

    @unittest.skip("Test not implemented yet")
    def test_add_ic_sweep_seqences_column(self):
        """
        Test that we can add a dynamic column to the sweep_sequences via nwbfile.add_ic_sweep_sequences_column
        """
        pass

    @unittest.skip("Test not implemented yet")
    def test_add_ic_runs_column(self):
        """
        Test that we can add a dynamic column to the runs via nwbfile.add_ic_runs_column
        """
        pass


if __name__ == '__main__':
    unittest.main()
