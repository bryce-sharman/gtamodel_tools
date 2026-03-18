from __future__ import annotations

from os import PathLike
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Hashable, Iterable

import gtamodel_tools.common.spatial_aggregator as sa

idx = pd.IndexSlice
class Matrix(object):
    """ Class to store and apply operations to matrices.

    Matrices in this package are two-dimensional, storing information 
    between an origin (denoted as p) and a destination, (denoted as q).

    Args:
        - matrix: pd.Series
            Matrix data in tall format.
        - name: str
            Matrix name:

    Notes:
        Matrices are stored internally as a pandas.Series in tall 
        format.
    
    
    """
    ORIG_COL = 'p'
    DEST_COL = 'q'
    def __init__(self, matrix: pd.Series) -> None:
        self._matrix = matrix

#region Properties
    @property
    def name(self) -> Hashable | None:
        return self._matrix.name
    
    @property
    def tall(self) -> pd.Series:
        """ Matrix in tall format. """
        return self._matrix
    
    @property
    def wide(self) -> pd.DataFrame:
        m = self._matrix.unstack()
        m.columns = m.columns.droplevel(0)
        return m
    
#region Operators
    def add(self, m: Matrix | float) -> Matrix:
        if isinstance(m, Matrix):
            return Matrix(self._matrix.add(m._matrix))
        else:
            # Use pandas addition directly
            return Matrix(self._matrix.add(m))
        
    def subtract(self, m: Matrix) -> Matrix:
        if isinstance(m, Matrix):
            return Matrix(self._matrix.subtract(m._matrix))
        else:
            # Use pandas subtraction directly
            return Matrix(self._matrix.subtract(m))
        
    
    def multiply(self, m: Matrix) -> Matrix:
        if isinstance(m, Matrix):
            return Matrix(self._matrix.multiply(m._matrix))
        else:
            # Use pandas multiplication directly
            return Matrix(self._matrix.multiply(m))
        
    def divide(self, m: Matrix) -> Matrix:
        if isinstance(m, Matrix):
            return Matrix(self._matrix.divide(m._matrix))
        else:
            # Use pandas division directly
            return Matrix(self._matrix.divide(m))

    def __add__(self, m: Matrix) -> Matrix:
        return self.add(m)
    
    def __sub__(self, m: Matrix) -> Matrix:
        return self.subtract(m)
    
    def __mul__(self, m: Matrix) -> Matrix:
        return self.multiply(m) 

    def __truediv__(self, m: Matrix) -> Matrix: 
        return self.divide(m)

#endregion

