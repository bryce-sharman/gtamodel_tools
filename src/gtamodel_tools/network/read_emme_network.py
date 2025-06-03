""" 
Module to read Emme network from network packages, and offer low-level
analysis tools called from other tools in this package.

Network packages are a development of the TravelModellingGroup at the 
University of Toronto that extends Emme's text output to include 
assignment results.

The code in this module is based on a design and code graciously provided by 
WSP Canada. 
 
"""
from pathlib import Path
import geopandas as gpd
import numpy as np
from os import PathLike
import pandas as pd
from pandas.api.types import is_string_dtype
import re
from shapely import LineString, Point
from typing import Callable, Hashable, List, Tuple, Union
import zipfile

# from gtamodel_tools.network.network import Network


idx = pd.IndexSlice

EMME_ENG_UNITS = {

    'p': 1E-12,
    'n': 1E-9,
    'u': 1E-6,
    'm': 0.001,
    'k': 1000.0,
    'M': 1E6,
    'G': 1E9,
    'T': 1E12
}

'''
def read_emme_network_from_nwp(
        nwp_fp: str | PathLike,
        coding_standard: str,
        *,
        node_attributes: str | List[str] | None = None,
        link_attributes: str |  List[str] | None = None,
        tline_attributes: str | List[str] | None = None
    ) -> Network:
    """ Read Emme network from TMG's nwp file format.
    
    
        nwp_fp: str | PathLike
            Path to network package (.nwp) containing network and
            (optionally) results.
        coding_standard: str
            Currently must be one of ['ncs11', 'ncs16', 'ncs22']
        node_attributes: str | List[str] | None = None
            Node extra attributes to import. If None will import all node 
            extra attributes. To skip node extra attribute imports, set to [].
            Default is None
        link_attributes: str |  List[str] | None = None
            Link extra attributes to import. If None will import all link 
            extra attributes. To skip link extra attribute imports, set to []
            Default is None
        tline_attributes: str | List[str] | None = None
            Transit line extra attributes to import. If None will import all 
            transit line extra attributes. To skip node transit line attribute 
            imports, set to []. Default is None

    
    """
   
    # Define columns as per coding standard
    if coding_standard == 'ncs11':
        import gtamodel_tools.enums.network.toronto_ncs11 as en_ntcs
    elif coding_standard == 'ncs16':
        import gtamodel_tools.enums.network.toronto_ncs16 as en_ntcs
    elif coding_standard == 'ncs22':
        import gtamodel_tools.enums.network.toronto_ncs22 as en_ntcs
    else:
        raise ValueError("Invalid Emme coding standard.")
    crs = en_ntcs.CRS

    nwp_fp = Path(nwp_fp)
    if not nwp_fp.is_file():
        raise FileExistsError(f'File does not exsit: {nwp_fp}')

    # Read nodes and links, extra attributes and results (if available)
    print('    Reading in base network -- nodes and links')
    nodes, links = read_nwp_base_network(nwp_fp, crs)
    # Merge in node and link results, if desired
    print('    Merging node and link attributes.')
    nodes = _merge_attributes(
        nodes, nwp_fp, read_nwp_node_attributes, node_attributes)
    links = _merge_attributes(
        links, nwp_fp, read_nwp_link_attributes, link_attributes)
    links = links.rename(LINKCOLS_RENAME, axis=1)

    try:
        results = read_nwp_traffic_results(nwp_fp)
        links = links.merge(
            results, how='left', left_index=True, right_index=True)
        has_traffic_results = True
    except KeyError:
        has_traffic_results = False

    # Read in transit network, extra attributes and results (if available)
    print('Reading in transit network.')
    tvehicles = read_nwp_transit_vehicles(nwp_fp)
    tlines, tsegments = read_nwp_transit_network(nwp_fp)
    print('    Merging in transit attributes.')
    try:

        tlines = _merge_attributes(
            tlines, nwp_fp, read_nwp_transit_line_attributes, 
            tline_attributes
        )
    except KeyError:
        print('     Could not merge in transit line attributes.')
    tlines = tlines.rename(TLINECOLS_RENAME, axis=1)

    tsegments = tsegments.rename(TSEGCOLS_RENAME, axis=1)
    try:
        results = read_nwp_transit_segment_results(
            nwp_fp, tsegments)
        tsegments = tsegments.merge(
            results[['boardings', 'alightings', 'volume']], 
            how='left', 
            left_index=True, 
            right_index=True
        )
        has_transit_results = True
    except KeyError:
        has_transit_results = False
    print('    Completed reading Emme Network.')
    return Network(
        nodes, links, tvehicles, tlines, tsegments, coding_standard, 
        has_traffic_results, has_transit_results
    )

'''

