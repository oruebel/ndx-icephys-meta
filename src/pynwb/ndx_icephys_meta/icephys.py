from pynwb import register_class
from pynwb.file import NWBFile
from pynwb.icephys import IntracellularElectrode, PatchClampSeries
from pynwb.base import TimeSeries
import numpy as np
try:
    from pynwb.core import DynamicTable, DynamicTableRegion, VectorIndex
except ImportError:
    from hdmf.common import DynamicTable, DynamicTableRegion, VectorIndex
from hdmf.utils import docval, popargs, getargs, call_docval_func, get_docval, fmt_docval_args
import warnings
import pandas as pd
from collections import OrderedDict
from copy import copy

namespace = 'ndx-icephys-meta'


class HierarchicalDynamicTableMixin(object):
    """
    Mixin class for defining specialized functionality for hierarchical dynamic tables.


    Assumptions:

    1) The current implementation assumes that there is only one DynamicTableRegion column
    that needs to be expanded as part of the hierarchy.  Allowing multiple hierarchical
    columns in a single table get tricky, because it is unclear how those rows should
    be joined. To clarify, allowing multiple DynamicTableRegion should be fine, as long
    as only one of them should be expanded as part of the hierarchy.

    2) The default implementation of the get_hierarchy_column_name function assumes that
    the first DynamicTableRegion that references a DynamicTable that inherits from
    HierarchicalDynamicTableMixin is the one that should be expanded as part of the
    hierarchy of tables. If there is no such column, then the default implementation
    assumes that the first DynamicTableRegion column is the one that needs to be expanded.
    These assumption of get_hierarchy_column_name can be easily fixed by overwriting
    the function in the subclass to return the name of the approbritate column.
    """

    def get_hierarchy_column_name(self):
        """
        Get the name of column that references another DynamicTable that
        is itself a HierarchicalDynamicTableMixin table.

        :returns: String with the column name or None
        """
        first_col = None
        for col_index, col in enumerate(self.columns):
            if isinstance(col, DynamicTableRegion):
                first_col = col.name
                if isinstance(col.table, HierarchicalDynamicTableMixin):
                    return col.name
        return first_col

    def get_referencing_column_names(self):
        """
        Determine the names of all columns that reference another table, i.e.,
        find all DynamicTableRegion type columns

        Returns: List of strings with the column names
        """
        col_names = []
        for col_index, col in enumerate(self.columns):
            if isinstance(col, DynamicTableRegion):
                col_names.append(col.name)
        return col_names

    def get_targets(self, include_self=False):
        """
        Get a list of the full table hierarchy, i.e., recursively list all
        tables referenced in the hierarchy.

        Returns: List of DynamicTable objects

        """
        hcol_name = self.get_hierarchy_column_name()
        hcol = self[hcol_name]
        hcol_target = hcol.table if isinstance(hcol, DynamicTableRegion) else hcol.target.table
        if isinstance(hcol_target, HierarchicalDynamicTableMixin):
            re = [self, ] if include_self else []
            re += [hcol_target, ]
            re += hcol_target.get_targets()
            return re
        else:
            return [hcol_target, ]

    def to_denormalized_dataframe(self, flat_column_index=False):
        """
        Shorthand for 'self.to_hierarchical_dataframe().reset_index()'

        The function denormalizes the hierarchical table and represents all data as
        columns in the resulting dataframe.
        """
        hier_df = self.to_hierarchical_dataframe(flat_column_index=True)
        flat_df = hier_df.reset_index()
        if not flat_column_index:
            # cn[0] is the level, cn[1:] is the label. If cn has only 2 elements than use cn[1] instead to
            # avoid creating column labels that are tuples with just one element
            mi_tuples = [(cn[0], cn[1:] if len(cn) > 2 else cn[1])
                         for cn in flat_df.columns]
            flat_df.columns = pd.MultiIndex.from_tuples(mi_tuples, names=('source_table', 'label'))

        return flat_df

    def to_hierarchical_dataframe(self, flat_column_index=False):
        """
        Create a Pandas dataframe with a hierarchical MultiIndex index that represents the
        hierarchical dynamic table.
        """
        # Get the references column
        hcol_name = self.get_hierarchy_column_name()
        hcol = self[hcol_name]
        hcol_target = hcol.table if isinstance(hcol, DynamicTableRegion) else hcol.target.table

        # Create the data variables we need to collect the data for our output dataframe and associated index
        index = []
        data = []
        columns = None
        index_names = None

        # If we have indexed columns (other than our hierarchical column) then our index data for our
        # MultiIndex will contain lists as elements (which are not hashable) and as such create an error.
        # As such we need to check if we have any affected columns so we can  fix our data
        indexed_column_indicies = np.where([isinstance(self[colname], VectorIndex)
                                            for colname in self.colnames if colname != hcol_name])[0]
        indexed_column_indicies += 1  # Need to increment by 1 since we add the row id in our iteration below

        # Case 1:  Our DynamicTableRegion column points to a regular DynamicTable
        #          If this is the case than we need to de-normalize the data and flatten the hierarchy
        if not isinstance(hcol_target, HierarchicalDynamicTableMixin):
            # 1) Iterate over all rows in our hierarchical columns (i.e,. the DynamicTableRegion column)
            for row_index, row_df in enumerate(hcol[:]):  # need hcol[:] here in case this is an h5py.Dataset
                # 1.1): Since hcol is a DynamicTableRegion, each row returns another DynamicTable so we
                #       next need to iterate over all rows in that table to denormalize our data
                for row in row_df.itertuples(index=True):
                    # 1.1.1) Determine the column data for our row. Each selected row from our target table
                    #        becomes a row in our flattened table
                    data.append(row)
                    # 1.1.2) Determine the multi-index tuple for our row, consisting of: i) id of the row in this
                    #        table, ii) all columns (except the hierarchical column we are flattening), and
                    #        iii) the index (i.e., id) from our target row
                    index_data = ([self.id[row_index], ] +
                                  [self[row_index, colname] for colname in self.colnames if colname != hcol_name])
                    for i in indexed_column_indicies:  # Fix data from indexed columns
                        index_data[i] = tuple(index_data[i])  # Convert from list to tuple (which is hashable)
                    index.append(tuple(index_data))
                    # Determine the names for our index and columns of our output table if this is the first row.
                    # These are constant for all rows so we only need to do this onle once for the first row.
                    if row_index == 0:
                        index_names = ([(self.name, 'id')] +
                                       [(self.name, colname)
                                        for colname in self.colnames if colname != hcol_name])
                        if flat_column_index:
                            columns = [(hcol_target.name, 'id'), ] + list(row_df.columns)
                        else:
                            columns = pd.MultiIndex.from_tuples([(hcol_target.name, 'id'), ] +
                                                                [(hcol_target.name, c) for c in row_df.columns],
                                                                names=('source_table', 'label'))
            #  if we had an empty data table then at least define the columns
            if index_names is None:
                index_names = ([(self.name, 'id')] +
                               [(self.name, colname)
                                for colname in self.colnames if colname != hcol_name])
                if flat_column_index:
                    columns = [(hcol_target.name, 'id'), ] + list(row_df.columns)
                else:
                    columns = pd.MultiIndex.from_tuples([(hcol_target.name, 'id'), ] +
                                                        [(hcol_target.name, c) for c in hcol_target.colnames],
                                                        names=('source_table', 'label'))

        # Case 2:  Our DynamicTableRegion columns points to another HierarchicalDynamicTable.
        else:
            # 1) First we need to recursively flatten the hierarchy by calling 'to_hierarchical_dataframe()'
            #    (i.e., this function) on the target of our hierarchical column
            hcol_hdf = hcol_target.to_hierarchical_dataframe(flat_column_index=flat_column_index)
            # 2) Iterate over all rows in our hierarchcial columns (i.e,. the DynamicTableRegion column)
            for row_index, row_df_level1 in enumerate(hcol[:]):   # need hcol[:] here  in case this is an h5py.Dataset
                # 1.1): Since hcol is a DynamicTableRegion, each row returns another DynamicTable so we
                #       next need to iterate over all rows in that table to denormalize our data
                for row_df_level2 in row_df_level1.itertuples(index=True):
                    # 1.1.2) Since our target is itself a HierarchicalDynamicTable each target row itself
                    #        may expand into multiple rows in flattened hcol_hdf. So we now need to look
                    #        up the rows in hcol_hdf that correspond to the rows in row_df_level2.
                    #        NOTE: In this look-up we assume that the ids (and hence the index) of
                    #              each row in the table are in fact unique.
                    for row_tuple_level3 in hcol_hdf.loc[[row_df_level2[0]]].itertuples(index=True):
                        # 1.1.2.1) Determine the column data for our row.
                        data.append(row_tuple_level3[1:])
                        # 1.1.2.2) Determine the multi-index tuple for our row,
                        index_data = ([self.id[row_index], ] +
                                      [self[row_index, colname] for colname in self.colnames if colname != hcol_name] +
                                      list(row_tuple_level3[0]))
                        for i in indexed_column_indicies:  # Fix data from indexed columns
                            index_data[i] = tuple(index_data[i])  # Convert from list to tuple (which is hashable)
                        index.append(tuple(index_data))
                        # Determine the names for our index and columns of our output table if this is the first row
                        if row_index == 0:
                            index_names = ([(self.name, "id")] +
                                           [(self.name, colname)
                                            for colname in self.colnames if colname != hcol_name] +
                                           hcol_hdf.index.names)
                            columns = hcol_hdf.columns
            # if we had an empty table, then at least define the columns
            if index_names is None:
                index_names = ([(self.name, "id")] +
                               [(self.name, colname)
                                for colname in self.colnames if colname != hcol_name] +
                               hcol_hdf.index.names)
                columns = hcol_hdf.columns

        # Construct the pandas dataframe with the hierarchical multi-index
        multi_index = pd.MultiIndex.from_tuples(index, names=index_names)
        out_df = pd.DataFrame(data=data, index=multi_index, columns=columns)
        return out_df


