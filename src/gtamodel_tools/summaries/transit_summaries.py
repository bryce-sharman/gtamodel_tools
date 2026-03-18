import pandas as pd
from typing import Type

from gtamodel_tools.network.network import Network
import gtamodel_tools.common.spatial_aggregator as sa


def summarize_transit_boardings_by_operator(
        networks: Network | list[Network]) -> float | pd.DataFrame:
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
        networks: Network | list[Network]) -> float | pd.DataFrame:
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
        networks: Network | list[Network]) -> pd.DataFrame:
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


def summarize_boardings_by_region(
        networks: Network | list[Network],
        node_aggregation: Type[sa.SpatialAggregator],
        filter_expression: str | None = None,
        crosstab_columns: str | list[str] | None = None
        ) -> float | pd.DataFrame:
    """ Outputs the transit volumes and capacities at countposts.

    Args:
        networks: 
            Network object[s] containing transit data.
        node_aggregation: sa.SpatialAggregator
            Node spatial aggregations used to aggregate boardings.
        filter_expression:
            Optional filter_expression passed into 
            summarize_transit_segments method.
        crosstab_columns: 
            Optional crosstab_columns passed into 
            summarize_transit_segments method.

    Returns:
        DataFrame transit volumes and capacities at countposts.

    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_boardings_by_region(
            networks[0], node_aggregation, filter_expression, crosstab_columns)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_boardings_by_region(
                n, node_aggregation, filter_expression, crosstab_columns)
        return result
    else:
        return networks.summarize_transit_segments(
            expression='boardings', 
            filter_expression=filter_expression,
            node_aggregation=node_aggregation,
            crosstab_columns=crosstab_columns
        )

def summarize_alightings_by_region(
        networks: Network | list[Network],
        node_aggregation: Type[sa.SpatialAggregator],
        filter_expression: str | None = None,
        crosstab_columns: str | list[str] | None = None
        ) -> float | pd.DataFrame:
    """ Outputs the transit volumes and capacities at countposts.

    Args:
        networks: 
            Network object[s] containing transit data.
        node_aggregation:
            Node spatial aggregations used to aggregate alightings.
        filter_expression: 
            Optional filter_expression passed into 
            summarize_transit_segments method.
        crosstab_columns:
            Optional crosstab_columns passed into 
            summarize_transit_segments method.

    Returns:
        DataFrame transit volumes and capacities at countposts.

    """
    if isinstance(networks, list):
        n_networks = len(networks)
        result = summarize_alightings_by_region(
            networks[0], node_aggregation, filter_expression, crosstab_columns)
        if n_networks == 1:
            return result
        for n in networks[1:]:
            result += summarize_alightings_by_region(
                n, node_aggregation, filter_expression, crosstab_columns)
        return result
    else:
        return networks.summarize_transit_segments(
            expression='alightings', 
            filter_expression=filter_expression,
            node_aggregation=node_aggregation,
            crosstab_columns=crosstab_columns
        )