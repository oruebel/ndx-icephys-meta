"""
Unit test module for testing the HierarchicalDynamicTableMixin class

To test the conversion of DynamicTables to pandas.DataFrame we store the expected pandas
results in an HDF5 file on the side of the tests as setting up the tables manually can
be tricky. If we have confirmed that the mixing is working as expected we can update
the expected test results by enabling the test_generate_reference_testdata test function
and running the tests.
"""
import unittest
import numpy as np
from hdmf.utils import docval, popargs, get_docval, call_docval_func
import pandas
import os

try:
    from hdmf.common import DynamicTable
except ImportError:
    from pynwb.core import DynamicTable

try:
    from ndx_icephys_meta.icephys import HierarchicalDynamicTableMixin
except ImportError:
    # If we are running tests directly in the GitHub repo without installing the extension
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ndx_icephys_meta.icephys import HierarchicalDynamicTableMixin


class HierarchicalTableLevel(HierarchicalDynamicTableMixin, DynamicTable):
    """Test table class that references another table"""
    __columns__ = (
        {'name': 'child_table_refs',
         'description': 'Column with a references to the next level in the hierarchy',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'name', 'type': str, 'doc': 'The name of the table'},
            {'name': 'child_table',
             'type': DynamicTable,
             'doc': 'the child DynamicTable this HierarchicalTableLevel point to.'},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        # Define default name and description settings
        kwargs['description'] = (kwargs['name'] + " HierarchicalTableLevel")
        # Initialize the DynamicTable
        call_docval_func(super(HierarchicalTableLevel, self).__init__, kwargs)
        if self['child_table_refs'].target.table is None:
            self['child_table_refs'].target.table = popargs('child_table', kwargs)


class TestHierarchicalDynamicTableMixin(unittest.TestCase):
    """
    Test the HierarchicalDynamicTableMixin class.

    Since the HierarchicalDynamicTableMixin only implements front-end convenient function
    we do not need to worry about I/O, but it is sufficient if we test with container
    class. The only time I/O becomes relevant is on read in case that, e.g., a
    h5py.Dataset may behave differently than a numpy array.
    """
    def setUp(self):
        self.table_level0 = DynamicTable(name='level0', description="level0 DynamicTable")
        self.table_level1 = HierarchicalTableLevel(name='level1', child_table=self.table_level0)
        self.table_level2 = HierarchicalTableLevel(name='level2', child_table=self.table_level1)

    def tearDown(self):
        del self.table_level0
        del self.table_level1
        del self.table_level2

    def popolate_tables(self):
        """Helper function to populate our tables generate in setUp with some simple data"""
        self.table_level0.add_row(id=10)
        self.table_level0.add_row(id=11)
        self.table_level0.add_row(id=12)
        self.table_level0.add_row(id=13)
        self.table_level0.add_column(data=['tag1', 'tag2', 'tag2', 'tag1', 'tag3', 'tag4', 'tag5'],
                                     name='tags',
                                     description='custom tags',
                                     index=[1, 2, 4, 7])
        self.table_level0.add_column(data=np.arange(4),
                                     name='myid',
                                     description='custom ids',
                                     index=False)
        self.table_level1.add_row(id=0, child_table_refs=[0, 1])
        self.table_level1.add_row(id=1, child_table_refs=[2])
        self.table_level1.add_row(id=2, child_table_refs=[3])
        self.table_level1.add_column(data=['tag1', 'tag2', 'tag2'],
                                     name='tag',
                                     description='custom tag',
                                     index=False)
        self.table_level1.add_column(data=['tag1', 'tag2', 'tag2', 'tag1', 'tag3', 'tag4', 'tag5'],
                                     name='tags',
                                     description='custom tags',
                                     index=[2, 4, 7])
        self.table_level2.add_row(id=0, child_table_refs=[0, ])
        self.table_level2.add_row(id=1, child_table_refs=[1, 2])
        self.table_level2.add_column(data=[10, 12],
                                     name='filter',
                                     description='filter value',
                                     index=False)

    @unittest.skip("Enable this test if you want to generate a new reference test data for comparison")
    def test_generate_reference_testdata(self):
        """
        Save reference results for the tests evaluating that the to_denormalized_dataframe
        and to_hierarchical_dataframe functions are working. This test should be enabled
        to regenerate the reference results. CAUTION: We should confirm first that the
        functions produce the correct results.
        """
        self.popolate_tables()
        ref_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'referencedata_test_hierarchical_dynamic_table_mixin.h5')
        if os.path.exists(ref_filename):
            os.remove(ref_filename)
        print("\n Generating reference test data file %s" % ref_filename)
        temp = self.table_level1.to_denormalized_dataframe(flat_column_index=False)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_denormalized_dataframe_table_level1')
        temp = self.table_level2.to_denormalized_dataframe(flat_column_index=False)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_denormalized_dataframe_table_level2')
        temp = self.table_level1.to_denormalized_dataframe(flat_column_index=True)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_denormalized_dataframe_flat_column_index_table_level1')
        temp = self.table_level2.to_denormalized_dataframe(flat_column_index=True)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_denormalized_dataframe_flat_column_index_table_level2')
        temp = self.table_level1.to_hierarchical_dataframe(flat_column_index=False)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_hierarchical_dataframe_table_level1')
        temp = self.table_level2.to_hierarchical_dataframe(flat_column_index=False)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_hierarchical_dataframe_table_level2')
        temp = self.table_level1.to_hierarchical_dataframe(flat_column_index=True)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_hierarchical_dataframe_flat_column_index_table_level1')
        temp = self.table_level2.to_hierarchical_dataframe(flat_column_index=True)
        temp.to_hdf(path_or_buf=ref_filename,
                    key='test_to_hierarchical_dataframe_flat_column_index_table_level2')

    def test_populate_table_hierarchy(self):
        """Test that just checks that populating the tables with data works correctly"""
        self.popolate_tables()
        # Check level0 data
        self.assertListEqual(self.table_level0.id[:], np.arange(10, 14, 1).tolist())
        self.assertListEqual(self.table_level0['tags'][:],
                             [['tag1'], ['tag2'], ['tag2', 'tag1'], ['tag3', 'tag4', 'tag5']])
        self.assertListEqual(self.table_level0['myid'][:].tolist(), np.arange(0, 4, 1).tolist())
        # Check level1 data
        self.assertListEqual(self.table_level1.id[:], np.arange(0, 3, 1).tolist())
        self.assertListEqual(self.table_level1['tag'][:], ['tag1', 'tag2', 'tag2'])
        self.assertTrue(self.table_level1['child_table_refs'].target.table is self.table_level0)
        self.assertEqual(len(self.table_level1['child_table_refs'].target.table), 4)
        # Check level2 data
        self.assertListEqual(self.table_level2.id[:], np.arange(0, 2, 1).tolist())
        self.assertListEqual(self.table_level2['filter'][:], [10, 12])
        self.assertTrue(self.table_level2['child_table_refs'].target.table is self.table_level1)
        self.assertEqual(len(self.table_level2['child_table_refs'].target.table), 3)

    def test_get_hierarchy_column_name(self):
        """Test the get_hiearchy_column_name function"""
        self.popolate_tables()
        self.assertEqual(self.table_level1.get_hierarchy_column_name(), 'child_table_refs')
        self.assertEqual(self.table_level2.get_hierarchy_column_name(), 'child_table_refs')

    def test_get_referencing_column_names(self):
        """test the get_referencing_column_names function"""
        self.popolate_tables()
        self.assertListEqual(self.table_level1.get_referencing_column_names(), ['child_table_refs'])
        self.assertListEqual(self.table_level2.get_referencing_column_names(), ['child_table_refs'])

    def test_get_targets(self):
        """test the get_targets function"""
        self.popolate_tables()
        # test level 1
        temp = self.table_level1.get_targets()
        self.assertEqual(len(temp), 1)
        self.assertTrue(temp[0] is self.table_level0)
        # test level2
        temp = self.table_level2.get_targets()
        self.assertEqual(len(temp), 2)
        self.assertTrue(temp[0] is self.table_level1)
        self.assertTrue(temp[1] is self.table_level0)

    def test_to_denormalized_dataframe(self):
        """
        Test to_denormalized_dataframe(flat_column_index=False)
        for self.table_level1 and self.table_level2
        """
        ref_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'referencedata_test_hierarchical_dynamic_table_mixin.h5')
        if not os.path.exists(ref_filename):
            self.skipTest("Reference data file not found required for test. %s" & ref_filename)
        self.popolate_tables()
        # level 1
        curr = self.table_level1.to_denormalized_dataframe(flat_column_index=False)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_denormalized_dataframe_table_level1')
        pandas.testing.assert_frame_equal(curr, ref)
        # level 2
        curr = self.table_level2.to_denormalized_dataframe(flat_column_index=False)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_denormalized_dataframe_table_level2')
        pandas.testing.assert_frame_equal(curr, ref)

    def test_to_denormalized_dataframe_flat_column_index(self):
        """
        Test to_denormalized_dataframe(flat_column_index=True)
        for self.table_level1 and self.table_level2
        """
        ref_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'referencedata_test_hierarchical_dynamic_table_mixin.h5')
        if not os.path.exists(ref_filename):
            self.skipTest("Reference data file not found required for test. %s" & ref_filename)
        self.popolate_tables()
        # test level 1
        curr = self.table_level1.to_denormalized_dataframe(flat_column_index=True)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_denormalized_dataframe_flat_column_index_table_level1')
        pandas.testing.assert_frame_equal(curr, ref)
        # test level 2
        curr = self.table_level2.to_denormalized_dataframe(flat_column_index=True)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_denormalized_dataframe_flat_column_index_table_level2')
        pandas.testing.assert_frame_equal(curr, ref)

    def test_to_hierarchical_dataframe_empty_table(self):
        """
        Test creating the hierarchical table that is empty
        """
        # Do not populate with data, just straight convert to dataframe
        tab = self.table_level1.to_hierarchical_dataframe()
        self.assertEqual(len(tab), 0)
        self.assertListEqual(tab.columns.to_list(), [('level0', 'id')])
        self.assertListEqual(tab.index.names, [('level1', 'id')])
        tab = self.table_level2.to_hierarchical_dataframe()
        self.assertEqual(len(tab), 0)
        self.assertListEqual(tab.columns.to_list(), [('level0', 'id')])
        self.assertListEqual(tab.index.names, [('level2', 'id'), ('level1', 'id')])
        tab = self.table_level1.to_hierarchical_dataframe(flat_column_index=True)
        self.assertEqual(len(tab), 0)
        self.assertListEqual(tab.columns.to_list(), [('level0', 'id')])
        tab = self.table_level2.to_hierarchical_dataframe(flat_column_index=True)
        self.assertListEqual(tab.columns.to_list(), [('level0', 'id')])
        self.assertListEqual(tab.index.names, [('level2', 'id'), ('level1', 'id')])

    def test_to_hierarchical_dataframe(self):
        """
        Test to_hierarchical_dataframe(flat_column_index=False)
        for self.table_level1 and self.table_level2
        """
        ref_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'referencedata_test_hierarchical_dynamic_table_mixin.h5')
        if not os.path.exists(ref_filename):
            self.skipTest("Reference data file not found required for test. %s" & ref_filename)
        self.popolate_tables()
        # test level 1
        curr = self.table_level1.to_hierarchical_dataframe(flat_column_index=False)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_hierarchical_dataframe_table_level1')
        pandas.testing.assert_frame_equal(curr, ref)
        # test level 2
        curr = self.table_level2.to_hierarchical_dataframe(flat_column_index=False)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_hierarchical_dataframe_table_level2')
        pandas.testing.assert_frame_equal(curr, ref)

    def test_to_hierarchical_dataframe_flat_column_index(self):
        """
        Test to_hierarchical_dataframe(flat_column_index=True)
        for self.table_level1 and self.table_level2
        """
        ref_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    'referencedata_test_hierarchical_dynamic_table_mixin.h5')
        if not os.path.exists(ref_filename):
            self.skipTest("Reference data file not found required for test. %s" & ref_filename)
        self.popolate_tables()
        # test level 1
        curr = self.table_level1.to_hierarchical_dataframe(flat_column_index=True)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_hierarchical_dataframe_flat_column_index_table_level1')
        pandas.testing.assert_frame_equal(curr, ref)
        # test level 2
        curr = self.table_level2.to_hierarchical_dataframe(flat_column_index=True)
        ref = pandas.read_hdf(path_or_buf=ref_filename,
                              key='test_to_hierarchical_dataframe_flat_column_index_table_level2')
        pandas.testing.assert_frame_equal(curr, ref)


if __name__ == '__main__':
    unittest.main()