#region Read from File
    @classmethod
    def from_emme_mdf(
            cls, filepath: PathLike, name: Hashable='matrix') -> Matrix:
        """
        Reads two-dimensional matrix from Emme's official matrix "binary 
        serialization" format.
        
        This format is created using ``inro.emme.matrix.MatrixData.save()``.
        There is no official extension for this type of file; '.mdf' is recommended. 
        '.emxd' is also sometimes encountered.

        Args:
            file: PathLike
                The file to read.
            name: str
                Name to apply to the matrix. Default is 'matrix'

        Returns:
            gtamodel_tools.matrix.matrix.Matrix
        """
        with open(filepath, 'rb') as f:
            magic, version, dtype_index, ndim = np.fromfile(
                f, np.uint32, count=4)
            if (magic != 0xC4D4F1B2 or version != 1 or  
                    not (0 < dtype_index <= 4) or not (0 < ndim <= 2)):
                raise IOError("Unexpected file header: magic number: %X, "
                            "version: %d, data type: %d, dimensions: %d."
                            % (magic, version, dtype_index, ndim))
            shape = np.fromfile(f, np.uint32, count=ndim)
            index_list = []
            for n_items in shape:
                indices = np.fromfile(f, np.int32, n_items)
                index_list.append(indices)
            if len(index_list) != 2:
                raise RuntimeError("Expected two-dimensional matrix.")
            dtype = {1: np.float32, 2: np.float64, 3: np.int32, 4: np.uint32}[
                dtype_index]
            flat_length = shape.prod()  # Multiply the shape tuple
            matrix = np.fromfile(f, dtype, count=flat_length)
        matrix.shape = shape
        index = pd.Index(index_list[0], name=cls.ORIG_COL)
        columns = pd.Index(index_list[1], name=cls.DEST_COL)
        df = pd.DataFrame(matrix, index=index, columns=columns)
        s = df.stack()
        s = pd.Series(index=s.index, data=s.to_numpy(), name = name)
        return cls(s)

    @classmethod
    def from_emme_emx(cls, file: PathLike, 
             *, 
             zones: int | Iterable[int] | pd.Index | None = None,
             tall: bool = False
        ) -> np.ndarray | pd.DataFrame | pd.Series:
        """Reads an "internal" Emme matrix.
        
        These files are found in `<Emme Project>/Database/emmemat` with an '.emx' 
        extension. This data format does not contain information about zones. 
        Its size is determined by the dimensions of the Emmebank 
        (``Emmebank.dimensions['centroids']``), 
        regardless of the number of zones actually used in all scenarios.

        Args:
            file: PathLike 
                The file to read.
            zones (int | Iterable[int] | pandas.Index, optional): 
                An Index or Iterable will be interpreted as the zone labels for the 
                matrix rows and columns; returning a DataFrame or Series (depending
                on ``tall``). If an integer is provided, the returned ndarray will 
                be truncated to this 'number of zones'. Otherwise, the returned 
                ndarray will be size to the maximum number of zone dimensioned by 
                the Emmebank. Defaults to ``None``. 
            tall (bool, optional): If True, a 1D data structure will be returned. 
                If ``zone_index`` is provided, a Series will be returned, otherwise 
                a 1D ndarray. Defaults to ``False``. 

        Returns:
            numpy.ndarray, pandas.DataFrame, or pandas.Series.

        Examples:
            For a project with 20 zones:

            >>> matrix = read_emx("Database/emmemat/mf1.emx")
            >>> print type(matrix), matrix.shape
            (numpy.ndarray, (20, 20))

            >>> matrix = read_emx("Database/emmemat/mf1.emx", zones=10)
            >>> print type(matrix), matrix.shape
            (numpy.ndarray, (10, 10))

            >>> matrix = read_emx("Database/emmemat/mf1.emx", zones=range(10))
            >>> print type(matrix), matrix.shape
            <class 'pandas.core.frame.DataFrame'> (10, 10)

            >>> matrix = read_emx("Database/emmemat/mf1.emx", zones=range(10), tall=True)
            >>> print type(matrix), matrix.shape
            <class 'pandas.core.series.Series'> 100

        """
        raise NotImplementedError("Read from Emme .emx not yet implemented.")
        # with open(file, mode='rb') as reader:
        #     data = np.fromfile(reader, dtype=np.float32)

        #     n = int(len(data) ** 0.5)
        #     assert len(data) == n ** 2

        #     if zones is None and tall:
        #         return data

        #     data.shape = n, n

        #     if isinstance(zones, (int, np.int_)):
        #         data = data[:zones, :zones]

        #         if tall:
        #             data.shape = zones * zones
        #             return data
        #         return data
        #     elif zones is None:
        #         return data

        #     zones = pd.Index(zones)
        #     n = len(zones)
        #     data = data[:n, :n]

        #     matrix = pd.DataFrame(data, index=zones, columns=zones)

        #     return matrix.stack() if tall else matrix


    @classmethod
    def from_csv(cls, filepath: PathLike, name: str='matrix') -> Matrix:
        raise NotImplementedError("Read from CSV not yet implemented.")

    @classmethod
    def from_omx(cls, filepath: PathLike, name: str='matrix'):
        raise NotImplementedError("Read from OMX not yet implemented.")
#endregion

