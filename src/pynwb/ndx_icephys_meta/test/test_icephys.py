import unittest2 as unittest
from pynwb import NWBFile
import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb.icephys import CurrentClampStimulusSeries, VoltageClampSeries
from pynwb.testing import remove_test_file
from hdmf.utils import docval, popargs
from pynwb import NWBHDF5IO


try:
    from ndx_icephys_meta.icephys import IntracellularRecordings, Sweeps, SweepSequences, Runs, Conditions
except ImportError:
    # If we are running tests directly in the GitHub repo without installing the extension
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import IntracellularRecordings, Sweeps, SweepSequences, Runs, Conditions


class ICEphysMetaTestBase(unittest.TestCase):
    """
    Base helper class for setting up tests for the ndx-icephys-meta extension
    """
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
                in_ir = infile.get_processing_module('icephys_meta_module').get('IntracellularRecordings')  # noqa F841
                # TODO compare the data in ir with in_ir to make sure the data was written and read correctly
            if sw is not None:
                in_sw = infile.get_processing_module('icephys_meta_module').get('Sweeps')  # noqa F841
                # TODO compare the data in sw with in_sw to make sure the data was written and read correctly
            if sws is not None:
                in_sws = infile.get_processing_module('icephys_meta_module').get('SweepSequences')  # noqa F841
                # TODO compare the data in sws with in_sws to make sure the data was written and read correctly
            if runs is not None:
                in_runs = infile.get_processing_module('icephys_meta_module').get('Runs')  # noqa F841
                # TODO compare the data in runs with in_runs to make sure the data was written and read correctly
            if cond is not None:
                in_con = infile.get_processing_module('icephys_meta_module').get('Conditions')  # noqa F841
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
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        res = ir[0]
        # Check the ID
        self.assertEqual(res[0], 10)
        # Check the stimulus
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 5)
        self.assertIs(res[1][2], self.stimulus)
        # Check the response
        self.assertEqual(res[2][0], 0)
        self.assertEqual(res[2][1], 5)
        self.assertIs(res[2][2], self.response)
        # Check the Intracellular electrode
        self.assertIs(res[3], self.electrode)
        # test writing out ir table
        self.write_test_helper(ir)

    def test_add_row_no_response(self):
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=None,
                         id=10)
        res = ir[0]
        # Check the ID
        self.assertEqual(res[0], 10)
        # Check the stimulus
        self.assertEqual(res[1][0], 0)
        self.assertEqual(res[1][1], 5)
        self.assertIs(res[1][2], self.stimulus)
        # Check the response
        self.assertEqual(res[2][0], -1)
        self.assertEqual(res[2][1], -1)
        self.assertIs(res[2][2], self.stimulus)
        # Check the Intracellular electrode
        self.assertIs(res[3], self.electrode)
        # test writing out ir table
        self.write_test_helper(ir)

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


class SweepsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Sweeps Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Sweeps container
        """
        ir = IntracellularRecordings()
        _ = Sweeps(intracellular_recordings=ir)
        self.assertTrue(True)

    def test_basic_write(self):
        """
        Populate, write, and read the Sweeps container and other required containers
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings=ir)
        sw.add_sweep(recordings=[0])
        self.write_test_helper(ir=ir, sw=sw)


class SweepSequencesTests(ICEphysMetaTestBase):
    """
    Test class for testing the SweepsSequences Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the SweepSequences container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings=ir)
        _ = SweepSequences(sweeps=sw)
        self.assertTrue(True)

    def test_basic_write(self):
        """
        Populate, write, and read the SweepSequences container and other required containers
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ])
        self.write_test_helper(ir=ir, sw=sw, sws=sws)


class RunsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Runs Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Runs container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings=ir)
        sws = SweepSequences(sweeps=sw)
        _ = Runs(sweep_sequences=sws)
        self.assertTrue(True)

    def test_basic_write(self):
        """
        Populate, write, and read the Runs container and other required containers
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ])
        runs = Runs(sweep_sequences=sws)
        runs.add_run(sweep_sequences=[0, ])
        self.write_test_helper(ir=ir, sw=sw, sws=sws, runs=runs)


class ConditionsTests(ICEphysMetaTestBase):
    """
    Test class for testing the Conditions Container class
    """

    def test_init(self):
        """
        Test  __init__ to make sure we can instantiate the Conditions container
        """
        ir = IntracellularRecordings()
        sw = Sweeps(intracellular_recordings=ir)
        sws = SweepSequences(sweeps=sw)
        runs = Runs(sweep_sequences=sws)
        _ = Conditions(runs=runs)
        self.assertTrue(True)

    def test_basic_write(self):
        """
        Populate, write, and read the Conditions container and other required containers
        """
        ir = IntracellularRecordings()
        ir.add_recording(electrode=self.electrode,
                         stimulus=self.stimulus,
                         response=self.response,
                         id=10)
        sw = Sweeps(intracellular_recordings=ir)
        sw.add_sweep(recordings=[0])
        sws = SweepSequences(sw)
        sws.add_sweep_sequence(sweeps=[0, ])
        runs = Runs(sweep_sequences=sws)
        runs.add_run(sweep_sequences=[0, ])
        cond = Conditions(runs=runs)
        cond.add_condition(runs=[0, ])
        self.write_test_helper(ir=ir, sw=sw, sws=sws, runs=runs, cond=cond)


if __name__ == '__main__':
    unittest.main()