@register_class('AlignedDynamicTable', namespace)
class AlignedDynamicTable(DynamicTable):
    """
    DynamicTable container that subports storing a collection of subtables. Each sub-table is a
    DynamicTable itself that is aligned with the main table by row index. I.e., all
    DynamicTables stored in this group MUST have the same number of rows. This type effectively
    defines a 2-level table in which the main data is stored in the main table implementd by this type
    and additional columns of the table are grouped into categories, with each category being'
    represented by a separate DynamicTable stored within the group.
    """
    __fields__ = (
        {'name': 'category_tables', 'child': True},
        'description')

    @docval(*get_docval(DynamicTable.__init__),
            {'name': 'category_tables', 'type': list,
             'doc': 'List of DynamicTables to be added to the container', 'default': None},
            {'name': 'categories', 'type': 'array_data',
             'doc': 'List of names with the ordering of category tables', 'default': None})
    def __init__(self, **kwargs):
        in_category_tables = popargs('category_tables', kwargs)
        in_categories = popargs('categories', kwargs)
        if in_categories is None and in_category_tables is not None:
            in_categories = [tab.name for tab in in_category_tables]
        if in_categories is not None and in_category_tables is None:
            raise ValueError("Categories provided but no category_tables given")
        # at this point both in_categories and in_category_tables should either both be None or both be a list
        if in_categories is not None:
            if len(in_categories) != len(in_category_tables):
                raise ValueError("%s category_tables given but %s categories specified" %
                                 (len(in_category_tables), len(in_categories)))
        # Initialize the main dynamic table
        call_docval_func(super().__init__, kwargs)
        # Create and set all sub-categories
        dts = OrderedDict()
        # Add the custom categories given as inputs
        if in_category_tables is not None:
            # We may need to resize our main table when adding categories as the user may not have set ids
            if len(in_category_tables) > 0:
                # We have categories to process
                if len(self.id) == 0:
                    # The user did not initialize our main table id's nor set columns for our main table
                    for i in range(len(in_category_tables[0])):
                        self.id.append(i)
            # Add the user-provided categories in the correct order as described by the categories
            # This is necessary, because we do not store the categories explicitly but we maintain them
            # as the order of our self.category_tables. In this makes sure look-ups are consistent.
            lookup_index = OrderedDict([(k, -1) for k in in_categories])
            for i, v in enumerate(in_category_tables):
                # Error check that the name of the table is in our categories list
                if v.name not in lookup_index:
                    raise ValueError("DynamicTable %s does not appear in categories %s" % (v.name, str(in_categories)))
                # Error check to make sure no two tables with the same name are given
                if lookup_index[v.name] >= 0:
                    raise ValueError("Duplicate table name %s found in input dynamic_tables" % v.name)
                lookup_index[v.name] = i
            for table_name, tabel_index in lookup_index.items():
                # This error case should not be able to occur since the length of the in_categories and
                # in_category_tables must match and we made sure that each DynamicTable we added had its
                # name in the in_categories list. We, therefore, exclude this check from coverage testing
                # but we leave it in just as a backup trigger in case something unexpected happens
                if tabel_index < 0:  # pragma: no cover
                    raise ValueError("DynamicTable %s listed in categories but does not appear in category_tables" %
                                     table_name)  # pragma: no cover
                # Test that all category tables have the correct number of rows
                category = in_category_tables[tabel_index]
                if len(category) != len(self):
                    raise ValueError('Category DynamicTable %s does not align, it has %i rows expected %i' %
                                     (category.name, len(category), len(self)))
                # Add the category table to our category_tables.
                dts[category.name] = category
        # Set the self.category_tables attribute, which will set the parent/child relationships for the category_tables
        self.category_tables = dts

    @docval({'name': 'val', 'type': (str, tuple), 'doc': 'The name of the category or column to check.'})
    def __contains__(self, val):
        """
        Check if the give value (i.e., column) exists in this table

        If the val is a string then check if the given category exists. If val is a tuple
        of two strings (category, colname) then check for the given category if the given
        colname exists.
        """
        if isinstance(val, str):
            return val in self.category_tables
        elif isinstance(val, tuple):
            if len(val) != 2:
                raise ValueError("Expected tuple of strings of length 2 got tuple of length %i" % len(val))
            return val[1] in self.get_category(val[0])

    @property
    def categories(self):
        """
        Get the list of names the categories

        Short-hand for list(self.category_tables.keys())

        :raises: KeyError if the given name is not in self.category_tables
        """
        return list(self.category_tables.keys())

    @docval({'name': 'category', 'type': DynamicTable, 'doc': 'Add a new DynamicTable category'},)
    def add_category(self, **kwargs):
        """
        Add a new DynamicTable to the AlignedDynamicTable to create a new category in the table.

        NOTE: The table must align with (i.e, have the same number of rows as) the main data table (and
        other category tables). I.e., if the AlignedDynamicTable is already populated with data
        then we have to populate the new category with the corresponding data before adding it.

        :raises: ValueError is raised if the input table does not have the same number of rows as the main table
        """
        category = getargs('category', kwargs)
        if len(category) != len(self):
            raise ValueError('New category DynamicTable does not align, it has %i rows expected %i' %
                             (len(category), len(self)))
        if category.name in self.category_tables:
            raise ValueError("Category %s already in the table" % category.name)
        self.category_tables[category.name] = category
        category.parent = self

    @docval({'name': 'name', 'type': str, 'doc': 'Name of the category we want to retrieve'})
    def get_category(self, **kwargs):
        return self.category_tables[popargs('name', kwargs)]

    @docval(*get_docval(DynamicTable.add_column),
            {'name': 'category', 'type': str, 'doc': 'The category the column should be added to',
             'default': None})
    def add_column(self, **kwargs):
        """
        Add a column to the table

        :raises: KeyError if the category does not exist

        """
        category_name = popargs('category', kwargs)
        if category_name is None:
            # Add the column to our main table
            call_docval_func(super().add_column, kwargs)
        else:
            # Add the column to a sub-category table
            try:
                category = self.get_category(category_name)
            except KeyError:
                raise KeyError("Category %s not in table" % category_name)
            category.add_column(**kwargs)

    @docval({'name': 'data', 'type': dict, 'doc': 'the data to put in this row', 'default': None},
            {'name': 'id', 'type': int, 'doc': 'the ID for the row', 'default': None},
            {'name': 'enforce_unique_id', 'type': bool, 'doc': 'enforce that the id in the table must be unique',
             'default': False},
            allow_extra=True)
    def add_row(self, **kwargs):
        """
        We can either provide the row data as a single dict or by specifying a dict for each category
        """
        data, row_id, enforce_unique_id = popargs('data', 'id', 'enforce_unique_id', kwargs)
        data = data if data is not None else kwargs

        # extract the category data
        category_data = {k: data.pop(k) for k in self.categories if k in data}

        # Check that we have the approbriate categories provided
        missing_categories = set(self.categories) - set(list(category_data.keys()))
        if missing_categories:
            raise ValueError(
                '\n'.join([
                    'row data keys don\'t match available categories',
                    'missing {} category keys: {}'.format(len(missing_categories), missing_categories)
                ])
            )
        # Add the data to our main dynamic table
        data['id'] = row_id
        data['enforce_unique_id'] = enforce_unique_id
        call_docval_func(super().add_row, data)

        # Add the data to all out dynamic table categories
        for category, values in category_data.items():
            self.category_tables[category].add_row(**values)

    @docval({'name': 'ignore_category_ids', 'type': bool,
             'doc': "Ignore id columns of sub-category tables", 'default': False},
            {'name': 'electrode_refs_as_objectids', 'type': bool,
             'doc': 'replace object references in the electrode column with object_ids',
             'default': False},
            {'name': 'stimulus_refs_as_objectids', 'type': bool,
             'doc': 'replace object references in the stimulus column with object_ids',
             'default': False},
            {'name': 'response_refs_as_objectids', 'type': bool,
             'doc': 'replace object references in the response column with object_ids',
             'default': False}
            )
    def to_dataframe(self, **kwargs):
        """Convert the collection of tables to a single pandas DataFrame"""
        dfs = [super().to_dataframe().reset_index(), ]

        if getargs('ignore_category_ids', kwargs):
            dfs += [category.to_dataframe() for category in self.category_tables.values()]
        else:
            dfs += [category.to_dataframe().reset_index() for category in self.category_tables.values()]
        names = [self.name, ] + list(self.category_tables.keys())
        res = pd.concat(dfs, axis=1, keys=names)
        if getargs('electrode_refs_as_objectids', kwargs):
            res[('electrodes', 'electrode')] = [e.object_id for e in res[('electrodes', 'electrode')]]
        if getargs('stimulus_refs_as_objectids', kwargs):
            res[('stimuli', 'stimulus')] = [(e[0], e[1],  e[2].object_id) for e in res[('stimuli', 'stimulus')]]
        if getargs('response_refs_as_objectids', kwargs):
            res[('responses', 'response')] = [(e[0], e[1],  e[2].object_id) for e in res[('responses', 'response')]]
        res.set_index((self.name, 'id'), drop=True, inplace=True)
        return res

    def __getitem__(self, item):
        """
        If item is:
        * int : Return a single row of the table
        * string : Return a single category of the table
        * tuple: Get a column, row, or cell from a particular category

        :returns: DataFrame when retrieving a row or category. Returns scalar when selecting a cell.
                 Returns a VectorData/VectorIndex when retrieving a single column.
        """
        if isinstance(item, (int, list, np.ndarray, slice)):
            # get a single full row from all tables
            dfs = ([super().__getitem__(item).reset_index(), ] +
                   [category[item].reset_index() for category in self.category_tables.values()])
            names = [self.name, ] + list(self.category_tables.keys())
            res = pd.concat(dfs, axis=1, keys=names)
            res.set_index((self.name, 'id'), drop=True, inplace=True)
            return res
        elif isinstance(item, str):
            # get a single category
            return self.get_category(item).to_dataframe()
        elif isinstance(item, tuple):
            # get a column, row, or cell from a particular category
            return self.get_category(item[0])[item[1:]]


