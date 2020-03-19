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
# TODO Test to_dataframe
# TODO Test __getitem__


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

    def test_init_categories_without_category_tables_error(self):
        # Test raise error if categories is given without category_tables
        with self.assertRaises(ValueError) as ve:
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                categories=['cat1', 'cat2'])
        self.assertEqual(str(ve.exception), "Categories provided but no category_tables given")

    def test_init_length_mismatch_between_categories_and_category_tables(self):
        # Test length mismatch between categories and category_tables
        with self.assertRaises(ValueError) as ve:
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                categories=['cat1', 'cat2'],
                category_tables=[])
        self.assertEqual(str(ve.exception), "0 category_tables given but 2 categories specified")

    def test_init_category_table_names_do_not_match_categories(self):
        # Construct some categories for testing
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        # Test add category_table that is not listed in the categories list
        with self.assertRaises(ValueError) as ve:
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                categories=['test1', 'test2', 't3'],  # bad name for 'test3'
                category_tables=categories)
        self.assertEqual(str(ve.exception), "DynamicTable test3 does not appear in categories ['test1', 'test2', 't3']")

    def test_init_duplicate_category_table_name(self):
        # Test duplicate table name
        with self.assertRaises(ValueError) as ve:
            categories = [DynamicTable(name=val,
                                       description=val+" description",
                                       columns=[VectorData(name=val+t,
                                                           description=val+t+' description',
                                                           data=np.arange(10)) for t in ['c1', 'c2', 'c3']]
                                       ) for val in ['test1', 'test1', 'test3']]
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                categories=['test1', 'test2', 'test3'],
                category_tables=categories)
        self.assertEqual(str(ve.exception), "Duplicate table name test1 found in input dynamic_tables")

    def test_init_misaligned_category_tables(self):
        # Test misaligned category tables
        with self.assertRaises(ValueError) as ve:
            categories = [DynamicTable(name=val,
                                       description=val+" description",
                                       columns=[VectorData(name=val+t,
                                                           description=val+t+' description',
                                                           data=np.arange(10)) for t in ['c1', 'c2', 'c3']]
                                       ) for val in ['test1', 'test2']]
            categories.append(DynamicTable(name='test3',
                                           description="test3 description",
                                           columns=[VectorData(name='test3 '+t,
                                                               description='test3 '+t+' description',
                                                               data=np.arange(8)) for t in ['c1', 'c2', 'c3']]))
            AlignedDynamicTable(
                name='test_aligned_table',
                description='Test aligned container',
                categories=['test1', 'test2', 'test3'],
                category_tables=categories)
        self.assertEqual(str(ve.exception), "Category DynamicTable test3 does not align, it has 8 rows expected 10")

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
        temp = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)
        self.assertEqual(temp.categories, category_names)

    def test_init_with_custom_nonempty_categories_and_main(self):
        """
        Test that we can create a non-empty table with custom non-empty categories
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
            category_tables=categories,
            columns=[VectorData(name='main_' + t,
                                description='main_'+t+'_description',
                                data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']])

        self.assertEqual(temp.categories, category_names)
        self.assertTrue('test1' in temp)  # test that contains category works
        self.assertTrue(('test1', 'c1') in temp)  # test that contains a column works
        with self.assertRaises(ValueError):  # test the error case of a tuple with len !-2
            ('test1', 'c1', 't3') in temp
        self.assertTupleEqual(temp.colnames, ('main_c1', 'main_c2', 'main_c3'))

    def test_init_with_custom_misaligned_categories(self):
        """Test that we cannot create an empty table with custom categories"""
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

    def test_add_category(self):
        """Test that we can correct a non-empty category to an existing table"""
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories[0:2])
        self.assertListEqual(adt.categories, category_names[0:2])
        adt.add_category(categories[-1])
        self.assertListEqual(adt.categories, category_names)

    def test_add_category_misaligned_rows(self):
        """Test that we can correct a non-empty category to an existing table"""
        category_names = ['test1', 'test2']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)
        self.assertListEqual(adt.categories, category_names)
        with self.assertRaises(ValueError) as ve:
            adt.add_category(DynamicTable(name='test3',
                                          description='test3_description',
                                          columns=[VectorData(name='test3_'+t,
                                                              description='test3 '+t+' description',
                                                              data=np.arange(num_rows - 2)) for t in ['c1', 'c2', 'c3']
                                                   ]))
        self.assertEqual(str(ve.exception), "New category DynamicTable does not align, it has 8 rows expected 10")

    def test_add_category_already_in_table(self):
        category_names = ['test1', 'test2', 'test2']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories[0:2])
        self.assertListEqual(adt.categories, category_names[0:2])
        with self.assertRaises(ValueError) as ve:
            adt.add_category(categories[-1])
        self.assertEqual(str(ve.exception), "Category test2 already in the table")

    def test_add_column(self):
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            columns=[VectorData(name='test_'+t,
                                description='test_'+t+' description',
                                data=np.arange(10)) for t in ['c1', 'c2', 'c3']])
        # Test successful add
        adt.add_column(name='testA', description='testA', data=np.arange(10))
        self.assertTupleEqual(adt.colnames,  ('test_c1', 'test_c2', 'test_c3', 'testA'))

    def test_add_column_bad_category(self):
        """Test add column with bad category"""
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            columns=[VectorData(name='test_'+t,
                                description='test_'+t+' description',
                                data=np.arange(10)) for t in ['c1', 'c2', 'c3']])
        with self.assertRaises(KeyError) as ke:
            adt.add_column(category='mycat', name='testA', description='testA', data=np.arange(10))
        self.assertEqual(str(ke.exception), "'Category mycat not in table'")

    def test_add_column_bad_length(self):
        """Test add column that is too short"""
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            columns=[VectorData(name='test_'+t,
                                description='test_'+t+' description',
                                data=np.arange(10)) for t in ['c1', 'c2', 'c3']])
        # Test successful add
        with self.assertRaises(ValueError) as ve:
            adt.add_column(name='testA', description='testA', data=np.arange(8))
        self.assertEqual(str(ve.exception), "column must have the same number of rows as 'id'")

    def test_add_column_to_subcategory(self):
        """Test adding a column to a subcategory"""
        category_names = ['test1', 'test2', 'test3']
        num_rows = 10
        categories = [DynamicTable(name=val,
                                   description=val+" description",
                                   columns=[VectorData(name=val+t,
                                                       description=val+t+' description',
                                                       data=np.arange(num_rows)) for t in ['c1', 'c2', 'c3']]
                                   ) for val in category_names]
        adt = AlignedDynamicTable(
            name='test_aligned_table',
            description='Test aligned container',
            category_tables=categories)
        self.assertListEqual(adt.categories, category_names)
        # Test successful add
        adt.add_column(category='test2', name='testA', description='testA', data=np.arange(10))
        self.assertTupleEqual(adt.get_category('test2').colnames, ('test2c1', 'test2c2', 'test2c3', 'testA'))


if __name__ == '__main__':
    unittest.main()