#region Write to file
    def to_csv(self, filepath: PathLike, format: str='tall') -> None:
        raise NotImplementedError('Matrix write to CSV not yet implemented.')

    def to_omx(self, filepath: PathLike) -> None:
        raise NotImplementedError('Matrix write to OMX not yet implemented.')

    def to_mdf(self, filepath: PathLike) -> None:
        """Writes a matrix to Emme's official "binary serialization" format.
        
        Can be loaded in Emme using ``inro.emme.matrix.MatrixData.load()``. 
        There is no official extension for this type of file; '.mdf' 
        is recommended.

        Args:
            file:  PathLike 
                The path or file handler to write to.
        """
        print("Matrix.to_mdf() is not yet tested, use with caution.")
        m = self._matrix
        row_index = m.index.get_level_values(0).unique()
        column_index = m.index.get_level_values(1).unique()
        with open(filepath, mode='wb') as writer:
            # Header
            np.array([0xC4D4F1B2, 1, 1, 2], dtype=np.uint32).tofile(writer)  
            # Shape
            np.array(m.shape, dtype=np.uint32).tofile(writer)
            np.array(row_index, dtype=np.int32).tofile(writer)
            np.array(column_index, dtype=np.int32).tofile(writer)
            m.astype(np.float32).to_numpy().tofile(writer)

    def to_emx(self, filepath: PathLike, emmebank_zones: int) -> None:
        """ Writes an "internal" Emme matrix with an '.emx' extension. The
        number of zones that the Emmebank is dimensioned for must be known in 
        order for the file to be written correctly.

        Args:
            file: PathLike 
                The path or file handler to write to.
            emmebank_zones: int
                The number of zones the target Emmebank is dimensioned for.
        """
        print("Matrix.to_to_emx() is not yet tested, use with caution.")
        if not isinstance(emmebank_zones, int) or emmebank_zones <= 0:
            raise ValueError('emmebank_zones must be a postitive integer')

        with open(filepath, mode='wb') as writer:
            data = self._matrix.to_numpy()
            n = data.shape[0]
            if n > emmebank_zones:
                out = data[:emmebank_zones, :emmebank_zones].astype(np.float32)
            else:
                out = np.zeros([emmebank_zones, emmebank_zones], dtype=np.float32)
                out[:n, :n] = data
            out.tofile(writer)
#endregion



#region Spatial aggregation

    # def apply_spatial_aggregation(
    #         self,
    #         origin_aggr: Type[sa.SpatialAggregator] | None | False = None,
    #         destination_aggr: Type[sa.SpatialAggregator] | None | False = None
    #     ) -> pd.Series | pd.DataFrame:
    #     """ Spatially aggregate matrix.

    #     Args:
    #         origin_aggr: sa.SpatialAggregator or None
    #                 Spatial aggregation applied to origin. If None then that 
    #                 level is output at the TAZ level, if False then then this 
    #                 will not be included in summary  aggregation. Cannot be 
    #                 False for a single-level aggregation. Default is None.
                    
    #         destination_aggr: sa.SpatialAggregator or None
    #             Spatial aggregation applied to destination. If None then that 
    #                 level is output at the TAZ level, if False then then this 
    #                 will not be included in summary  aggregation. 
    #                 Default is None.

    #     Returns:
    #         Aggregated matrix, either as pd.Series for 1-D matrix, or 
    #             pd.DataFrame for 2-D matrix.

    #     """
    #     # Validate aggregations before trying to merge
    #     if self._ndims == 1 and not isinstance(
    #             origin_aggr, sa.SpatialAggregator):
    #         raise ValueError(
    #             'origin_aggr must be defined to aggregate a 1-D matrix.')
    #     if self._ndims == 2:
    #         if not (
    #                 isinstance(origin_aggr, sa.SpatialAggregator) or 
    #                 isinstance(origin_aggr, sa.SpatialAggregator)):
    #             raise ValueError(
    #                 'Either origin_aggr or destination_aggr must be specified '
    #                 'to aggregate a 2-D matrix.')

    #     if self._ndims == 1:
    #         matrix = self._matrix.reset_index()
    #         return sa.summarize_table_with_spatial_aggregation(
    #             values=matrix,
    #             geom_id=self._matrix.name,
    #             spatial_aggregations=origin_aggr
    #         )
    #     else:
    #         matrix = self._matrix.stack()
    #         matrix.name = 'matrix'
    #         matrix = matrix.reset_index()
    #         return sa.summarize_table_with_spatial_aggregation(
    #             df=matrix,
    #             values='matrix',
    #             geom_id=[self._origcol, self._destcol],
    #             spatial_aggregations=[origin_aggr, destination_aggr]
    #         ).unstack()
#endregion