@register_class('IntracellularElectrodesTable', namespace)
class IntracellularElectrodesTable(DynamicTable):
    """
    Table for storing intracellular electrode related metadata'
    """
    __columns__ = (
        {'name': 'electrode',
         'description': 'Column for storing the reference to the intracellular electrode',
         'required': True,
         'index': False,
         'table': False},
    )

    @docval(*get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        # Define defaultb name and description settings
        kwargs['name'] = 'electrodes'
        kwargs['description'] = ('Table for storing intracellular electrode related metadata')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)


@register_class('IntracellularStimuliTable', namespace)
class IntracellularStimuliTable(DynamicTable):
    """
    Table for storing intracellular electrode related metadata'
    """
    __columns__ = (
        {'name': 'stimulus',
         'description': 'Column storing the reference to the recorded stimulus for the recording (rows)',
         'required': True,
         'index': False,
         'table': False},
    )

    @docval(*get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        # Define defaultb name and description settings
        kwargs['name'] = 'stimuli'
        kwargs['description'] = ('Table for storing intracellular stimulus related metadata')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)


@register_class('IntracellularResponsesTable', namespace)
class IntracellularResponsesTable(DynamicTable):
    """
    Table for storing intracellular electrode related metadata'
    """
    __columns__ = (
        {'name': 'response',
         'description': 'Column storing the reference to the recorded response for the recording (rows)',
         'required': True,
         'index': False,
         'table': False},
    )

    @docval(*get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        # Define defaultb name and description settings
        kwargs['name'] = 'responses'
        kwargs['description'] = ('Table for storing intracellular response related metadata')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)


