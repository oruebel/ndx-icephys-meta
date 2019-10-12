import unittest2 as unittest
from pynwb import NWBFile
import numpy as np
from datetime import datetime
from dateutil.tz import tzlocal
from pynwb.icephys import CurrentClampStimulusSeries, VoltageClampSeries


try:
    from ndx_icephys_meta.icephys import *
except ImportError:
    import os, sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import *

class IntracellularRecordingsTests(unittest.TestCase):

    def setUp(self):
        # Create an example nwbfile with a device, intracellular electrode, stimulus, and response
        self.nwbfile = NWBFile('my first synthetic recording', 'EXAMPLE_ID', datetime.now(tzlocal()),
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


    def tearDown(self):
        pass

    def test_init(self):
        _ = IntracellularRecordings()
        self.assertTrue(True)

    def test_add_row(self):
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

        # For testing we'll add our IR table as a processing module and write the file to disk
        # test_module = self.nwbfile.create_processing_module(name='icephys_meta_module',
        #                                                     description='icephys metadata module')
        # test_module.add(ir)
        # # Write our test file
        # from pynwb import NWBHDF5IO
        # with NWBHDF5IO('icephys_example.nwb', 'w') as io:
        #     io.write(self.nwbfile)

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
        self.assertIsNone(res[2][2])
        # Check the Intracellular electrode
        self.assertIs(res[3], self.electrode)

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



if __name__ == '__main__':
    unittest.main()