def parse_tmg_ncs_line_id(s: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """
    A function to parse line IDs based on TMG Network Coding Standard 
    conventions. Returns pandas Series objects corresponding to the parsed 
    operator and route IDs
    """
    operator = s.str[:2].str.replace(r'\d+', '', regex=True)

    # Isolate for route number, if applicable
    route = s.str.replace(r'\D', '', regex=True).str.lstrip('0') 
    # If no route number, assume route id based on TMG NCS convention
    for idx, _ in route[route == ''].items():  
        route.loc[idx] = s.loc[idx][len(operator.loc[idx]):-1]
    return operator, route


def process_emme_eng_notation_series(
        s: pd.Series, *, to_dtype=float) -> pd.Series:  
    """
    A function to convert Pandas Series containing values in Emme's 
    engineering notation.
    """
    values = s.str.replace(r'\D+', '.', regex=True).astype(to_dtype)
    units = s.str.replace(
        r'[\d,.]+', '', regex=True).map(EMME_ENG_UNITS).fillna(1.0)
    return values * units


def read_nwp_base_network(
        nwp_fp: PathLike,
        crs: str
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    A function to read the base network from a Network Package file 
    (exported from Emme using the TMG Toolbox) into DataFrames.

    Args:
        nwp_fp: File path to the network package.
        crs: Projection in which Emme network is encoded.

    Returns:
        A tuple of geopandas GeoDataFrames:
            - Nodes, as a Point GeoDataFrame
            - Links as a LineString GeoDataFrame

    """
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    # Identify node and link regions in the file.
    header_nodes, header_links, last_line = None, None, None
    with zipfile.ZipFile(nwp_fp) as zf:
        for i, line in enumerate(zf.open('base.211'), start=1):
            line = line.strip().decode('utf-8')
            if line.startswith('c'):
                continue  # Skip comment lines
            if line.startswith('t nodes'):
                header_nodes = i
            elif line.startswith('t links'):
                header_links = i
        last_line = i

        # Read nodes
        n_rows = header_links - header_nodes - 2
        data_types = {
            'c': str, 'Node': np.int64, 'X-coord': float, 'Y-coord': float, 
            'Data1': float, 'Data2': float, 'Data3': float, 'Label': str
        }
        nodes = pd.read_csv(
            zf.open('base.211'), index_col='Node', dtype=data_types, 
            skiprows=header_nodes, nrows=n_rows, sep=r'\s+')
        nodes.columns = nodes.columns.str.lower()
        nodes.columns = nodes.columns.str.strip()
        nodes.index.name = 'node'
        nodes.rename(columns={'x-coord': 'x', 'y-coord': 'y'}, inplace=True)
        nodes['is_centroid'] = nodes['c'] == 'a*'
        nodes.drop('c', axis=1, inplace=True)
        nodes_geom = gpd.points_from_xy(x=nodes['x'], y=nodes['y'], crs=crs)
        nodes = gpd.GeoDataFrame(nodes, geometry=nodes_geom, crs=crs)

        # Read links
        n_rows = last_line - header_links - 1
        links = pd.read_csv(
            zf.open('base.211'), index_col=['From', 'To'], 
            skiprows=header_links, nrows=n_rows,
            sep=r'\s+', low_memory=False
        )
        links.columns = links.columns.str.lower()
        links.columns = links.columns.str.strip()
        links.index.names = ['inode', 'jnode']
        mask_mod = links['c'] == 'm'
        n_modified_links = len(links[mask_mod])
        if n_modified_links > 0:
            print(f'  Ignored {n_modified_links} modification records '
                  f'in the links table')
        links = links[~mask_mod].drop('c', axis=1)
        if 'typ' in links.columns:
            links.rename(columns={'typ': 'type'}, inplace=True)
        if 'lan' in links.columns:
            links.rename(columns={'lan': 'lanes'}, inplace=True)

        # Data type conversion
        links = links.astype(
            {'modes': str, 'type': int, 'lanes': float, 'vdf': int})
        # Check if using Emme's engineering notation in these columns
        # and convert if that's the case.
        for col in ['length', 'data1', 'data2', 'data3']:
            if is_string_dtype(links[col]):  
                links[col] = process_emme_eng_notation_series(links[col])
            else:
                links[col] = links[col].astype(float)
    # Read in the link shapes
    addshapes_dict = {
        'i_node': [], 
        'j_node': [], 
        'vertex_no': [], 
        'x-coord': [], 
        'y-coord': []
    }
    sep = ' '  # Separator used when exporting link shapes in NWP tools
    with zipfile.ZipFile(nwp_fp) as zf:
        for i, line in enumerate(zf.open('shapes.251'), start=1):
            line = line.strip().decode('utf-8')
            # At this point I'll only worry about adding vertices as the
            # objective is to read exported link shapes early
            if line.startswith('a'):
                tokens = line.split(sep)
                addshapes_dict['i_node'].append(int(tokens[1]))
                addshapes_dict['j_node'].append(int(tokens[2]))
                addshapes_dict['vertex_no'].append(int(tokens[3]))
                addshapes_dict['x-coord'].append(float(tokens[4]))
                addshapes_dict['y-coord'].append(float(tokens[5]))
    linkshapes = pd.DataFrame.from_dict(addshapes_dict)
    linkshapes = linkshapes.set_index(['i_node', 'j_node', 'vertex_no'])
    
    # Create link geometry
    link_geometry = gpd.GeoSeries(index=links.index, crs=crs)
    for (i_node, j_node), _ in links.iterrows():
        try:
            ls = linkshapes.loc[idx[i_node, j_node, :]]
            # If we get here that means that we have a link shape
            pt_list = [nodes.at[i_node, 'geometry']]
            for _, row in ls.iterrows():
                pt_list.append(Point(row['x-coord'], row['y-coord']))            
            pt_list.append(nodes.at[j_node, 'geometry'])
        except KeyError: # No link shape for this link, create a straight link
            pt_list = [nodes.at[i_node, 'geometry'], 
                       nodes.at[j_node, 'geometry']]

        link_geometry.at[i_node, j_node] = LineString(pt_list)
    links = gpd.GeoDataFrame(links, geometry=link_geometry, crs=crs)
    return nodes, links

def read_nwp_exatts_list(nwp_fp: Union[str, PathLike], **kwargs) -> pd.DataFrame:
    """A function to read the extra attributes present in a Network Package file 
    (exported from Emme using the TMG Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.
        **kwargs: Any valid keyword arguments used by ``pandas.read_csv()``.

    Returns:
        pd.DataFrame
    """
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    kwargs['index_col'] = False
    if 'quotechar' not in kwargs:
        kwargs['quotechar'] = "'"

    with zipfile.ZipFile(nwp_fp) as zf:
        df = pd.read_csv(zf.open('exatts.241'), **kwargs)
        df.columns = df.columns.str.strip()
        df['type'] = df['type'].astype('category')

    return df


def base_read_nwp_att_data(nwp_fp: Union[str, PathLike], att_type: str, index_col: Union[str, List[str]],
                            attributes: Union[str, List[str]] = None, **kwargs) -> pd.DataFrame:
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    if attributes is not None:
        if isinstance(attributes, Hashable):
            attributes = [attributes]
        elif isinstance(attributes, list):
            pass
        else:
            raise RuntimeError

    if 'quotechar' not in kwargs:
        kwargs['quotechar'] = "'"

    with zipfile.ZipFile(nwp_fp) as zf:
        df = pd.read_csv(zf.open(f'exatt_{att_type}.241'), **kwargs)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if is_string_dtype(df[col]):
                df[col] = df[col].str.strip()
        df.set_index(index_col, inplace=True)

    if attributes is not None:
        df = df[attributes].copy()

    return df


def read_nwp_node_attributes(nwp_fp: Union[str, PathLike], *, attributes: Union[str, List[str]] = None,
                             **kwargs) -> pd.DataFrame:
    """A function to read node attributes from a Network Package file (exported from Emme using the TMG Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.
        attributes (str | List[str], optional): Defaults to ``None``. Names of node attributes to extract. Note
            that ``'inode'`` will be included by default.
        **kwargs: Any valid keyword arguments used by ``pandas.read_csv()``.

    Returns:
        pd.DataFrame
    """
    return base_read_nwp_att_data(nwp_fp, 'nodes', 'inode', attributes, **kwargs)


def read_nwp_link_attributes(nwp_fp: Union[str, PathLike], *, attributes: Union[str, List[str]] = None,
                             **kwargs) -> pd.DataFrame:
    """A function to read link attributes from a Network Package file (exported from Emme using the TMG Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.
        attributes (str | List[str], optional): Defaults to ``None``. Names of link attributes to extract. Note
            that ``'inode'`` and ``'jnode'`` will be included by default.
        **kwargs: Any valid keyword arguments used by ``pandas.read_csv()``.

    Returns:
        pd.DataFrame
    """
    return base_read_nwp_att_data(nwp_fp, 'links', ['inode', 'jnode'], attributes, **kwargs)


def read_nwp_transit_line_attributes(nwp_fp: Union[str, PathLike], *, attributes: Union[str, List[str]] = None,
                                     **kwargs) -> pd.DataFrame:
    """A function to read transit line attributes from a Network Package file (exported from Emme using the TMG
    Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.
        attributes (str | List[str], optional): Defaults to ``None``. Names of transit line attributes to extract.
            Note that ``'line'`` will be included by default.
        **kwargs: Any valid keyword arguments used by ``pandas.read_csv()``.

    Returns:
        pd.DataFrame
    """
    return base_read_nwp_att_data(nwp_fp, 'transit_lines', 'line', attributes, **kwargs)


def read_nwp_traffic_results(nwp_fp: Union[str, PathLike]) -> pd.DataFrame:
    """A function to read the traffic assignment results from a Network Package file (exported from Emme using the TMG
    Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.

    Returns:
        pd.DataFrame
    """
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    with zipfile.ZipFile(nwp_fp) as zf:
        df = pd.read_csv(zf.open('link_results.csv'), index_col=['i', 'j'])
        df.index.names = ['inode', 'jnode']

    return df



def read_nwp_transit_network(nwp_fp: Union[str, PathLike]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """A function to read the transit network from a Network Package file (exported from Emme using the TMG Toolbox)
    into DataFrames.

    Args:
        nwp_fp (str | PathLike): File path to the network package.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: A tuple of DataFrames containing the transt lines and segments.
    """
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    # Parse through transit line transaction file
    seg_cols = ['inode', 'dwt', 'ttf', 'us1', 'us2', 'us3']
    transit_lines = []
    transit_segs = []
    current_tline = None
    with zipfile.ZipFile(nwp_fp) as zf:
        for line in zf.open('transit.221'):
            line = line.strip().decode('utf-8')
            if line.startswith('c') or line.startswith('t') or line.startswith('path'):
                continue  # Skip
            elif line.startswith('a'):
                parts = re.sub(r'\s+', ' ', line.replace("'", ' ')).split(' ')
                parts = parts[1:6] + [' '.join(parts[6:-3])] + parts[-3:]  # reconstruct parts with a joined description
                transit_lines.append(parts)
                current_tline = parts[0]
            else:
                parts = re.sub(r'\s+', ' ', line).split(' ')
                if len(parts) < len(seg_cols):
                    parts = parts + [np.nan] * (len(seg_cols) - len(parts))  # row needed for node... pad with NaNs
                parts.insert(0, current_tline)
                transit_segs.append(parts)

    # Create transit segment dataframe
    transit_segs = pd.DataFrame(transit_segs, columns=['line'] + seg_cols)
    transit_segs['inode'] = transit_segs['inode'].astype(np.int64)
    transit_segs['jnode'] = transit_segs.groupby('line')['inode'].shift(-1).fillna(0).astype(np.int64)
    transit_segs['seg_seq'] = (transit_segs.groupby('line').cumcount() + 1).astype(int)
    transit_segs['loop'] = (transit_segs.groupby(['line', 'inode', 'jnode'])['seg_seq'].cumcount() + 1).astype(int)
    transit_segs.dropna(inplace=True)  # remove rows without dwt, ttf, us1, us2, us3 data (i.e. the padded rows)
    transit_segs = transit_segs[['line', 'inode', 'jnode', 'seg_seq', 'loop', 'dwt', 'ttf', 'us1', 'us2', 'us3']].copy()
    transit_segs['dwt'] = transit_segs['dwt'].str.replace('dwt=', '', regex=False)
    transit_segs['ttf'] = transit_segs['ttf'].str.replace('ttf=', '', regex=False).astype(np.int16)
    transit_segs['us1'] = transit_segs['us1'].str.replace('us1=', '', regex=False).astype(float)
    transit_segs['us2'] = transit_segs['us2'].str.replace('us2=', '', regex=False).astype(float)
    transit_segs['us3'] = transit_segs['us3'].str.replace('us3=', '', regex=False).astype(float)

    # Create transit lines dataframe
    columns = ['line', 'mode', 'veh', 'headway', 'speed', 'description', 'data1', 'data2', 'data3']
    data_types = {  # remember that python 3.6 doesn't guarentee that order is maintained...
        'line': str, 'mode': str, 'veh': int, 'headway': float, 'speed': float, 'description': str, 'data1': float,
        'data2': float, 'data3': float
    }
    # Slight code change here from original WSP code to set the transit 
    # line and segment index
    transit_lines = pd.DataFrame(transit_lines, columns=columns).astype(
        data_types).set_index('line')
    transit_segs = transit_segs.set_index(
        ['line', 'inode', 'jnode', 'loop'])

    return transit_lines, transit_segs





def read_nwp_transit_segment_results(
        nwp_fp: Union[str, PathLike], segments: pd.DataFrame) -> pd.DataFrame:
    """
    A function to read and summarize the transit segment boardings, alightings, 
    and volumes from a Network Package file (exported from Emme using the 
    TMG Toolbox).

    Args:
        nwp_fp (str | PathLike): File path to the network package.
        segments: pd.DataFrame, segments read in using read_nwp_transit_network

    Returns:
        pd.DataFrame
    """
    segments = segments.copy()   # To not modify input DataFrame
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')

    with zipfile.ZipFile(nwp_fp) as zf:
        results = pd.read_csv(
            zf.open('segment_results.csv'), 
            index_col=['line', 'i', 'j', 'loop'])

    segments['boardings'] = results['transit_boardings'].round(3)
    segments['volume'] = results['transit_volume'].round(3)
    n_missing_segments = len(segments[segments['boardings'].isnull()])
    if n_missing_segments > 0:
        print(f'  Found {n_missing_segments} segments with missing results; '
              f'their results will be set to 0')
        segments.fillna(0, inplace=True)
    segments.reset_index(inplace=True)

    segments['prev_seg_volume'] = segments.groupby('line')['volume'].shift(1).fillna(0)
    segments['alightings'] = segments.eval('prev_seg_volume + boardings - volume').round(3)

    segments.drop(['dwt', 'ttf', 'us1', 'us2', 'us3', 'prev_seg_volume'], axis=1, inplace=True)
    segments = segments[['line', 'inode', 'jnode', 'seg_seq', 'loop', 'boardings', 'alightings', 'volume']].copy()
    segments = segments.set_index(['line', 'inode', 'jnode', 'loop'])
    return segments


def read_nwp_transit_vehicles(nwp_fp: Union[str, PathLike]) -> pd.DataFrame:
    """A function to read the transit vehicles from a Network Package file (exported from Emme using the TMG Toolbox)
    into DataFrames.

    Args:
        nwp_fp (str | PathLike): File path to the network package.

    Returns:
        pd.DataFrame: DataFrame containing the transit vehicles.
    """
    nwp_fp = Path(nwp_fp)
    if not nwp_fp.exists():
        raise FileNotFoundError(f'File `{nwp_fp.as_posix()}` not found.')
    with zipfile.ZipFile(nwp_fp) as zf:
        # Get header
        header = None
        for i, line in enumerate(zf.open('vehicles.202'), start=1):
            line = line.strip().decode('utf-8')
            if line.startswith('c'):
                continue  # Skip comment lines
            if line.startswith('t vehicles'):
                header = i

        # Read data
        data_types = {
            'id': int, 'description': str, 'mode': str, 'fleet_size': int, 'seated_capacity': float,
            'total_capacity': float, 'cost_time_coeff': float, 'cost_distance_coeff': float, 'energy_time_coeff': float,
            'energy_distance_coeff': float, 'auto_equivalent': float
        }
        vehicles = pd.read_csv(
            zf.open('vehicles.202'), index_col='id', usecols=data_types.keys(), dtype=data_types, skiprows=header,
            quotechar="'", sep=r'\s+'
        )
        vehicles.index.name = 'veh_id'

    return vehicles

def merge_attributes(
        left_df: pd.DataFrame,
        nwp_fp: str | PathLike,
        attr_function: Callable,
        attributes: str | List[str] | None
    ) -> pd.DataFrame:
    """ Merge node, link or transit line attributes into network dataframe. """
    attrs = attr_function(nwp_fp, attributes=attributes)
    attr_names = attrs.columns
    if len(attr_names) == 0:
        return left_df
    left_df = left_df.merge(
        attrs, how="left", left_index=True, right_index=True)
    left_df[attr_names].fillna(0.0)
    return left_df
