from __future__ import annotations

from os import PathLike
import numpy as np
import pandas as pd
from typing import List, Type, Union

import gtamodel_tools.common.spatial_aggregator as sa
from gtamodel_tools.io.common import coerce_matrix, open_file


class Matrix(object):
    """ Class to store and apply operations to matrices.

    Args:
        - ndims: int
            Number of dimensions, must be 1 or 2 
        - matrix: pd.DataFrame or pd.Series
            Matrix data as a pandas dataframe. For 2-D matrices, can either
            be in tall or wide format.

    Notes:
        - One-dimensional matrices are stored internall as a pandas Series,
          where the index corresponds to the zone system.
        - Two-dimensional matrices are stored internally in as a 
          pandas DataFrame in wide format. The index and columns are expected
          to correspond to the zone system.
    
    
    """

    def __init__(
            self, 
            ndims: int, 
            matrix: pd.Series | pd.DataFrame
        ):
        self._origcol = 'p'
        self._destcol = 'q'
        if ndims not in [1, 2]:
            raise ValueError('ndims must be 1 or 2.')
        self._ndims = ndims

        if ndims == 1:
            if isinstance(matrix, pd.Series):
                self._matrix = matrix
            elif isinstance(matrix.pd.DataFrame):
                if matrix.shape[1] != 1:
                    raise ValueError(
                        'Can only read a DataFrame with one column as a '
                        '1-D matrix. ')
                self._matrix = matrix.squeeze()
            self._matrix.name = 'matrix'
            self._matrix.index.name = 'zone'
        else:
            if matrix.shape[1] == 1:
                if matrix.index.nlevels != 2:
                    raise ValueError(
                        'Expecting two-level index when importing 2-D matrix '
                        'in tall format.')
                self._matrix = matrix.unstack()
            else:
                if matrix.index.nlevels != 1 or matrix.columns.nlevels != 1:
                    raise ValueError(
                        'Multi-column DataFrames can only have a single-level '
                        'index and columns.')
            self._matrix = matrix
            self._matrix.index.name = self._origcol
            self._matrix.columns.name = self._destcol


    @property
    def ndims(self) -> int:
        return self._ndims

    @property
    def matrix(self) -> pd.Series | pd.DataFrame:
        return self._matrix


    def to_mdf(self, file: PathLike) -> None:
        """Writes a matrix to Emme's official "binary serialization" format.
        
        Can be loaded in Emme using ``inro.emme.matrix.MatrixData.load()``. 
        There is no official extension for this type of file; '.mdf' 
        is recommended.

        Args:
            file (str | FileIO | Path): 
                The path or file handler to write to.
        """
        matrix = self._matrix
        if isinstance(matrix, pd.Series):
            row_index = matrix.index.get_level_values(0).unique()
            column_index = matrix.index.get_level_values(1).unique()
        elif isinstance(matrix, pd.DataFrame):
            row_index = matrix.index
            column_index = matrix.columns
        else:
            raise TypeError("Only labelled matrix objects are supported")

        with open_file(file, mode='wb') as writer:
            data = coerce_matrix(matrix, allow_raw=False)
            # Header
            np.array([0xC4D4F1B2, 1, 1, 2], dtype=np.uint32).tofile(writer)  
            # Shape
            np.array(data.shape, dtype=np.uint32).tofile(writer)

            np.array(row_index, dtype=np.int32).tofile(writer)
            np.array(column_index, dtype=np.int32).tofile(writer)

            data.tofile(writer)

    def to_emx(self, file: PathLike, emmebank_zones: int) -> None:
        """ Writes an "internal" Emme matrix with an '.emx' extension. The
        number of zones that the Emmebank is dimensioned for must be known in 
        order for the file to be written correctly.

        Args:
            file (str | FileIO | Path): 
                The path or file handler to write to.
            emmebank_zones (int): 
                The number of zones the target Emmebank is dimensioned for.
        """
        if not isinstance(emmebank_zones, int) or emmebank_zones <= 0:
            raise ValueError('emmebank_zones must be a postitive integer')

        with open_file(file, mode='wb') as writer:
            data = coerce_matrix(self._matrix)
            n = data.shape[0]
            if n > emmebank_zones:
                out = data[:emmebank_zones, :emmebank_zones].astype(np.float32)
            else:
                out = np.zeros([emmebank_zones, emmebank_zones], dtype=np.float32)
                out[:n, :n] = data
            out.tofile(writer)


    def apply_spatial_aggregation(
            self,
            origin_aggr: Type[sa.SpatialAggregator] | None | False = None,
            destination_aggr: Type[sa.SpatialAggregator] | None | False = None
        ) -> pd.Series | pd.DataFrame:
        """ Spatially aggregate matrix.

        Args:
            origin_aggr: sa.SpatialAggregator or None
                    Spatial aggregation applied to origin. If None then that 
                    level is output at the TAZ level, if False then then this 
                    will not be included in summary  aggregation. Cannot be 
                    False for a single-level aggregation. Default is None.
                    
            destination_aggr: sa.SpatialAggregator or None
                Spatial aggregation applied to destination. If None then that 
                    level is output at the TAZ level, if False then then this 
                    will not be included in summary  aggregation. 
                    Default is None.

        Returns:
            Aggregated matrix, either as pd.Series for 1-D matrix, or 
                pd.DataFrame for 2-D matrix.

        """
        # Validate aggregations before trying to merge
        if self._ndims == 1 and not isinstance(
                origin_aggr, sa.SpatialAggregator):
            raise ValueError(
                'origin_aggr must be defined to aggregate a 1-D matrix.')
        if self._ndims == 2:
            if not (
                    isinstance(origin_aggr, sa.SpatialAggregator) or 
                    isinstance(origin_aggr, sa.SpatialAggregator)):
                raise ValueError(
                    'Either origin_aggr or destination_aggr must be specified '
                    'to aggregate a 2-D matrix.')

        if self._ndims == 1:
            matrix = self._matrix.reset_index()
            return sa.summarize_table_with_spatial_aggregation(
                values=matrix,
                geom_id=self._matrix.name,
                spatial_aggregations=origin_aggr
            )
        else:
            matrix = self._matrix.stack()
            matrix.name = 'matrix'
            matrix = matrix.reset_index()
            return sa.summarize_table_with_spatial_aggregation(
                df=matrix,
                values='matrix',
                geom_id=[self._origcol, self._destcol],
                spatial_aggregations=[origin_aggr, destination_aggr]
            ).unstack()
