"""
Unit test module for testing the AlignedDynamicTableContainer
"""
import unittest2 as unittest
import os
import warnings

import numpy as np
from pynwb.testing import remove_test_file
from pynwb import NWBHDF5IO
from pandas.testing import assert_frame_equal

try:
    from hdmf.common import DynamicTable, VectorData
except ImportError:
    from pynwb.core import DynamicTable, VectorData

try:
    from ndx_icephys_meta.icephys import AlignedDynamicTable
except ImportError:
    # If we are running tests directly in the GitHub repo without installing the extension
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import AlignedDynamicTable


# TODO Test add_row
# TODO Test add_column
# TODO Test add_category
# TODO Test to_dataframe
# TODO Test __getitem__
# TODO Test the various error cases for __init__


class TestAlignedDynamicTableContainer(unittest.TestCase):
    """
    Test the AlignedDynamicTable class.
    """
    def setUp(self):
        warnings.simplefilter("always")  # Trigger all warnings
        self.path = 'test_icephys_meta_intracellularrecording.h5'

    def tearDown(self):
        remove_test_file(self.path)

    def test_init(self):
        """Test that just checks that populating the tables with data works correctly"""
        AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container')

    def test_init_with_custom_empty_categories(self):
        """Test that we can create an empty table with custom categories"""
        category_names = ['test1', 'test2', 'test3']
        categories = [DynamicTable(name=val, description=val+" description") for val in category_names]
        AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)

    def test_init_with_custom_nonempty_categories(self):
        """Test that we can create an empty table with custom categories"""
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)

    def test_init_with_custom_nonempty_categories_and_main(self):
        """
        Test that we can create an empty table with custom categories. This also tests
        the contains, categories, main_table methods.
        """
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        temp = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)

        self.assertEqual(temp.categories, category_names)
        self.assertTrue('test1' in temp)  # test that contains category works
        self.assertTrue(('test1', 'c1') in temp)  # test that contains a column works
        with self.assertRaises(ValueError):  # test the error case of a tuple with len !-2
            ('test1', 'c1', 't3') in temp

    def test_init_with_custom_misaligned_categories(self):
        """Test that we can create an empty table with custom categories"""
        num_rows = 10
        val1 = 'test1'
        val2 = 'test2'
        categories = [DynamicTable(name=val1,
                                   description=val1+" description",
                                   columns=[VectorData(name=val1+t,
                                                       description=val1+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]),
                      DynamicTable(name=val1,
                                   description=val1+" description",
                                   columns=[VectorData(name=val2+t,
                                                       description=val2+t+' description',
                                                       data=np.arange(num_rows+1)) for t in ['c1', 'c2', 'c3']])
                      ]
        with self.assertRaises(ValueError):
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                category_tables=categories)

    def test_init_with_duplicate_custom_categories(self):
        """Test that we can create an empty table with custom categories"""
        category_names = ['test1', 'test1']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        with self.assertRaises(ValueError):
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                category_tables=categories)

    def test_round_trip_container(self):
        """Test read and write the container by itself"""
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        curr = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)

        with NWBHDF5IO(self.path, 'w') as io:
            io.write(curr)

        with NWBHDF5IO(self.path, 'r') as io:
            incon = io.read()
            self.assertListEqual(incon.categories, curr.categories)
            for n in category_names:
                assert_frame_equal(incon[n], curr[n])


if __name__ == '__main__':
    unittest.main()