@register_class('IntracellularRecordingsTable', namespace)
class IntracellularRecordingsTable(AlignedDynamicTable):
    """
    A table to group together a stimulus and response from a single electrode and
    a single simultaneous_recording. Each row in the table represents a single recording consisting
    typically of a stimulus and a corresponding response.
    """
    @docval(*get_docval(AlignedDynamicTable.__init__, 'id', 'columns', 'colnames', 'category_tables', 'categories'))
    def __init__(self, **kwargs):
        kwargs['name'] = 'intracellular_recordings'
        kwargs['description'] = ('A table to group together a stimulus and response from a single electrode '
                                 'and a single simultaneous recording and for storing metadata about the '
                                 'intracellular recording.')
        in_category_tables = getargs('category_tables', kwargs)
        if in_category_tables is None or len(in_category_tables) == 0:
            kwargs['category_tables'] = [IntracellularElectrodesTable(),
                                         IntracellularStimuliTable(),
                                         IntracellularResponsesTable()]
            kwargs['categories'] = None
        else:
            # Check if our required data tables are supplied, otherwise add them to the list
            required_dynamic_table_given = [-1 for i in range(3)]  # The first three are our required tables
            for i, tab in enumerate(in_category_tables):
                if isinstance(tab, IntracellularElectrodesTable):
                    required_dynamic_table_given[0] = i
                elif isinstance(tab, IntracellularStimuliTable):
                    required_dynamic_table_given[1] = i
                elif isinstance(tab, IntracellularResponsesTable):
                    required_dynamic_table_given[2] = i
            # Check if the supplied tables contain data but not all required tables have been supplied
            required_dynamic_table_missing = np.any(np.array(required_dynamic_table_given[0:3]) < 0)
            if len(in_category_tables[0]) != 0 and required_dynamic_table_missing:
                raise ValueError("IntracellularElectrodeTable, IntracellularStimuliTable, and "
                                 "IntracellularResponsesTable are required when adding custom, non-empty "
                                 "tables to IntracellularRecordingsTable as the missing data for the required "
                                 "tables cannot be determined automatically")
            # Compile the complete list of tables
            dynamic_table_arg = copy(in_category_tables)
            categories_arg = [] if getargs('categories', kwargs) is None else copy(getargs('categories', kwargs))
            if required_dynamic_table_missing:
                if required_dynamic_table_given[2] < 0:
                    dynamic_table_arg.append(IntracellularResponsesTable)
                    if not dynamic_table_arg[-1].name in categories_arg:
                        categories_arg.insert(0, dynamic_table_arg[-1].name)
                if required_dynamic_table_given[1] < 0:
                    dynamic_table_arg.append(IntracellularStimuliTable())
                    if not dynamic_table_arg[-1].name in categories_arg:
                        categories_arg.insert(0, dynamic_table_arg[-1].name)
                if required_dynamic_table_given[0] < 0:
                    dynamic_table_arg.append(IntracellularElectrodesTable())
                    if not dynamic_table_arg[-1].name in categories_arg:
                        categories_arg.insert(0, dynamic_table_arg[-1].name)
            kwargs['category_tables'] = dynamic_table_arg
            kwargs['categories'] = categories_arg

        call_docval_func(super().__init__, kwargs)

    @docval({'name': 'electrode', 'type': IntracellularElectrode, 'doc': 'The intracellular electrode used'},
            {'name': 'stimulus_start_index', 'type': 'int', 'doc': 'Start index of the stimulus', 'default': -1},
            {'name': 'stimulus_index_count', 'type': 'int', 'doc': 'Stop index of the stimulus', 'default': -1},
            {'name': 'stimulus', 'type': TimeSeries,
             'doc': 'The TimeSeries (usually a PatchClampSeries) with the stimulus',
             'default': None},
            {'name': 'response_start_index', 'type': 'int', 'doc': 'Start index of the response', 'default': -1},
            {'name': 'response_index_count', 'type': 'int', 'doc': 'Stop index of the response', 'default': -1},
            {'name': 'response', 'type': TimeSeries,
             'doc': 'The TimeSeries (usually a PatchClampSeries) with the response',
             'default': None},
            {'name': 'electrode_metadata', 'type': dict,
             'doc': 'Additional electrode metadata to be stored in the electrodes table', 'default': None},
            {'name': 'stimulus_metadata', 'type': dict,
             'doc': 'Additional stimulus metadata to be stored in the stimuli table', 'default': None},
            {'name': 'response_metadata', 'type': dict,
             'doc': 'Additional resposnse metadata to be stored in the responses table', 'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_recording(self, **kwargs):
        """
        Add a single recording to the IntracellularRecordingsTable table.

        Typically, both stimulus and response are expected. However, in some cases only a stimulus
        or a resposne may be recodred as part of a recording. In this case, None, may be given
        for either stimulus or response, but not both. Internally, this results in both stimulus
        and response pointing to the same timeseries, while the start_index and index_count for
        the invalid series will both be set to -1.
        """
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
        # Confirm that we have at least a valid stimulus or response
        if stimulus is None and response is None:
            raise ValueError("stimulus and response cannot both be None.")

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

        # If either stimulus or response are None, then set them to the same TimeSeries to keep the I/O happy
        response = response if response is not None else stimulus
        stimulus = stimulus if stimulus is not None else response

        # Make sure the types are compatible
        if ((response.neurodata_type.startswith("CurrentClamp") and
                stimulus.neurodata_type.startswith("VoltageClamp")) or
                (response.neurodata_type.startswith("VoltageClamp") and
                 stimulus.neurodata_type.startswith("CurrentClamp"))):
            raise ValueError("Incompatible types given for 'stimulus' and 'response' parameters. "
                             "'stimulus' is of type %s and 'response' is of type %s." %
                             (stimulus.neurodata_type, response.neurodata_type))
        if response.neurodata_type == 'IZeroClampSeries':
            if stimulus is not None:
                raise ValueError("stimulus should usually be None for IZeroClampSeries response")
        if isinstance(response, PatchClampSeries) and isinstance(stimulus, PatchClampSeries):
            # # We could also check sweep_number, but since it is mostly relevant to the deprecated SweepTable
            # # we don't really need to enforce it here
            # if response.sweep_number != stimulus.sweep_number:
            #     warnings.warn("sweep_number are usually expected to be the same for PatchClampSeries type "
            #                   "stimulus and response pairs in an intracellular recording.")
            if response.electrode != stimulus.electrode:
                raise ValueError("electrodes are usually expected to be the same for PatchClampSeries type "
                                 "stimulus and response pairs in an intracellular recording.")

        # Compile the electrodes table data
        electrodes = popargs('electrode_metadata', kwargs)
        if electrodes is None:
            electrodes = {}
        electrodes['electrode'] = electrode

        # Compile the stimuli table data
        stimuli = popargs('stimulus_metadata', kwargs)
        if stimuli is None:
            stimuli = {}
        stimuli['stimulus'] = (stimulus_start_index, stimulus_index_count, stimulus)

        # Compile the reponses table data
        responses = popargs('response_metadata', kwargs)
        if responses is None:
            responses = {}
        responses['response'] = (response_start_index, response_index_count, response)

        _ = super().add_row(enforce_unique_id=True,
                            electrodes=electrodes,
                            responses=responses,
                            stimuli=stimuli,
                            **kwargs)
        return len(self) - 1


@register_class('SimultaneousRecordingsTable', namespace)
class SimultaneousRecordingsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recordings from the
    IntracellularRecordingsTable table together that were recorded simultaneously
    from different electrodes.
    """

    __columns__ = (
        {'name': 'recordings',
         'description': 'Column with a references to one or more rows in the IntracellularRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'intracellular_recordings_table',
             'type': IntracellularRecordingsTable,
             'doc': 'the IntracellularRecordingsTable table that the recordings column indexes. May be None when '
                    'reading the Container from file as the table attribute is already populated in this case '
                    'but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        intracellular_recordings_table = popargs('intracellular_recordings_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'simultaneous_recordings'
        kwargs['description'] = ('A table for grouping different intracellular recordings from the'
                                 'IntracellularRecordingsTable table together that were recorded simultaneously '
                                 'from different electrodes.')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)
        if self['recordings'].target.table is None:
            if intracellular_recordings_table is not None:
                self['recordings'].target.table = intracellular_recordings_table
            else:
                raise ValueError("intracellular_recordings constructor argument required")

    @docval({'name': 'recordings',
             'type': 'array_data',
             'doc': 'the indices of the recordings belonging to this simultaneous recording'},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_simultaneous_recording(self, **kwargs):
        """
        Add a single Sweep consisting of one-or-more recordings and associated custom
        SimultaneousRecordingsTable metadata to the table.
        """
        _ = super().add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('SequentialRecordingsTable', namespace)
class SequentialRecordingsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording simultaneous_recordings from the
    SimultaneousRecordingsTable table together. This is typically used to group together simultaneous_recordings
    where the a sequence of stimuli of the same type with varying parameters
    have been presented in a sequence.
    """

    __columns__ = (
        {'name': 'simultaneous_recordings',
         'description': 'Column with a references to one or more rows in the SimultaneousRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
        {'name': 'stimulus_type',
         'description': 'Column storing the type of stimulus used for the sequential recording',
         'required': True,
         'index': False,
         'table': False}
    )

    @docval({'name': 'simultaneous_recordings_table',
             'type': SimultaneousRecordingsTable,
             'doc': 'the SimultaneousRecordingsTable table that the simultaneous_recordings '
                    'column indexes. May be None when reading the Container from file as the '
                    'table attribute is already populated in this case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        simultaneous_recordings_table = popargs('simultaneous_recordings_table', kwargs)
        # Define defaultb name and description settings
        kwargs['name'] = 'sequential_recordings'
        kwargs['description'] = ('A table for grouping different intracellular recording simultaneous_recordings '
                                 'from the SimultaneousRecordingsTable table together. This is typically used to '
                                 'group together simultaneous_recordings where the a sequence of stimuli of the '
                                 'same type with varying parameters have been presented in a sequence.')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)
        if self['simultaneous_recordings'].target.table is None:
            if simultaneous_recordings_table is not None:
                self['simultaneous_recordings'].target.table = simultaneous_recordings_table
            else:
                raise ValueError('simultaneous_recordings_table constructor argument required')

    @docval({'name': 'stimulus_type',
             'type': str,
             'doc': 'the type of stimulus used for the sequential recording'},
            {'name': 'simultaneous_recordings',
             'type': 'array_data',
             'doc': 'the indices of the simultaneous_recordings belonging to this sequential recording'},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_sequential_recording(self, **kwargs):
        """
        Add a sequential recording (i.e., one row)  consisting of one-or-more recording simultaneous_recordings
        and associated custom sequential recording  metadata to the table.
        """
        _ = super().add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('RepetitionsTable', namespace)
class RepetitionsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording sequential recordings together.
    With each SweepSequence typically representing a particular type of stimulus, the
    RepetitionsTable table is typically used to group sets of stimuli applied in sequence.
    """

    __columns__ = (
        {'name': 'sequential_recordings',
         'description': 'Column with a references to one or more rows in the SequentialRecordingsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'sequential_recordings_table',
             'type': SequentialRecordingsTable,
             'doc': 'the SequentialRecordingsTable table that the sequential_recordings column indexes. May '
                    'be None when reading the Container from file as the table attribute is already populated '
                    'in this case but otherwise this is required.',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        sequential_recordings_table = popargs('sequential_recordings_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'repetitions'
        kwargs['description'] = ('A table for grouping different intracellular recording sequential recordings '
                                 'together. With each SimultaneousRecording typically representing a particular type '
                                 'of stimulus, the RepetitionsTable table is typically used to group sets '
                                 'of stimuli applied in sequence.')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)
        if self['sequential_recordings'].target.table is None:
            if sequential_recordings_table is not None:
                self['sequential_recordings'].target.table = sequential_recordings_table
            else:
                raise ValueError('sequential_recordings_table constructor argument required')

    @docval({'name': 'sequential_recordings',
             'type': 'array_data',
             'doc': 'the indices of the sequential recordings belonging to this repetition',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_repetition(self, **kwargs):
        """
        Add a repetition (i.e., one row)  consisting of one-or-more recording sequential recordings
        and associated custom repetition  metadata to the table.
        """
        _ = super().add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('ExperimentalConditionsTable', namespace)
class ExperimentalConditionsTable(DynamicTable, HierarchicalDynamicTableMixin):
    """
    A table for grouping different intracellular recording repetitions together that
    belong to the same experimental conditions.
    """

    __columns__ = (
        {'name': 'repetitions',
         'description': 'Column with a references to one or more rows in the RepetitionsTable table',
         'required': True,
         'index': True,
         'table': True},
    )

    @docval({'name': 'repetitions_table',
             'type': RepetitionsTable,
             'doc': 'the RepetitionsTable table that the repetitions column indexes',
             'default': None},
            *get_docval(DynamicTable.__init__, 'id', 'columns', 'colnames'))
    def __init__(self, **kwargs):
        repetitions_table = popargs('repetitions_table', kwargs)
        # Define default name and description settings
        kwargs['name'] = 'experimental_conditions'
        kwargs['description'] = ('A table for grouping different intracellular recording repetitions together that '
                                 'belong to the same experimental experimental_conditions.')
        # Initialize the DynamicTable
        call_docval_func(super().__init__, kwargs)
        if self['repetitions'].target.table is None:
            if repetitions_table is not None:
                self['repetitions'].target.table = repetitions_table
            else:
                raise ValueError('repetitions_table constructor argument required')

    @docval({'name': 'repetitions',
             'type': 'array_data',
             'doc': 'the indices of the repetitions  belonging to this condition',
             'default': None},
            returns='Integer index of the row that was added to this table',
            rtype=int,
            allow_extra=True)
    def add_experimental_condition(self, **kwargs):
        """
        Add a condition (i.e., one row)  consisting of one-or-more recording repetitions of sequential recordings
        and associated custom experimental_conditions  metadata to the table.
        """
        _ = super().add_row(enforce_unique_id=True, **kwargs)
        return len(self.id) - 1


@register_class('ICEphysFile', namespace)
class ICEphysFile(NWBFile):
    """
    Extension of the NWBFile class to allow placing the new icephys
    metadata types in /general/intracellular_ephys in the NWBFile
    NOTE: If this proposal for extension to NWB gets merged with
    the core schema, then this type would be removed and the
    NWBFile specification updated instead
    """

    __nwbfields__ = ({'name': 'intracellular_recordings',
                      'child': True,
                      'required_name': 'intracellular_recordings',
                      'doc': 'IntracellularRecordingsTable table to group together a stimulus and response '
                             'from a single intracellular electrode and a single simultaneous recording.'},
                     {'name': 'icephys_simultaneous_recordings',
                      'child': True,
                      'required_name': 'simultaneous_recordings',
                      'doc': 'SimultaneousRecordingsTable table for grouping different intracellular recordings from'
                             'the IntracellularRecordingsTable table together that were recorded simultaneously '
                             'from different electrodes'},
                     {'name': 'icephys_sequential_recordings',
                      'child': True,
                      'required_name': 'sequential_recordings',
                      'doc': 'A table for grouping different simultaneous intracellular recording from the '
                             'SimultaneousRecordingsTable table together. This is typically used to group '
                             'together simultaneous recordings where the a sequence of stimuli of the same '
                             'type with varying parameters have been presented in a sequence.'},
                     {'name': 'icephys_repetitions',
                      'child': True,
                      'required_name': 'repetitions',
                      'doc': 'A table for grouping different intracellular recording sequential recordings together.'
                             'With each SweepSequence typically representing a particular type of stimulus, the '
                             'RepetitionsTable table is typically used to group sets of stimuli applied in sequence.'},
                     {'name': 'icephys_experimental_conditions',
                      'child': True,
                      'required_name': 'experimental_conditions',
                      'doc': 'A table for grouping different intracellular recording repetitions together that '
                             'belong to the same experimental experimental_conditions.'},
                     )

    @docval(*get_docval(NWBFile.__init__),
            {'name': 'intracellular_recordings', 'type': IntracellularRecordingsTable, 'default': None,
             'doc': 'the IntracellularRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_simultaneous_recordings', 'type': SimultaneousRecordingsTable, 'default': None,
             'doc': 'the SimultaneousRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_sequential_recordings', 'type': SequentialRecordingsTable, 'default': None,
             'doc': 'the SequentialRecordingsTable table that belongs to this NWBFile'},
            {'name': 'icephys_repetitions', 'type': RepetitionsTable, 'default': None,
             'doc': 'the RepetitionsTable table that belongs to this NWBFile'},
            {'name': 'icephys_experimental_conditions', 'type': ExperimentalConditionsTable, 'default': None,
             'doc': 'the ExperimentalConditionsTable table that belongs to this NWBFile'},
            {'name': 'ic_filtering', 'type': str, 'default': None,
             'doc': '[DEPRECATED] Use IntracellularElectrode.filtering instead. Description of filtering used.'})
    def __init__(self, **kwargs):
        # Get the arguments to pass to NWBFile and remove arguments custum to this class
        intracellular_recordings = kwargs.pop('intracellular_recordings', None)
        icephys_simultaneous_recordings = kwargs.pop('icephys_simultaneous_recordings', None)
        icephys_sequential_recordings = kwargs.pop('icephys_sequential_recordings', None)
        icephys_repetitions = kwargs.pop('icephys_repetitions', None)
        icephys_experimental_conditions = kwargs.pop('icephys_experimental_conditions', None)
        if kwargs.get('sweep_table') is not None:
            warnings.warn("Use of SweepTable is deprecated. Use the intracellular_recordings, "
                          "simultaneous_recordings, sequential_recordings, repetitions and/or "
                          "experimental_conditions table(s) instead.", DeprecationWarning)
        # Initialize the NWBFile parent class
        pargs, pkwargs = fmt_docval_args(super().__init__, kwargs)
        super().__init__(*pargs, **pkwargs)
        # Set ic filtering if requested
        self.ic_filtering = kwargs.get('ic_filtering')
        # Set the intracellular_recordings if available
        setattr(self, 'intracellular_recordings', intracellular_recordings)
        setattr(self, 'icephys_simultaneous_recordings', icephys_simultaneous_recordings)
        setattr(self, 'icephys_sequential_recordings', icephys_sequential_recordings)
        setattr(self, 'icephys_repetitions', icephys_repetitions)
        setattr(self, 'icephys_experimental_conditions', icephys_experimental_conditions)

    @property
    def ic_filtering(self):
        return self.fields.get('ic_filtering')

    @ic_filtering.setter
    def ic_filtering(self, val):
        if val is not None:
            warnings.warn("Use of ic_filtering is deprecated. Use the IntracellularElectrode.filtering"
                          "field instead", DeprecationWarning)
            self.fields['ic_filtering'] = val

    @docval(*get_docval(NWBFile.add_stimulus),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_stimulus(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        timeseries = popargs('timeseries', kwargs)
        self._add_stimulus_internal(timeseries)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys_repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(timeseries)

    @docval(*get_docval(NWBFile.add_stimulus),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_stimulus_template(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        timeseries = popargs('timeseries', kwargs)
        self._add_stimulus_template_internal(timeseries)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys_repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(timeseries)

    @docval(*get_docval(NWBFile.add_acquisition),
            {'name': 'use_sweep_table', 'type': bool, 'default': False, 'doc': 'Use the deprecated SweepTable'})
    def add_acquisition(self, **kwargs):
        """
        Overwrite behavior from NWBFile to avoid use of the deprecated SweepTable
        """
        nwbdata = popargs('nwbdata', kwargs)
        self._add_acquisition_internal(nwbdata)
        use_sweep_table = popargs('use_sweep_table', kwargs)
        if use_sweep_table:
            if self.sweep_table is None:
                warnings.warn("Use of SweepTable is deprecated. Use the IntracellularRecordingsTable, "
                              "SimultaneousRecordingsTable tables instead. See the add_intracellular_recordings, "
                              "add_icephsy_simultaneous_recording, add_icephys_sequential_recording, "
                              "add_icephys_repetition, add_icephys_condition functions.",
                              DeprecationWarning)
            self._update_sweep_table(nwbdata)

    @docval(returns='The NWBFile.intracellular_recordings table', rtype=IntracellularRecordingsTable)
    def get_intracellular_recordings(self):
        """
        Get the NWBFile.intracellular_recordings table.

        In contrast to NWBFile.intracellular_recordings, this function will create the
        IntracellularRecordingsTable table if not yet done, whereas NWBFile.intracellular_recordings
        will return None if the table is currently not being used.
        """
        if self.intracellular_recordings is None:
            self.intracellular_recordings = IntracellularRecordingsTable()
        return self.intracellular_recordings

    @docval(*get_docval(IntracellularRecordingsTable.add_recording),
            returns='Integer index of the row that was added to IntracellularRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_intracellular_recording(self, **kwargs):
        """
        Add a intracellular recording to the intracellular_recordings table. If the
        electrode, stimulus, and/or response do not exsist yet in the NWBFile, then
        they will be added to this NWBFile before adding them to the table.
        """
        # Add the stimulus, response, and electrode to the file if they don't exist yet
        stimulus, response, electrode = getargs('stimulus', 'response', 'electrode', kwargs)
        if (stimulus is not None and
                (stimulus.name not in self.stimulus and
                 stimulus.name not in self.stimulus_template)):
            self.add_stimulus(stimulus, use_sweep_table=False)
        if response is not None and response.name not in self.acquisition:
            self.add_acquisition(response, use_sweep_table=False)
        if electrode is not None and electrode.name not in self.icephys_electrodes:
            self.add_icephys_electrode(electrode)
        # make sure the intracellular recordings table exists and if not create it using get_intracellular_recordings
        # Add the recoding to the intracellular_recordings table
        return call_docval_func(self.get_intracellular_recordings().add_recording, kwargs)

    @docval(returns='The NWBFile.icephys_simultaneous_recordings table', rtype=SimultaneousRecordingsTable)
    def get_icephys_simultaneous_recordings(self):
        """
        Get the NWBFile.icephys_simultaneous_recordings table.

        In contrast to NWBFile.icephys_simultaneous_recordings, this function will create the
        SimultaneousRecordingsTable table if not yet done, whereas NWBFile.icephys_simultaneous_recordings
        will return None if the table is currently not being used.
        """
        if self.icephys_simultaneous_recordings is None:
            self.icephys_simultaneous_recordings = SimultaneousRecordingsTable(self.get_intracellular_recordings())
        return self.icephys_simultaneous_recordings

    @docval(*get_docval(SimultaneousRecordingsTable.add_simultaneous_recording),
            returns='Integer index of the row that was added to SimultaneousRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_simultaneous_recording(self, **kwargs):
        """
        Add a new simultaneous recording to the icephys_simultaneous_recordings table
        """
        return call_docval_func(self.get_icephys_simultaneous_recordings().add_simultaneous_recording, kwargs)

    @docval(returns='The NWBFile.icephys_sequential_recordings table', rtype=SequentialRecordingsTable)
    def get_icephys_sequential_recordings(self):
        """
        Get the NWBFile.icephys_sequential_recordings table.

        In contrast to NWBFile.icephys_sequential_recordings, this function will create the
        IntracellularRecordingsTable table if not yet done, whereas NWBFile.icephys_sequential_recordings
        will return None if the table is currently not being used.
        """
        if self.icephys_sequential_recordings is None:
            self.icephys_sequential_recordings = SequentialRecordingsTable(self.get_icephys_simultaneous_recordings())
        return self.icephys_sequential_recordings

    @docval(*get_docval(SequentialRecordingsTable.add_sequential_recording),
            returns='Integer index of the row that was added to SequentialRecordingsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_sequential_recording(self, **kwargs):
        """
        Add a new sequential recording to the icephys_sequential_recordings table
        """
        self.get_icephys_sequential_recordings()
        return call_docval_func(self.icephys_sequential_recordings.add_sequential_recording, kwargs)

    @docval(returns='The NWBFile.icephys_repetitions table', rtype=RepetitionsTable)
    def get_icephys_repetitions(self):
        """
        Get the NWBFile.icephys_repetitions table.

        In contrast to NWBFile.icephys_repetitions, this function will create the
        RepetitionsTable table if not yet done, whereas NWBFile.icephys_repetitions
        will return None if the table is currently not being used.
        """
        if self.icephys_repetitions is None:
            self.icephys_repetitions = RepetitionsTable(self.get_icephys_sequential_recordings())
        return self.icephys_repetitions

    @docval(*get_docval(RepetitionsTable.add_repetition),
            returns='Integer index of the row that was added to RepetitionsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_repetition(self, **kwargs):
        """
        Add a new repetition to the RepetitionsTable table
        """
        return call_docval_func(self.get_icephys_repetitions().add_repetition, kwargs)

    @docval(returns='The NWBFile.icephys_experimental_conditions table', rtype=ExperimentalConditionsTable)
    def get_icephys_experimental_conditions(self):
        """
        Get the NWBFile.icephys_experimental_conditions table.

        In contrast to NWBFile.icephys_experimental_conditions, this function will create the
        RepetitionsTable table if not yet done, whereas NWBFile.icephys_experimental_conditions
        will return None if the table is currently not being used.
        """
        if self.icephys_experimental_conditions is None:
            self.icephys_experimental_conditions = ExperimentalConditionsTable(self.get_icephys_repetitions())
        return self.icephys_experimental_conditions

    @docval(*get_docval(ExperimentalConditionsTable.add_experimental_condition),
            returns='Integer index of the row that was added to ExperimentalConditionsTable',
            rtype=int,
            allow_extra=True)
    def add_icephys_experimental_condition(self, **kwargs):
        """
        Add a new condition to the ExperimentalConditionsTable table
        """
        return call_docval_func(self.get_icephys_experimental_conditions().add_experimental_condition, kwargs)

    def get_icephys_meta_parent_table(self):
        """
        Get the top-most table in the intracellular ephys metadata table hierarchy that exists in this NWBFile.

        The intracellular ephys metadata consists of a hierarchy of DynamicTables, i.e.,
        experimental_conditions --> repetitions --> sequential_recordings -->
        simultaneous_recordings --> intracellular_recordings etc.
        In a given NWBFile not all tables may exist. This convenience functions returns the top-most
        table that exists in this file. E.g., if the file contains only the simultaneous_recordings
        and intracellular_recordings tables then the function would return the simultaneous_recordings table.
        Similarly, if the file contains all tables then it will return the experimental_conditions table.

        :returns: DynamicTable object or None
        """
        if self.icephys_experimental_conditions is not None:
            return self.icephys_experimental_conditions
        elif self.icephys_repetitions is not None:
            return self.icephys_repetitions
        elif self.icephys_sequential_recordings is not None:
            return self.icephys_sequential_recordings
        elif self.icephys_simultaneous_recordings is not None:
            return self.icephys_simultaneous_recordings
        elif self.intracellular_recordings is not None:
            return self.intracellular_recordings
        else:
            return None
