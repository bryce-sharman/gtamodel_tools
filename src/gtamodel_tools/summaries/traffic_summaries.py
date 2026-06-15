import geopandas as gpd
from os import PathLike
import pandas as pd

from gtamodel_tools.network.network import Network

def summarize_traffic_vkt(
        networks: Network | list[Network],
        scale_by_auto_phf: bool=False,
        **kwargs
    ) -> float | pd.DataFrame:
    """ Summarizes auto vehicle kilometres travelled.

    Args:
        networks: 
            Network object[s] containing transit data.
        scale_by_auto_phf:
                If True, scale VKT by the auto peak-hour factor.
        kwargs:
            Additional parameters to be passed into 
                network.summarize_link_attributes

    Returns:
        Series with total boardings per operator.
    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_traffic_vkt(
            networks[0], scale_by_auto_phf, **kwargs)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_traffic_vkt(
                n, scale_by_auto_phf, **kwargs)
        return result
    else:
        result =  networks.summarize_link_attributes(
            'vkt', **kwargs)
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled VKTs.") 
            result = result * networks.auto_phf
        return result


def summarize_traffic_vht(
        networks: Network | list[Network],
        scale_by_auto_phf: bool = False,
        **kwargs
    ) -> float | pd.DataFrame:
    """ Summarizes auto vehicle hours travelled.

    Args:
        networks: 
            Network object[s] containing transit data.
        scale_by_auto_phf:
                If True, scale VKT by the auto peak-hour factor.
        kwargs:
            Additional parameters to be passed into 
                network.summarize_link_attributes
    
    Returns:
        Series with total boardings per operator.
    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_traffic_vht(
            networks[0], scale_by_auto_phf, **kwargs)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_traffic_vht(
                n, scale_by_auto_phf, **kwargs)
        return result
    else:
        result = networks.summarize_link_attributes(
            'vht', **kwargs)
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled VHTs.") 
            result = result * networks.auto_phf
        return result

    
def summarize_traffic_across_screenlines(
        networks: Network | list[Network],
        screenlines_fp: PathLike, 
        index_col: str,
        scale_by_auto_phf: bool = False
    ) -> pd.DataFrame:
    """ Summarizes auto traffic volumes across screenlines.

    Args:
        networks: 
            Network object[s] containing transit data.
        screenlines_fp: Path to shapefile, or equivalent
        index_col: column in geospatial data containing the 
            screenlines names.
        scale_by_auto_phf: bool
                If True, scale VKT by the auto peak-hour factor.
    Returns:
        Series with total traffic volumes per screenline.
    """
    summary_results_cols = [
        'capacity', 'auto_vol', 'additional_vol', 'traffic_vol']
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_traffic_across_screenlines(
            networks[0], screenlines_fp, index_col, scale_by_auto_phf)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            tmp_result = summarize_traffic_across_screenlines(
                n, screenlines_fp, index_col, scale_by_auto_phf)
            result[summary_results_cols] = \
                result[summary_results_cols] + \
                tmp_result[summary_results_cols]
        result['vcr'] = result['traffic_vol'] / result['capacity']
        return result
    else:
        result = networks.summarize_traffic_across_screenlines(
            screenlines_fp, index_col
        )
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled traffic volumes.") 
            result[summary_results_cols] = \
                result[summary_results_cols] * networks.auto_phf
        result['vcr'] = result['traffic_vol'] / result['capacity']
        return result