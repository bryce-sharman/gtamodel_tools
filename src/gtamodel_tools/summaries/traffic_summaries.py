import geopandas as gpd
import pandas as pd

from gtamodel_tools.network.network import Network

def summarize_traffic_vkt(
        networks: Network | list[Network],
        summarize_by_linkclass: bool,
        scale_by_auto_phf: bool = False
    ) -> float | pd.DataFrame:
    """ Summarizes auto vehicle kilometres travelled.

    Args:
        networks: 
            Network object[s] containing transit data.
        summarize_by_linkclass: bool
                If True, additionally segment VKT by link classification.
        scale_by_auto_phf: bool
                If True, scale VKT by the auto peak-hour factor.

    Returns:
        Series with total boardings per operator.
    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_traffic_vkt(
            networks[0], summarize_by_linkclass, scale_by_auto_phf)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_traffic_vkt(
                n, summarize_by_linkclass, scale_by_auto_phf)
        return result
    else:
        result =  networks.summarize_link_attributes(
            'vkt', 
            node_aggregation=networks.node_ranges, 
            segment_by_linkclass=True
        )
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled VKTs.") 
            result = result * networks.auto_phf
        return result


def summarize_traffic_vht(
        networks: Network | list[Network],
        summarize_by_linkclass: bool,
        scale_by_auto_phf: bool = False
    ) -> float | pd.DataFrame:
    """ Summarizes auto vehicle hours travelled.

    Args:
        networks: 
            Network object[s] containing transit data.
        summarize_by_linkclass: bool
                If True, additionally segment VHT by link classification.
        scale_by_auto_phf: bool
                If True, scale VKT by the auto peak-hour factor.
    
    Returns:
        Series with total boardings per operator.
    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_traffic_vht(
            networks[0], summarize_by_linkclass, scale_by_auto_phf)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_traffic_vht(
                n, summarize_by_linkclass, scale_by_auto_phf)
        return result
    else:
        result = networks.summarize_link_attributes(
            'vht', 
            node_aggregation=networks.node_ranges, 
            segment_by_linkclass=True
        )
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled VHTs.") 
            result = result * networks.auto_phf
        return result

    
def summarize_traffic_across_screenlines(
        networks: Network | list[Network],
        screenlines: gpd.GeoDataFrame,
        scale_by_auto_phf: bool = False
    ) -> pd.DataFrame:
    """ Summarizes auto traffic volumes across screenlines.

    Args:
        networks: 
            Network object[s] containing transit data.
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
            networks[0], screenlines, scale_by_auto_phf)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            tmp_result = summarize_traffic_across_screenlines(
                n, screenlines, scale_by_auto_phf)
            result[summary_results_cols] = \
                result[summary_results_cols] + \
                tmp_result[summary_results_cols]
        result['vcr'] = result['traffic_vol'] / result['capacity']
        return result
    else:
        result = networks.summarize_traffic_across_screenlines(screenlines)
        if scale_by_auto_phf:
            if networks.auto_phf is None:
                raise RuntimeError(
                    "Auto peak-hour factor (auto_phf) must be defined "
                    "to calculate scaled traffic volumes.") 
            result[summary_results_cols] = \
                result[summary_results_cols] * networks.auto_phf
        result['vcr'] = result['traffic_vol'] / result['capacity']
        return result