""" Tests for gtamodel_tools.network.network.summarize_traffic_across_screenlines. """

import pytest

@pytest.fixture
def screenlines_gdf(testdata_path) -> gpd.GeoDataFrame:
    shp_path = testdata_path / "Screenlines" / "Screenlines.shp"
    gdf = gpd.read_file(shp_path)
    return gdf.set_index('name')








# def summarize_traffic_across_screenlines(
#         networks: Network | list[Network],
#         screenlines: gpd.GeoDataFrame,
#         scale_by_auto_phf: bool = False
#     ) -> pd.DataFrame:
#     """ Summarizes auto traffic volumes across screenlines.

#     Args:
#         networks: 
#             Network object[s] containing transit data.
#         scale_by_auto_phf: bool
#                 If True, scale VKT by the auto peak-hour factor.
#     Returns:
#         Series with total traffic volumes per screenline.
#     """
#     summary_results_cols = [
#         'capacity', 'auto_vol', 'additional_vol', 'traffic_vol']
#     if isinstance(networks, list):
#         n_networks = len(networks)
#         result = summarize_traffic_across_screenlines(
#             networks[0], screenlines, scale_by_auto_phf)
#         if n_networks == 1:
#             return result
#         for n in networks[1:]:
#             tmp_result = summarize_traffic_across_screenlines(
#                 n, screenlines, scale_by_auto_phf)
#             result[summary_results_cols] = \
#                 result[summary_results_cols] + \
#                 tmp_result[summary_results_cols]
#         result['vcr'] = result['traffic_vol'] / result['capacity']
#         return result
#     else:
#         result = networks.summarize_traffic_across_screenlines(screenlines)
#         if scale_by_auto_phf:
#             if networks.auto_phf is None:
#                 raise RuntimeError(
#                     "Auto peak-hour factor (auto_phf) must be defined "
#                     "to calculate scaled traffic volumes.") 
#             result[summary_results_cols] = \
#                 result[summary_results_cols] * networks.auto_phf
#         result['vcr'] = result['traffic_vol'] / result['capacity']
#         return result