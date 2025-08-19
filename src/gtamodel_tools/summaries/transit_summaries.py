import pandas as pd
from typing import List

from gtamodel_tools.network.network import Network

def summarize_transit_boardings_by_operator(
        networks: Network | List[Network]) -> float | pd.DataFrame:
    """ Summarizes transit boardings by operator.

    Args:
        networks: 
            Network object[s] containing transit data.

    Returns:
        Series with total boardings per operator.
    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_transit_boardings_by_operator(networks[0])
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_transit_boardings_by_operator(n)
        return result
    else:
        return networks.summarize_transit_segments(
            networks.tsegment_boardings_col, 
            crosstab_columns=networks.toperator
        )


def summarize_transit_pkt_by_operator(
        networks: Network | List[Network]) -> float | pd.DataFrame:
    """ Summarizes passenger kilometres travelled by operator.

    Args:
        networks: Network object[s] containing transit data.

    Returns:
        Series with total passenger kilometres travelled per operator.
    """
    # Assuming net has a method to get boardings by operator
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_transit_pkt_by_operator(networks[0])
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_transit_pkt_by_operator(n)
        return result
    else:
        return networks.summarize_transit_segments(
        networks.transit_pkt_expr, 
        crosstab_columns=networks.toperator
    )


def summarize_transit_line_profiles(network: Network) -> float | pd.DataFrame:
    """ Summarizes line profiles for transit lines.

    Args:
        network: Network object containing transit data.

    Returns:
        DataFrame with line profiles.

    Notes:
        Line profiles are currently only envisioned for one time period
        at a time. Can expand to multiple time periods in the future.
    """
    # Assuming net has a method to calculate line profiles
    return network.calculate_line_profiles()

def summarize_at_transit_countposts(
        networks: Network | List[Network]) -> pd.DataFrame:
    """ Outputs the transit volumes and capacities at countposts.

    Args:
        networks: Network object[s] containing transit data.

    Returns:
        DataFrame transit volumes and capacities at countposts.

    """
    # Assuming net has a method to get boardings by operator
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_at_transit_countposts(networks[0])
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_at_transit_countposts(n)
        return result
    else:
        return networks.output_transit_results_at_countposts()


