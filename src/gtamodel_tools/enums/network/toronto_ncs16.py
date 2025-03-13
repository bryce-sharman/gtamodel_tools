import gtamodel_tools.common.spatial_aggregator as sa

CRS = 'EPSG:26917'

LENGTH_COL = 'length'
MODES_COL = 'modes'
TYPE_COL = 'type'
LANES_COL = 'lanes'
VDF_COL = 'vdf'
FFSPD_COL = 'data2'
LANECAP_COL = 'data3'
AUTOVOL_COL = 'auto_volume'
AUTOADDVOL_COL = 'additional_volume'
AUTOTIME_COL = 'auto_time'

TRAFFIC_VKT_EXPR = "length * (auto_volume + additional_volume)"
TRAFFIC_VHT_EXPR = "timau * (auto_volume + additional_volume) / 60.0"
FILTER_VCR_EXPR = "((auto_volume + additional_volume) /  " \
                  "(lanes * data3)) > "
MIN_REGNODE_ID = 10000
AUTO_MODE = 'c'
zone_ranges = sa.create_spatial_aggregator(
        'custom_ranges', 
        ranges=[
            ('toronto', 1, 1000), 
            ('durham', 1001, 2000),
            ('york', 2001, 3000),
            ('peel', 3001, 4000),
            ('halton', 4001, 5000),
            ('hamilton', 5001, 6000),
            ('external', 6001, 7000),
            ('undefined', 7001, 9799),
            ('special', 9800, 9999)
        ],
        ids=range(0, 10000),
        name='zone_regions',
    )

node_ranges = sa.create_spatial_aggregator(
        'custom_ranges', 
        ranges=[
            ('centroid', 0, 9999), 
            ('Toronto', 10000, 19999), 
            ('Durham', 20000, 29999),
            ('York', 30000, 39999),
            ('Peel', 40000, 49999),
            ('Halton', 50000, 59999),
            ('Hamilton', 60000, 69999),
            ('External', 70000, 89999),
            ('Special', 90000, 999999),
            ('Niagara', 70000, 79999),
            ('Haldimand-Norfolk',  80000, 80999),
            ('Brant County',  81000, 81999),
            ('Waterloo Region',  82000, 84999),
            ('Wellington County',  85000, 86999),
            ('Dufferin County',  87000, 87999),
            ('Simcoe County',  88000, 89999),
            ('Kawartha Lakes Division', 90000, 90999),
            ('Peterborough County', 91000, 91999),
            ('External zones/gateways Canada', 94000, 94999),
            ('External zones/gateways, US', 95000, 95999),
            ('BRT/LRT nodes', 96000, 96999),
            ('Subway nodes',  97000, 97999),
            ('GO Rail nodes',  98000, 98999),
            ('Hypernetwork nodes', 100000, 900000),
            ('HOV',  900000, 999999)
        ],
        ids=range(0, 1000000),
        name='zone_regions',
    )

